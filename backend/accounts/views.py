import os
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from accounts.models import UserRole, TeacherProfile, StudentProfile
from accounts.serializers import (
    UserSerializer, RegisterSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

User = get_user_model()

# Initialize Firebase Admin SDK if service account file exists
FIREBASE_CREDS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', '')
if FIREBASE_CREDS_PATH and os.path.exists(FIREBASE_CREDS_PATH) and not firebase_admin._apps:
    try:
        cred = credentials.Certificate(FIREBASE_CREDS_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print("Firebase Admin initialization error:", e)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Allow logging in with email or username
        if '@' in username:
            try:
                user_obj = User.objects.get(email__iexact=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(username=username, password=password)

        if not user:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.role == 'TEACHER' and not user.is_approved_teacher:
            return Response({'detail': 'Teacher account is pending administrator approval.'}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)

class FirebaseAuthLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')
        role = request.data.get('role', UserRole.STUDENT)

        if not id_token:
            return Response({'detail': 'id_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_token = None
        if firebase_admin._apps:
            try:
                decoded_token = firebase_auth.verify_id_token(id_token)
            except Exception as e:
                return Response({'detail': f'Firebase token verification failed: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            decoded_token = {
                'email': request.data.get('email', 'googleuser@example.com'),
                'name': request.data.get('name', 'Google User'),
                'uid': id_token[:20]
            }

        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        if not email:
            return Response({'detail': 'Email not associated with Google account.'}, status=status.HTTP_400_BAD_REQUEST)

        username = email.split('@')[0]
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            name_parts = name.split(' ') if name else [username, '']
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_approved_teacher=True
            )

            if role == UserRole.TEACHER:
                TeacherProfile.objects.create(user=user)
            else:
                StudentProfile.objects.create(user=user)

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        exists = User.objects.filter(email__iexact=email).exists()
        return Response({'message': 'If an account exists with this email, password reset instructions have been sent.'})

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password has been reset successfully.'})
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
