from django.db import models
from django.conf import settings
from classes.models import Classroom

class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'

class AssignmentStatus(models.TextChoices):
    ASSIGNED = 'ASSIGNED', 'Assigned'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    REWORK_REQUIRED = 'REWORK_REQUIRED', 'Rework Required'
    COMPLETED = 'COMPLETED', 'Completed'

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    instructions = models.TextField(blank=True, default='')
    category = models.CharField(max_length=100, default='General')
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    max_credit_points = models.PositiveIntegerField(default=10)
    due_date = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tasks')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_assignments')
    status = models.CharField(max_length=30, choices=AssignmentStatus.choices, default=AssignmentStatus.ASSIGNED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    earned_credits = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('task', 'student')

    def __str__(self):
        return f"{self.task.title} -> {self.student.username} ({self.status})"
