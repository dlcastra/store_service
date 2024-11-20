import requests
from cryptography.fernet import Fernet
from django.urls import reverse

from core import settings

ciper = Fernet(settings.ENCRYPTION_KEY)


def encrypt_data(data: str) -> str:
    encrypted_data = ciper.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(data: str) -> str:
    decrypted_data = ciper.decrypt(data.encode())
    return decrypted_data.decode()


def get_node_url() -> str | None:
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        response.raise_for_status()
        tunnels: list = response.json().get("tunnels", [])
        return tunnels[0]["public_url"]

    except requests.RequestException as e:
        print(f"Error fetching ngrok URL: {e}")
        return None


def setup_url(request) -> str:
    relative_url = reverse("payment_webhook")
    absolute_url = request.build_absolute_uri(relative_url)

    return absolute_url


if __name__ == "__main__":
    print(get_node_url())
