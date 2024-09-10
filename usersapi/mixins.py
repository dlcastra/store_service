from rest_framework import status
from rest_framework.response import Response


class AuthorizationTokenMixin:
    logger = None

    def _get_token_from_header(self, auth_header):
        if not auth_header or not auth_header.startswith("Token "):
            self.logger.error("Invalid Token")
            return None, Response(
                {"detail": "Authorization header is missing or invalid."}, status=status.HTTP_400_BAD_REQUEST
            )
        return auth_header.split()[1], None

    def _error_response(self, message, response_status=None):
        response_status = status.HTTP_400_BAD_REQUEST if response_status is None else response_status
        return Response({"error": message}, status=response_status)
