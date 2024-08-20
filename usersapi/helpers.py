import hashlib
import secrets

from usersapi.models import CustomObtainToken


def generate_key(old_token):
    while True:
        random_string = secrets.token_bytes(20)
        raw_key = f"{old_token.user}{old_token.user_agent}{old_token.ip_address}{random_string}"
        token = hashlib.sha256(raw_key.encode()).hexdigest()

        if not CustomObtainToken.objects.filter(key=token).exists():
            break

    return token
