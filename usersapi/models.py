import hashlib

from django.db import models
from django.conf import settings


class CustomObtainToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def generate_key(self):
        raw_key = f"{self.user}{self.user_agent}{self.ip_address}"
        return hashlib.sha1(raw_key.encode()).hexdigest()

    def __str__(self):
        return f"{self.user} - {self.key}"
