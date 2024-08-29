import secrets

from django.db import models

from core import settings


class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.CharField(max_length=64, unique=True, db_index=True)
    wallet_balance = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.address:
            self.address = self.create_wallet_addr()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        return secrets.token_hex(32)

    @staticmethod
    def check_key_unique(address):
        return not Wallet.objects.filter(address=address).exists()

    @staticmethod
    def create_wallet_addr():
        while True:
            keys = [Wallet.generate_key() for _ in range(3)]
            unique_keys = [key for key in keys if Wallet.check_key_unique(key)]

            if unique_keys:
                break

        return unique_keys[0]
