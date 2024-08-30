from cryptography.fernet import Fernet
from core import settings

ciper = Fernet(settings.ENCRYPTION_KEY)


def encrypt_data(data: str) -> str:
    encrypted_data = ciper.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(data: str) -> str:
    decrypted_data = ciper.decrypt(data.encode())
    return decrypted_data.decode()
