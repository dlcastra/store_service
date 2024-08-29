from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.utils import IntegrityError
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usersapi.models import CustomUser
from wallet.models import Wallet, WalletToWalletTransaction

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
        if "wallet_addr_to" not in request.data:
            return Response(
                {"message": "To make transaction you must provide wallet address in 'wallet_addr_to'!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "amount" not in request.data:
            return Response(
                {"error": "To make transaction you must provide amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            wallet_from = Wallet.objects.get(user=request_user_from)
            wallet_addr_from = wallet_from.address
        except Wallet.DoesNotExist:
            return Response(
                {"error": "To make WalletToWallet transaction you need to create a wallet"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet_addr_to = request.data.get("wallet_addr_to")
        if wallet_addr_from == wallet_addr_to:
            return Response({"error": "Cannot transfer to the same wallet"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wallet_to = Wallet.objects.get(address=wallet_addr_to)
            user_id_in_wallet = wallet_to.user_id
            user_to = CustomUser.objects.get(id=user_id_in_wallet)
        except (Wallet.DoesNotExist, IntegrityError):
            return Response({"error": "Enter valid wallet address"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(request.data.get("amount"))
        except (ValueError, InvalidOperation):
            return Response({"error": "Enter valid amount. Ex: 1.00"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        if wallet_from.wallet_balance >= amount:
            with transaction.atomic():
                wallet_from.wallet_balance -= amount
                wallet_to.wallet_balance += amount
                wallet_from.save()
                wallet_to.save()

                WalletToWalletTransaction.objects.create(
                    user_from=request_user_from,
                    user_to=user_to,
                    wallet_addr_from=wallet_addr_from,
                    wallet_addr_to=wallet_addr_to,
                    amount=amount,
                )
                return Response(
                    {"message": "Transaction was successful", "Your balance": wallet_from.wallet_balance},
                    status=status.HTTP_201_CREATED,
                )
        return Response({"error": "Insufficient funds in wallet"}, status=status.HTTP_400_BAD_REQUEST)
