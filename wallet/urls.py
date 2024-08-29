from django.urls import path

from wallet import views

urlpatterns = [
    # WALLET
    path("connect-wallet/", views.ConnectWalletView.as_view(), name="connect_wallet"),
    path("wallet/", views.GetWalletInfoView.as_view(), name="wallet"),
    path(
        "wallet/make-transaction/", views.WalletToWallerTransactionView.as_view(), name="wallet_to_wallet_transaction"
    ),
]
