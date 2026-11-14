from django.db import models
from django.conf import settings
from tasks.models import TaskAssignment

class NotificationType(models.TextChoices):
    TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task Assigned'
    DEADLINE_APPROACHING = 'DEADLINE_APPROACHING', 'Deadline Approaching'
    SUBMISSION_APPROVED = 'SUBMISSION_APPROVED', 'Submission Approved'
    SUBMISSION_REJECTED = 'SUBMISSION_REJECTED', 'Submission Rejected'
    REWORK_REQUIRED = 'REWORK_REQUIRED', 'Rework Required'
    NEW_SUBMISSION = 'NEW_SUBMISSION', 'New Submission'
    CREDIT_AWARDED = 'CREDIT_AWARDED', 'Credit Awarded'
    OVERDUE_ALERT = 'OVERDUE_ALERT', 'Overdue Alert'

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    related_assignment = models.ForeignKey(TaskAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"
