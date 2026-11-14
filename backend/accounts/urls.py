from django.urls import path
from accounts.views import (
    RegisterView, LoginView, FirebaseAuthLoginView,
    ProfileView, PasswordResetRequestView, PasswordResetConfirmView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('firebase-login/', FirebaseAuthLoginView.as_view(), name='auth-firebase-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('profile/', ProfileView.as_view(), name='auth-profile'),
    path('forgot-password/', PasswordResetRequestView.as_view(), name='auth-forgot-password'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='auth-reset-password'),
]
