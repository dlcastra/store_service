from django.urls import path
from rest_framework import routers

from wallet import views

router = routers.DefaultRouter()
router.register(r"wallet/transactions-history", views.GetWalletTransactionHistoryView, basename="transactions_history")

urlpatterns = router.urls

urlpatterns += [
    # WALLET
    path("wallet/connect", views.ConnectWalletView.as_view(), name="connect_wallet"),
    path("wallet/", views.GetWalletInfoView.as_view(), name="wallet"),
    path(
        "wallet/make-transaction/", views.WalletToWallerTransactionView.as_view(), name="wallet_to_wallet_transaction"
    ),
    path("wallet/refill", views.RefillWalletView.as_view(), name="refill_wallet"),
]
