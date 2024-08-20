# from django.urls import path
from rest_framework import routers

from storeapi import views

router = routers.DefaultRouter()
router.register(r"create-nft", views.CreateProductView, basename="create-nft")
router.register(r"market", views.ProductListView, basename="market")

urlpatterns = router.urls
