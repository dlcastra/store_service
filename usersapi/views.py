from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from usersapi import serializers
from usersapi.models import CustomObtainToken


class RegisterView(generics.CreateAPIView, GenericViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer


class LoginWithObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        token, created = CustomObtainToken.objects.get_or_create(user=user)
        token.user_agent = request.META.get("HTTP_USER_AGENT")
        token.ip_address = request.META.get("REMOTE_ADDR")
        print(request.META.get("REMOTE_ADDR"))

        return Response({"token": token.key, "user_agent": token.user_agent, "ip_address": token.ip_address})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()

            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

        except Token.DoesNotExist:
            return Response({"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        header_token = request.headers.get("Authorization").split()[1]

        if not header_token:
            return Response({"detail": "The token has not been transferred."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = Token.objects.get(user=request.user)
            if header_token == token.key:
                user = User.objects.get(username=request.user.username)
                user.delete()

                return Response({"detail": "Successfully deleted account."}, status=status.HTTP_200_OK)

        except Token.DoesNotExist:
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)


class RotateTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        header_token = request.headers.get("Authorization").split()[1]
        if not header_token:
            return Response({"detail": "The token has not been transferred."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = Token.objects.get(user=request.user)
            if header_token == token.key:
                token.delete()
                new_token = Token.objects.create(user=request.user)

                return Response({"New token": new_token.key}, status=status.HTTP_200_OK)

        except Token.DoesNotExist:
            return Response({"detail": "Token does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)


class GetAllActiveSessionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tokens = Token.objects.filter(user=request.user)
        if not tokens.exists():
            return Response({"detail": "No active sessions found."}, status=status.HTTP_404_NOT_FOUND)

        sessions = [{"token": token.key, "created_at": token.created} for token in tokens]
        return Response({"sessions": sessions}, status=status.HTTP_200_OK)
