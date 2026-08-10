from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """A user's own profile — 'email' is intentionally read-only (identity, not editable here)."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "department", "phone", "role"]
        read_only_fields = ["id", "email", "role"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Full user record for the admin "Users" directory, including role management."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "department", "phone", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "full_name", "department", "role"]

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AccessTokenSerializer(serializers.Serializer):
    """Response shape for /auth/refresh/ — a fresh access token only (the
    refresh token itself travels exclusively via the httpOnly cookie)."""

    access = serializers.CharField(read_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        password_validation.validate_password(value, user=self.context["request"].user)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
