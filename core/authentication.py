from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from usersapi.models import CustomObtainToken


class CustomObtainTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None

        try:
            token_type, key = auth_header.split(" ")
            if token_type != "Token":
                raise AuthenticationFailed("Invalid Token header")

            token = CustomObtainToken.objects.get(key=key)
        except (ValueError, CustomObtainToken.DoesNotExist):
            raise AuthenticationFailed("Invalid Token")

        return (token.user, token)
