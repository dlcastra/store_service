from django.db import models

from core import settings


class Product(models.Model):
    image = models.ImageField(upload_to="products_images/", blank=True)
    name = models.CharField(max_length=127)
    description = models.TextField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    release_data = models.DateTimeField(auto_now=True)
