from django.db import models
from django.conf import settings
import random
import string

def generate_join_code():
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return ''.join(random.choices(chars, k=6))

class Classroom(models.Model):
    name = models.CharField(max_length=150)
    section = models.CharField(max_length=50, blank=True, default='A')
    academic_year = models.CharField(max_length=50, blank=True, default='2026-2027')
    description = models.TextField(blank=True, default='')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_classes')
    code = models.CharField(max_length=20, unique=True, blank=True)
    is_joining_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.section:
            self.section = 'A'
        if not self.academic_year:
            self.academic_year = '2026-2027'
        if not self.code:
            self.code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        while True:
            code = "STM" + generate_join_code()[:3]
            if not Classroom.objects.filter(code=code).exists():
                return code

    def regenerate_code(self):
        self.code = self._generate_unique_code()
        self.save()
        return self.code

    def __str__(self):
        return f"{self.name} - {self.section} ({self.code})"

class ClassEnrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='class_enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('classroom', 'student')

    def __str__(self):
        return f"{self.student.username} in {self.classroom.name}"

class ClassJoinRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='join_requests')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='class_join_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('classroom', 'student')

    def __str__(self):
        return f"{self.student.username} -> {self.classroom.name} ({self.status})"
