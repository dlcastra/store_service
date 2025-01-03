import decimal
import logging

import requests
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from usersapi.models import CustomUser
from usersapi.tasks import send_email
from wallet.constants import MAX_TRANSACTION_AMOUNT, MIN_TRANSACTION_AMOUNT
from wallet.filters import TransactionsFilter
from wallet.mixins import WalletTransactionMixin
from wallet.models import Wallet, WalletToWalletTransaction, PaymentTransaction
from wallet.paginations import TransactionPagination
from wallet.serializers import TransactionHistorySerializer
from wallet.utils import get_node_url

""" --- WALLET --- """


class ConnectWalletView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    logger = logging.getLogger()

    def get(self, request):

        return Response(
            {"message": "To connect a wallet, specify your token in the body of the request or send POST request"},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        user_bonuses = CustomUser.objects.get(username=request.user.username)
        wallet, created = Wallet.objects.get_or_create(user=request.user)

        if not created:
            self.logger.warning("Wallet already exists")
            return Response(
                {"message": "You already have a wallet", "wallet address": f"{wallet.address}"},
                status=status.HTTP_200_OK,
            )

        wallet.wallet_balance += user_bonuses.amount_bonuses
        user_bonuses.amount_bonuses = 0
        user_bonuses.save()
        wallet.save()

        send_email.delay(
            email=request.user.email,
            subject="Your wallet",
            template_name="emails/wallet_connection.html",
            context={"username": request.user.username},
        )

        self.logger.info("The wallet has been successfully created")
        return Response({"message": f"Your wallet address: {wallet.address}"}, status=status.HTTP_201_CREATED)


class GetWalletInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        user = request.user
        wallet = Wallet.objects.get(user=user)
        return Response(
            {"wallet address": wallet.address, "wallet balance": wallet.wallet_balance}, status=status.HTTP_200_OK
        )


class GetWalletTransactionHistoryView(generics.ListAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionPagination
    serializer_class = TransactionHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TransactionsFilter

    def get_queryset(self):
        user = self.request.user
        transactions = WalletToWalletTransaction.objects.filter(user_from=user).order_by("-timestamp")

        return transactions

    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class WalletToWallerTransactionView(WalletTransactionMixin, APIView):
    permission_classes = [IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        request_user_from = request.user
        wallet_addr_to = request.data.get("wallet_addr_to")
        amount = request.data.get("amount")

        # GET DATA FROM REQUEST
        if "wallet_addr_to" not in request.data:
            self.logger.warning(f"Missing wallet address of the recipient. User: {request_user_from.username}")
            return self._error_response("To make transaction you must provide wallet address in 'wallet_addr_to'!")

        if "amount" not in request.data:
            self.logger.warning(f"Missing amount for transaction.")
            return self._error_response("To make a transaction, you must provide the amount.")

        # CHECK WALLET FROM
        wallet_from = self._get_wallet_from_user(request_user_from)
        if not wallet_from:
            self.logger.error(f"No wallet found for user {request_user_from.username}")
            return self._error_response("To make Wallet-To-Wallet transaction you need to create a wallet")

        if wallet_from.address == wallet_addr_to:
            self.logger.error(f"Attempt to transfer funds to the same wallet by user: {request_user_from.username}")
            return self._error_response("Cannot transfer to the same wallet")

        # CHECK WALLET TO
        wallet_to, user_to = self._get_wallet_to_and_user_to(wallet_addr_to)
        if not wallet_to or not user_to:
            return self._error_response("Enter valid wallet address")

        # CHECK AMOUNT AND WALLET BALANCE
        validated_amount = self._validate_amount(amount)
        if validated_amount is None:
            return self._error_response("Enter a valid amount. Ex: 1.00")

        if validated_amount > MAX_TRANSACTION_AMOUNT:
            return self._error_response("Maximum amount of transactions 100000.00")

        if validated_amount < MIN_TRANSACTION_AMOUNT:
            return self._error_response("Minimum amount of transactions 10.00")

        if wallet_from.wallet_balance < validated_amount:
            return self._error_response("Insufficient funds in wallet.")

        # CREATE AND SAVE TRANSACTION
        self._check_transaction_duplicate(request_user_from, user_to, wallet_from, wallet_to, validated_amount)
        transaction_id = self._perform_transaction(request_user_from, user_to, wallet_from, wallet_to, validated_amount)
        self.logger.info("Transaction successful")

        send_email.delay(
            email=request.user.email,
            subject="Your wallet",
            template_name="emails/W2WTransaction.html",
            context={
                "transaction_id": transaction_id,
                "username": request.user.username,
                "amount": validated_amount,
                "user_to": user_to.username,
                "wallet_to_addr": wallet_addr_to,
            },
        )

        return Response(
            {"message": "Transaction was successful", "Your balance": wallet_from.wallet_balance},
            status=status.HTTP_201_CREATED,
        )


class RefillWalletView(APIView):
    permission_classes = [IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        amount: int = request.data["amount"]
        ccy: int = request.data["ccy"] if "ccy" in request.data else 840

        user_wallet = self.get_user_wallet(user_id)
        if user_wallet is None:
            return Response({"error": "To make refill transaction you need to create a wallet"})

        return self._send_transaction_request(user_id, user_wallet, amount, ccy)

    def get_user_wallet(self, user_id: int) -> Wallet | None:
        """
        Return an instance of the user wallet
        """
        try:
            return Wallet.objects.select_related("user").get(user_id=user_id)
        except Wallet.DoesNotExist:
            self.logger.error("User's wallet is not defined")
            return None

    @staticmethod
    def _send_transaction_request(
        user_id: int, user_wallet: Wallet, amount: int, ccy: int, **kwargs
    ) -> dict | Response:

        payment_service_url: str = get_node_url()
        url = f"{payment_service_url}/make-transaction"
        payload = {"userId": user_id, "walletAddr": user_wallet.address, "amount": amount, "ccy": ccy, **kwargs}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return Response(response.json())
        except requests.RequestException as e:
            print(f"Error sending transaction request: {e}")
            return Response({"error": e}, status=status.HTTP_400_BAD_REQUEST)


class PaymentWebhookView(APIView):
    logger = logging.getLogger()

    def post(self, request, *args, **kwargs):
        request_body = request.data
        print(request_body)

        try:
            user_wallet: Wallet = self.get_user_wallet(request_body["user_id"])

            if request_body["status"] == "success":
                amount = self.get_correct_amount(request_body)
                self.create_refill_transaction(request_body, user_wallet, amount)
                self.update_wallet_balance(user_wallet, amount)

        except Exception as e:
            self.logger.error(f"Transaction processing: {e}")
            return Response({"status": "error"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "success"}, status=status.HTTP_200_OK)

    def get_user_wallet(self, user_id: int) -> Wallet | None:
        """
        Return an instance of the user wallet
        """
        try:
            return Wallet.objects.select_related("user").get(user_id=user_id)
        except Wallet.DoesNotExist:
            self.logger.error("User's wallet is not defined")
            return None

    def get_correct_amount(self, request_body) -> decimal.Decimal:
        """
        Changes the amount type from float to decimal
        and converts the amount of kopecks to whole currency
        """
        converted_amount = request_body["amount"] / 100
        self.logger.info(f"Amount converted: {converted_amount}")
        return decimal.Decimal(converted_amount)

    def create_refill_transaction(self, request_body, user_wallet: Wallet, amount: decimal.Decimal) -> None:
        refill_transaction = PaymentTransaction.objects.create(
            transaction_id=request_body["transactionId"],
            user=user_wallet.user,
            user_wallet_addr=user_wallet.address,
            amount=amount,
            currency=request_body.get("ccy", 840),
            invoice_id=request_body["invoiceId"],
        )

        if refill_transaction:
            self.logger.info(f"Transaction successfully created: {refill_transaction.transaction_id}")

        self.logger.info(f"Waiting for transaction processing to complete")

    def update_wallet_balance(self, user_wallet: Wallet, amount: decimal.Decimal) -> None:
        """
        Updates the user's wallet balance.
        """
        user_wallet.wallet_balance += amount
        user_wallet.save()
        self.logger.info(f"The balance of wallet {user_wallet.address} has been refilled by {amount}")
