import hashlib
import secrets

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from usersapi.models import CustomObtainToken


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["username", "password", "password2", "email", "first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords fields didn't match."})

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        user.set_password(validated_data["password"])
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class CustomObtainTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomObtainToken
        fields = ["key", "created", "user_agent"]

    def to_representation(self, instance):
        header_token = self.context.get("header_token")
        ret = super().to_representation(instance)
        random_string = secrets.token_bytes(20)
        raw_key = f"{random_string}{instance.key}{random_string}"

        if instance.key != header_token:
            ret["key"] = hashlib.sha256(raw_key.encode()).hexdigest()

        return ret
