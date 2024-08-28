import hashlib
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    amount_bonuses = models.IntegerField(default=0)
    amount_invitations = models.IntegerField(default=0)
    referral_code = models.CharField(max_length=150, default="")
    user_own_invite_code = models.CharField(max_length=15, unique=True)

    def save(self, *args, **kwargs):
        if not self.user_own_invite_code:
            self.user_own_invite_code = self.generate_user_invite_code()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_user_invite_code():
        return str(uuid.uuid4())[:15]


class CustomObtainToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    status = models.CharField(max_length=15, default="Online", null=False)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def generate_key(self):
        while True:
            random_string = secrets.token_bytes(20)
            raw_key = f"{self.user}{self.user_agent}{self.ip_address}{random_string}"
            token = hashlib.sha256(raw_key.encode()).hexdigest()

            if not CustomObtainToken.objects.filter(key=token).exists():
                break

        return token

    def __str__(self):
        return f"{self.user} - {self.key}"


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
