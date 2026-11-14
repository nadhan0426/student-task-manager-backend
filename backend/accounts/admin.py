from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User, TeacherProfile, StudentProfile, TeacherInvitationCode

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_approved_teacher', 'is_staff')
    list_filter = ('role', 'is_approved_teacher', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Permissions', {'fields': ('role', 'is_approved_teacher', 'phone_number')}),
    )

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id_number', 'total_credit_points')

@admin.register(TeacherInvitationCode)
class TeacherInvitationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_used', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('code',)
