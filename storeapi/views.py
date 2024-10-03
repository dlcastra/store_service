import logging
import time

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework import permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from core import permissions as custom_permissions
from storeapi.models import Product
from storeapi.paginations import ProductPagination
from storeapi.serializers import ProductSerializer, ProductListSerializer
from usersapi.models import CustomObtainToken, UserNFTBackpack
from wallet.mixins import WalletTransactionMixin


class CreateProductView(generics.CreateAPIView, GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        header_auth = self.request.headers.get("Authorization")
        header_token = header_auth.split(" ")[1]
        user = CustomObtainToken.objects.get(key=header_token).user

        if user:
            context["owner"] = user

        return context


class ProductListView(generics.ListAPIView, GenericViewSet):
    serializer_class = ProductListSerializer
    permission_classes = [custom_permissions.ReadOnly]
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["name", "price"]

    def get_queryset(self):
        queryset = Product.objects.all().order_by("release_data")

        return queryset

    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        time.sleep(1)
        return super().list(request, *args, **kwargs)


class BuyNFT(WalletTransactionMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    logger = logging.getLogger()

    def post(self, request, *args, **kwargs):
        request_user = request.user
        product_instance = get_object_or_404(Product, name=request.data.get("name"))
        wallet_from = self._get_wallet_from_user(request_user)
        wallet_to = self._get_wallet_from_user(product_instance.owner)
        validated_amount = self._validate_amount(product_instance.price)

        if not wallet_from:
            return self._error_response("To make Wallet-To-Wallet transaction you need to create a wallet")
        if not wallet_to:
            return self._error_response("The product owner has not connected the wallet ")
        if product_instance.owner == request_user:
            return self._error_response("You cannot buy your own product.")
        if wallet_from.wallet_balance < validated_amount:
            return self._error_response("Insufficient funds in wallet.")

        self._check_transaction_duplicate(
            request_user, product_instance.owner, wallet_from, wallet_to, validated_amount
        )
        self._perform_transaction(request_user, product_instance.owner, wallet_from, wallet_to, validated_amount)

        user_backpack, created = UserNFTBackpack.objects.update_or_create(
            products=product_instance, defaults={"user": request_user}
        )
        if created:
            self.logger.info(f"New UserNFTBackpack created for user: {request_user}, product: {product_instance.name}")
        else:
            self.logger.info(
                f"Updated existing UserNFTBackpack for user: {request_user}, product: {product_instance.name}"
            )

        product_instance.owner = request_user
        product_instance.save()

        return Response(
            {"message": "Transaction was successful", "Your balance": wallet_from.wallet_balance},
            status=status.HTTP_201_CREATED,
        )
