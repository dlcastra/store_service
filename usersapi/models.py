from django.db import models
from rest_framework.authtoken.models import Token


class CustomObtainToken(Token):
    user_agent = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} - {self.key}"
