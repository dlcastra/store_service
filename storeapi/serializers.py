from datetime import datetime

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from storeapi.models import Product


class ProductSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, validators=[UniqueValidator(queryset=Product.objects.all())])

    class Meta:
        model = Product
        fields = ["image", "name", "description", "price"]
        extra_kwargs = {"description": {"required": True}, "price": {"required": True}}

    def validate(self, attrs):
        if attrs["description"] is None:
            raise serializers.ValidationError("Description is required")
        if attrs["price"] is None:
            raise serializers.ValidationError("Price is required")
        if attrs["price"] <= 0:
            raise serializers.ValidationError("Price must be more than zero")

        return attrs

    def create(self, validated_data):
        user = self.context["owner"]
        print(user)
        product = Product.objects.create(owner=user, **validated_data)
        return product


class ProductListSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Product
        fields = ["owner", "image", "name", "description", "price", "release_data"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        release_data = ret["release_data"]
        datetime_obj = datetime.strptime(release_data, "%Y-%m-%dT%H:%M:%S.%fZ")
        formatted_release_data = datetime_obj.strftime("%Y-%m-%d")
        ret["release_data"] = formatted_release_data

        return ret
