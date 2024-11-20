import secrets
import uuid

from django.db import models

from core import settings


class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_wallet")
    address = models.CharField(max_length=64, unique=True, db_index=True)
    wallet_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

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


class WalletToWalletTransaction(models.Model):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_from")
    user_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_to")
    wallet_addr_from = models.CharField(max_length=185)
    wallet_addr_to = models.CharField(max_length=185)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(user_from=models.F("user_to")), name="prevent_self_transfer"),
            models.CheckConstraint(
                check=~models.Q(wallet_addr_from=models.F("wallet_addr_to")), name="prevent_same_wallet_transfer"
            ),
        ]

    def __str__(self):
        return f"Transaction {self.transaction_id} from {self.wallet_addr_from} to {self.wallet_addr_to}"


class PaymentTransaction(models.Model):
    transaction_id = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_payment_transaction"
    )
    user_wallet_addr = models.CharField(max_length=185)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    invoice_id = models.CharField(max_length=128)
    timestamp = models.DateTimeField(auto_now=True)
