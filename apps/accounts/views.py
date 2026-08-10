from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .permissions import IsAdministrator
from .serializers import (
    AccessTokenSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)

COOKIE_NAME = settings.REFRESH_TOKEN_COOKIE_NAME
token_generator = PasswordResetTokenGenerator()


def _set_refresh_cookie(response: Response, refresh_token) -> None:
    response.set_cookie(
        COOKIE_NAME,
        str(refresh_token),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/api/auth/",
    )


def _tokens_response(user: User, status_code: int = status.HTTP_200_OK) -> Response:
    refresh = RefreshToken.for_user(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserSerializer(user).data},
        status=status_code,
    )
    _set_refresh_cookie(response, refresh)
    return response


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _tokens_response(user, status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            raise AuthenticationFailed("Invalid email or password.")
        return _tokens_response(user)


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=None,
        responses={200: AccessTokenSerializer},
        description="Exchanges the httpOnly refresh-token cookie for a new access token. No request body.",
    )
    def post(self, request):
        raw_token = request.COOKIES.get(COOKIE_NAME)
        if not raw_token:
            raise AuthenticationFailed("No refresh token cookie present.")
        try:
            refresh = RefreshToken(raw_token)
        except TokenError as exc:
            raise AuthenticationFailed("Refresh token invalid or expired.") from exc

        access = str(refresh.access_token)
        response = Response({"access": access}, status=status.HTTP_200_OK)

        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
            if settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"]:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            user = User.objects.get(id=refresh["user_id"])
            new_refresh = RefreshToken.for_user(user)
            _set_refresh_cookie(response, new_refresh)

        return response


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Signed out; refresh-token cookie cleared and blacklisted.")},
    )
    def post(self, request):
        raw_token = request.COOKIES.get(COOKIE_NAME)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(COOKIE_NAME, path="/api/auth/")
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={204: OpenApiResponse(description="Password changed.")},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Reset your ChemSafe password",
                message=f"Use this link to reset your password: {reset_url}\n\nIf you didn't request this, ignore this email.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@chemsafe.local"),
                recipient_list=[email],
                fail_silently=True,
            )
        # Always 200 — don't reveal whether an account exists for this email.
        return Response(status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not token_generator.check_token(user, data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["password"])
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_200_OK)


class AdminUserListView(generics.ListAPIView):
    """Admin-only user directory, backing the 'Users' management page."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdministrator]
    queryset = User.objects.all().order_by("full_name", "email")
    pagination_class = None


class AdminUserRoleUpdateView(generics.UpdateAPIView):
    """Admin-only role change for a given user (PATCH {"role": "administrator"|"lab_staff"})."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdministrator]
    queryset = User.objects.all()
    http_method_names = ["patch"]
