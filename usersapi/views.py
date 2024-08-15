from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

from usersapi import paginations
from usersapi import serializers
from usersapi.filters import CustomTokenFilter
from usersapi.models import CustomObtainToken
from usersapi.serializers import CustomObtainTokenSerializer


class RegisterView(generics.CreateAPIView, GenericViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer


class LoginWithObtainAuthToken(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_addr = request.META.get("REMOTE_ADDR")

        token, created = CustomObtainToken.objects.get_or_create(
            user=user,
            user_agent=user_agent,
            ip_address=ip_addr,
        )

        return Response({"Token": token.key, "user_agent": token.user_agent}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT")
        user_ip_addr = request.META.get("REMOTE_ADDR")
        try:
            token = CustomObtainToken.objects.get(user=request.user, user_agent=user_agent, ip_address=user_ip_addr)
            token.delete()

            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            return Response({"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND)


class EditUserDataView(generics.RetrieveUpdateAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def get_object(self):
        return self.request.user


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        header_token = request.headers.get("Authorization").split()[1]

        if not header_token:
            return Response({"detail": "The token has not been transferred."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = CustomObtainToken.objects.get(user=request.user)
            if header_token == token.key:
                user = User.objects.get(username=request.user.username)
                user.delete()

                return Response({"detail": "Successfully deleted account."}, status=status.HTTP_200_OK)

        except CustomObtainToken.DoesNotExist:
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)


class RotateTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response(
                {"detail": "Authorization header is missing or invalid."}, status=status.HTTP_400_BAD_REQUEST
            )

        header_token = auth_header.split()[1]
        try:
            user_agent = request.META.get("HTTP_USER_AGENT")
            user_ip_addr = request.META.get("REMOTE_ADDR")
            token = CustomObtainToken.objects.get(user=request.user, user_agent=user_agent, ip_address=user_ip_addr)

            if header_token == token.key:
                token.delete()
                new_token = CustomObtainToken.objects.create(
                    user=request.user, user_agent=user_agent, ip_address=user_ip_addr
                )

                return Response({"new_token": new_token.key}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"detail": "Provided token does not match the user's token."}, status=status.HTTP_400_BAD_REQUEST
                )

        except CustomObtainToken.DoesNotExist:
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)


class GetAllActiveSessionsView(generics.ListAPIView, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = paginations.OnlyFiveElementsPagination
    serializer_class = CustomObtainTokenSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = CustomTokenFilter

    def get_queryset(self):
        user = self.request.user
        queryset = CustomObtainToken.objects.filter(user=user)
        return queryset

    def get(self, request, *args, **kwargs):
        tokens = self.filter_queryset(self.get_queryset())
        if not tokens.exists():
            return Response({"detail": "No active sessions found."}, status=status.HTTP_404_NOT_FOUND)

        sessions = [{"token": token.key, "created_at": token.created} for token in tokens]
        return Response({"sessions": sessions}, status=status.HTTP_200_OK)


class DeleteAnotherTokensView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response({"detail": "Missed authorization token."}, status=status.HTTP_403_FORBIDDEN)

        try:
            header_token = auth_header.split(" ")[1]
            __token_exist = CustomObtainToken.objects.get(key=header_token, user=request.user)

            another_user_tokens = CustomObtainToken.objects.filter(user=request.user).exclude(key=header_token)
            if another_user_tokens.exists():
                return Response({"detail": "You have only one active token."}, status=status.HTTP_200_OK)
            else:
                another_user_tokens.delete()
                return Response({"detail": "Other tokens deleted successfully."})

        except CustomObtainToken.DoesNotExist:
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
