from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from usersapi.models import CustomUser
from wallet.models import Wallet

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
                {"message": f"You already have a wallet\nWallet address: {wallet.address}"},
                status=status.HTTP_200_OK,
            )

        wallet.wallet_balance += user_bonuses.amount_bonuses
        user_bonuses.amount_bonuses = 0
        user_bonuses.save()
        wallet.save()

        return Response({"message": f"Your wallet address: {wallet.address}"}, status=status.HTTP_201_CREATED)
