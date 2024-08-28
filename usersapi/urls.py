from django.urls import path
from rest_framework import routers

from usersapi import views

router = routers.DefaultRouter()
router.register(r"register", views.RegisterView, basename="register"),
router.register(r"edit-user-data", views.EditUserDataView, basename="edit_user_data"),
router.register(r"get-active-sessions", views.GetAllActiveSessionsView, basename="get_active_sessions"),

urlpatterns = router.urls

urlpatterns += [
    path("login/", views.LoginWithObtainAuthToken.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete_account"),
    path("get-new-token/", views.RotateTokenView.as_view(), name="get_new_token"),
    path("delete-another-tokens/", views.DeleteAnotherTokensView.as_view(), name="delete_another_tokens"),
    # WALLET
    path("connect-wallet/", views.ConnectWalletView.as_view(), name="connect_wallet"),
]
