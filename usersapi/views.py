import logging
from datetime import timedelta

from django.contrib.auth import authenticate
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
from usersapi.models import CustomObtainToken, CustomUser
from usersapi.serializers import CustomObtainTokenSerializer

""" --- Registration | Login | Logout """


class RegisterView(generics.CreateAPIView, GenericViewSet):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer


class LoginWithObtainAuthToken(APIView):
    logger = logging.getLogger()

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_addr = request.META.get("REMOTE_ADDR")

        if not username or not password:
            self.logger.error("Missing username or password")
            return Response(
                {"error": "To login you must provide both username and password"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not user:
            self.logger.error("The user attempted to send an invalid username or password")
            return Response({"error": "Invalid password or username"}, status=status.HTTP_400_BAD_REQUEST)

        token, created = CustomObtainToken.objects.get_or_create(
            user=user,
            user_agent=user_agent,
            ip_address=ip_addr,
        )
        if token:
            token.status = "Online"
            token.save()

        self.logger.info("The user logged in successfully")
        return Response({"Token": token.key, "user_agent": token.user_agent}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT")
        user_ip_addr = request.META.get("REMOTE_ADDR")
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


class RotateTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        user_agent = request.META.get("HTTP_USER_AGENT")
        user_ip_addr = request.META.get("REMOTE_ADDR")

        if not auth_header or not auth_header.startswith("Token "):
            self.logger.error("Invalid Token")
            return Response(
                {"detail": "Authorization header is missing or invalid."}, status=status.HTTP_400_BAD_REQUEST
            )

        header_token = auth_header.split()[1]
        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=user_agent, ip_address=user_ip_addr)
            if header_token == token.key and token.status == "Online":
                token.key = generate_key(token)
                token.save()

                self.logger.info("Successfully rotated")
                return Response({"new_token": token.key}, status=status.HTTP_200_OK)
            else:
                self.logger.warning("Token is not owned by the user or its status is Offline")
                return Response(
                    {"detail": "Provided token does not match the user's token or token is Offline."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Token does not exist")
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)


""" --- Get views --- """


class GetAllActiveSessionsView(generics.ListAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = paginations.OnlyFiveElementsPagination
    serializer_class = CustomObtainTokenSerializer
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


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        header_token = request.headers.get("Authorization").split()[1]

        if not header_token:
            self.logger.error("No token provided")
            return Response({"detail": "The token has not been transferred."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=request.META.get("HTTP_USER_AGENT"))
            if header_token == token.key:
                user = CustomUser.objects.get(username=request.user.username)
                user.delete()

                self.logger.info("Successfully deleted account")
                return Response({"detail": "Successfully deleted account."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            self.logger.error("Token not found")
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)


class DeleteAnotherTokensView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            self.logger.error("No token provided")
            return Response({"detail": "Missed authorization token."}, status=status.HTTP_403_FORBIDDEN)

        try:
            header_token = auth_header.split(" ")[1]
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
