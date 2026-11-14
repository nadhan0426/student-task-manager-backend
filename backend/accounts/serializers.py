from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import UserRole, TeacherProfile, StudentProfile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    total_credit_points = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_approved_teacher', 'phone_number', 'total_credit_points')
        read_only_fields = ('id', 'is_approved_teacher', 'total_credit_points')

    def get_total_credit_points(self, obj):
        if hasattr(obj, 'student_profile'):
            return obj.student_profile.total_credit_points
        return 0

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number')

    def create(self, validated_data):
        password = validated_data.pop('password')
        role = validated_data.get('role', UserRole.STUDENT)

        if role == UserRole.TEACHER:
            validated_data['is_approved_teacher'] = True

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        if role == UserRole.TEACHER:
            TeacherProfile.objects.create(user=user)
        else:
            StudentProfile.objects.create(user=user)

        return user

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    username = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
