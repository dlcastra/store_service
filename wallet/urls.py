from django.urls import path

from wallet import views

urlpatterns = [
    # WALLET
    path("connect-wallet/", views.ConnectWalletView.as_view(), name="connect_wallet"),
]
