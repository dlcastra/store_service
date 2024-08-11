import rest_framework.authtoken.views as auth
from django.urls import path
from rest_framework import routers

from usersapi import views

router = routers.DefaultRouter()
router.register(r"register", views.RegisterView, basename="register"),

urlpatterns = router.urls

urlpatterns += [
    # path("login/", auth.obtain_auth_token, name="login"),
    path("login/", views.LoginWithObtainAuthToken.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete_account"),
    path("get-new-token/", views.RotateTokenView.as_view(), name="get_new_token"),
    path("get-active-sessions/", views.GetAllActiveSessionsView.as_view(), name="get_active_sessions"),
]
