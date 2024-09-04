import hashlib
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from storeapi.models import Product


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


class UserNFTBackpack(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_backpack")
    products = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="user_products")
