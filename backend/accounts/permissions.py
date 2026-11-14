from rest_framework import permissions
from accounts.models import UserRole

class IsApprovedTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.TEACHER and
            request.user.is_approved_teacher
        )

class IsStudentUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.STUDENT
        )
