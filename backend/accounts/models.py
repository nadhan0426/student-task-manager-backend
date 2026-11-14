from django.db import models
from django.contrib.auth.models import AbstractUser

class UserRole(models.TextChoices):
    TEACHER = 'TEACHER', 'Teacher'
    STUDENT = 'STUDENT', 'Student'

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    is_approved_teacher = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def is_teacher(self):
        return self.role == UserRole.TEACHER and self.is_approved_teacher

    def is_student(self):
        return self.role == UserRole.STUDENT

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    department = models.CharField(max_length=100, blank=True, default='')
    bio = models.TextField(blank=True, default='')

    def __str__(self):
        return f"TeacherProfile ({self.user.username})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id_number = models.CharField(max_length=50, blank=True, default='')
    total_credit_points = models.IntegerField(default=0)

    def __str__(self):
        return f"StudentProfile ({self.user.username})"

class TeacherInvitationCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"InviteCode: {self.code} (Used: {self.is_used})"
