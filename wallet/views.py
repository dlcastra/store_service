import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from usersapi.models import CustomUser
from wallet.constants import MAX_TRANSACTION_AMOUNT, MIN_TRANSACTION_AMOUNT
from wallet.filters import TransactionsFilter
from wallet.mixins import WalletTransactionMixin
from wallet.models import Wallet, WalletToWalletTransaction
from wallet.paginations import TransactionPagination
from wallet.serializers import TransactionHistorySerializer

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

        self.logger.info("The wallet has been successfully created")
        return Response({"message": f"Your wallet address: {wallet.address}"}, status=status.HTTP_201_CREATED)


class GetWalletInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
        self._perform_transaction(request_user_from, user_to, wallet_from, wallet_to, validated_amount)
        self.logger.info("Transaction successful")
        return Response(
            {"message": "Transaction was successful", "Your balance": wallet_from.wallet_balance},
            status=status.HTTP_201_CREATED,
        )
