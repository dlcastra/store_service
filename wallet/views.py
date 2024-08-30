from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usersapi.models import CustomUser
from wallet.constants import MAX_TRANSACTION_AMOUNT, MIN_TRANSACTION_AMOUNT
from wallet.models import Wallet, WalletToWalletTransaction
from wallet.utils import encrypt_data

""" --- WALLET --- """


class ConnectWalletView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        return Response(
            {"message": "To connect a wallet, specify your token in the body of the request or send POST request"},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        user_bonuses = CustomUser.objects.get(username=request.user.username)
        wallet, created = Wallet.objects.get_or_create(user=request.user)

        if not created:
            return Response(
                {"message": "You already have a wallet", "wallet address": f"{wallet.address}"},
                status=status.HTTP_200_OK,
            )

        wallet.wallet_balance += user_bonuses.amount_bonuses
        user_bonuses.amount_bonuses = 0
        user_bonuses.save()
        wallet.save()

        return Response({"message": f"Your wallet address: {wallet.address}"}, status=status.HTTP_201_CREATED)


class GetWalletInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet = Wallet.objects.get(user=user)
        return Response(
            {"wallet address": wallet.address, "wallet balance": wallet.wallet_balance}, status=status.HTTP_200_OK
        )


class WalletToWallerTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_user_from = request.user
        wallet_addr_to = request.data.get("wallet_addr_to")
        amount = request.data.get("amount")

        # GET DATA FROM REQUEST
        if "wallet_addr_to" not in request.data:
            return self._error_response("To make transaction you must provide wallet address in 'wallet_addr_to'!")

        if "amount" not in request.data:
            return self._error_response("To make a transaction, you must provide the amount.")

        # CHECK WALLET FROM
        wallet_from = self._get_wallet_from_user(request_user_from)
        if not wallet_from:
            return self._error_response({"error": "To make Wallet-To-Wallet transaction you need to create a wallet"})

        if wallet_from.address == wallet_addr_to:
            return self._error_response({"error": "Cannot transfer to the same wallet"})

        # CHECK WALLET TO
        wallet_to, user_to = self._get_wallet_to_and_user_to(wallet_addr_to)
        if not wallet_to or not user_to:
            return self._error_response({"error": "Enter valid wallet address"})

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
        return Response(
            {"message": "Transaction was successful", "Your balance": wallet_from.wallet_balance},
            status=status.HTTP_201_CREATED,
        )

    def _error_response(self, message):
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    def _get_wallet_from_user(self, user):
        try:
            return Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return None

    def _get_wallet_to_and_user_to(self, wallet_addr_to):
        try:
            wallet_to = Wallet.objects.get(address=wallet_addr_to)
            user_to = CustomUser.objects.get(id=wallet_to.user_id)
            return wallet_to, user_to

        except (Wallet.DoesNotExist, IntegrityError):
            return None, None

    def _validate_amount(self, amount):
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return None
            return amount

        except (ValueError, TypeError, InvalidOperation):
            return None

    def _perform_transaction(self, user_from, user_to, wallet_from, wallet_to, amount):
        try:
            with transaction.atomic():
                wallet_from.wallet_balance -= amount
                wallet_to.wallet_balance += amount
                wallet_from.save()
                wallet_to.save()

                WalletToWalletTransaction.objects.create(
                    user_from=user_from,
                    user_to=user_to,
                    wallet_addr_from=encrypt_data(wallet_from.address),
                    wallet_addr_to=encrypt_data(wallet_to.address),
                    amount=amount,
                )
        except Exception as e:
            transaction.rollback()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _check_transaction_duplicate(self, user_from, user_to, wallet_from, wallet_to, amount):
        recent_transaction = (
            WalletToWalletTransaction.objects.filter(
                user_from=user_from,
                user_to=user_to,
                wallet_addr_from=encrypt_data(wallet_from.address),
                wallet_addr_to=encrypt_data(wallet_to.address),
                amount=amount,
            )
            .order_by("-timestamp")
            .first()
        )
        if recent_transaction and (timezone.now() - recent_transaction.timestamp).total_seconds() < 60:
            self._error_response("Duplicate transaction detected. Please wait before retrying.")
