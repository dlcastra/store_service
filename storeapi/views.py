from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import permissions, generics
from rest_framework.viewsets import GenericViewSet

from core import permissions as custom_permissions
from storeapi.models import Product
from storeapi.paginations import ProductPagination
from storeapi.serializers import ProductSerializer, ProductListSerializer
from usersapi.models import CustomObtainToken


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
