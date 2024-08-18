import hashlib
import secrets

from django.db import models
from django.conf import settings


class CustomObtainToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

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
