import logging
from datetime import timedelta

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from usersapi import paginations
from usersapi import serializers
from usersapi.filters import CustomTokenFilter
from usersapi.helpers import generate_key
from usersapi.mixins import AuthorizationTokenMixin
from usersapi.models import CustomObtainToken, CustomUser

""" --- Registration | Login | Logout """


class RegisterView(generics.CreateAPIView, GenericViewSet):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer


class LoginWithObtainAuthToken(APIView):
    logger = logging.getLogger()
    serializer_class = serializers.LoginSerializer

    def post(self, request, *args, **kwargs):
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        user_ip_addr = request.META.get("REMOTE_ADDR", "Unknown")

        serializer = self.serializer_class(data={**request.data, "user_agent": user_agent, "ip_address": user_ip_addr})
        if not serializer.is_valid():
            self.logger.error("Missing or invalid data during login attempt")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        token, created = CustomObtainToken.objects.get_or_create(
            user=user,
            user_agent=user_agent,
            ip_address=user_ip_addr,
        )

        if token:
            token.status = "Online"
            token.save()

        self.logger.info("The user logged in successfully")
        return Response({"Token": token.key, "user_agent": token.user_agent}, status=status.HTTP_200_OK)


class ChangePassword(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()
    serializer_class = serializers.ChangePasswordSerializer

    def get_object(self, queryset=None):
        return self.request.user

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            old_password = serializer.data.get("old_password")
            if not self.object.check_password(old_password):
                self.logger.warning("Invalid old password")
                return Response({"old_password": "Wrong password"}, status=status.HTTP_400_BAD_REQUEST)

            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            self.logger.info("The new password has been accepted")
            return Response({"info": "Successfully changed"}, status=status.HTTP_204_NO_CONTENT)

        self.logger.error("Serializer data is not valid")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        user_ip_addr = request.META.get("REMOTE_ADDR", "Unknown")
        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=user_agent, ip_address=user_ip_addr)
            token.status = "Offline"
            token.save()

            self.logger.info("The user logged out successfully")
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Invalid token")
            return Response({"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND)


""" --- Edit views --- """


class EditUserDataView(generics.RetrieveUpdateAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomUser.objects.all()
    serializer_class = serializers.UserSerializer

    def get_object(self):
        return self.request.user


class RotateTokenView(AuthorizationTokenMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        user_ip_addr = request.META.get("REMOTE_ADDR", "Unknown")
        header_token, error_response = self._get_token_from_header(auth_header)
        if error_response:
            return error_response

        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=user_agent, ip_address=user_ip_addr)
            if token.status != "Online":
                self.logger.warning("Token status is Offline")
                return self._error_response("Provided token status is Offline, please login to change token.")
            if token.key == header_token:
                token.key = generate_key(token)
                token.save()
                self.logger.info("Successfully rotated")
                return Response({"new_token": token.key}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Token does not exist")
            self._error_response("Token does not exist.", status.HTTP_404_NOT_FOUND)

        return self._error_response("Bad request")


""" --- Get views --- """


class GetAllActiveSessionsView(generics.ListAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = paginations.OnlyFiveElementsPagination
    serializer_class = serializers.CustomObtainTokenSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = CustomTokenFilter
    logger = logging.getLogger()

    def get_queryset(self):
        user = self.request.user
        queryset = CustomObtainToken.objects.filter(user=user).order_by("created")
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        auth_header = self.request.headers.get("Authorization")
        if auth_header:
            header_token = auth_header.split(" ")[1]
            context["header_token"] = header_token

        return context

    def list(self, request, *args, **kwargs):
        list_ = super().list(request, *args, **kwargs)
        self.logger.info("Successfully retrieved")
        return list_


""" --- Delete views --- """


class DeleteAccountView(AuthorizationTokenMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        header_token, error_response = self._get_token_from_header(auth_header)
        if error_response:
            return error_response

        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=request.META.get("HTTP_USER_AGENT"))
            if header_token == token.key:
                user = CustomUser.objects.get(username=request.user.username)
                user.delete()

                self.logger.info("Successfully deleted account")
                return Response({"detail": "Successfully deleted account."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Token not found")
            return self._error_response("Token does not exist.", status.HTTP_404_NOT_FOUND)

        return self._error_response("Bad request")


class DeleteAnotherTokensView(AuthorizationTokenMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        header_token, error_response = self._get_token_from_header(auth_header)
        if error_response:
            return error_response

        try:
            another_user_tokens = CustomObtainToken.objects.filter(user=request.user).exclude(key=header_token)
            token_exist = CustomObtainToken.objects.get(key=header_token, user=request.user)
            token_age = timezone.now() - token_exist.created

            if token_age < timedelta(days=3):
                self.logger.warning("Age of the token is no more than 3 days")
                return Response({"detail": "Invalid token age."}, status=status.HTTP_400_BAD_REQUEST)

            if another_user_tokens.exists():
                another_user_tokens.delete()
                self.logger.info("Successfully deleted")
                return Response({"detail": "Other tokens deleted successfully."})
            return Response({"detail": "You have only one active token."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Token does not exist")
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            self.logger.critical("Something went wrong with a critical error")
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
