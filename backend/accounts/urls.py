from django.urls import path
from .views import (
    ConfirmForgotPasswordView,
    ForgotPasswordView,
    LoginView,
    MeView,
    RegisterView,
    ResendVerificationView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh-short"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("confirm-forgot-password/", ConfirmForgotPasswordView.as_view(), name="confirm-forgot-password"),
    path("me/", MeView.as_view(), name="me"),
]
