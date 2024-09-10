import hashlib
import secrets

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from usersapi.models import CustomObtainToken, CustomUser
from usersapi.tasks import send_email


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=CustomUser.objects.all())])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    referral_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = ["username", "password", "password2", "email", "first_name", "last_name", "referral_code"]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords fields didn't match."})

        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_password(validated_data["password"])

        try:
            referral_code = validated_data.get("referral_code")
            referrer = CustomUser.objects.get(user_own_invite_code=referral_code)
            if referrer:
                user.referral_code = referral_code
                user.amount_bonuses = 50
                referrer.amount_bonuses += 100
                referrer.amount_invitations += 1

                referrer.save()
        except CustomUser.DoesNotExist:
            pass

        user.save()
        send_email.delay(
            email=user.email,
            subject="Registration complete",
            template_name="emails/registration_email.html",
            context={"username": user.username},
        )

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    user_agent = serializers.CharField(required=False, allow_blank=True)
    ip_address = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise serializers.ValidationError("To login you must provide both username and password.")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid username or password.")

        data["user"] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["username", "email", "first_name", "last_name"]


class CustomObtainTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomObtainToken
        fields = ["id", "key", "created", "user_agent", "status"]

    def to_representation(self, instance):
        header_token = self.context.get("header_token")
        ret = super().to_representation(instance)
        random_string = secrets.token_bytes(20)
        raw_key = f"{random_string}{instance.key}{random_string}"

        if instance.key != header_token:
            ret["key"] = hashlib.sha256(raw_key.encode()).hexdigest()
        if instance.status == "Online":
            return ret

        raise serializers.ValidationError({"key": "To see other tokens, the status of your token must be ONLINE"})
