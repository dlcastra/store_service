from django.db import models

from usersapi.models import CustomUser


class Product(models.Model):
    image = models.ImageField(upload_to="products_images/", blank=True)
    name = models.CharField(max_length=127)
    description = models.TextField()
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    release_data = models.DateTimeField(auto_now=True)


class Order(models.Model):
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)
    order_id = models.CharField(max_length=100, unique=True, null=False)
    invoice_url = models.CharField(max_length=100, null=False)
    status = models.CharField(max_length=100, null=False, default="unpaid")


class OrderQuantity(models.Model):
    quantity = models.PositiveIntegerField(default=1)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="oq_products")
