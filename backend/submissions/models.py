from django.db import models
from django.conf import settings
from tasks.models import TaskAssignment

class TaskSubmission(models.Model):
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='submissions')
    version = models.PositiveIntegerField(default=1)
    student_comments = models.TextField(blank=True, default='')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=True)

    def __str__(self):
        return f"Submission v{self.version} for Assignment #{self.assignment_id}"

class SubmissionImage(models.Model):
    submission = models.ForeignKey(TaskSubmission, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='submissions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image #{self.id} for Submission #{self.submission_id}"

class ReviewDecision(models.TextChoices):
    APPROVED = 'APPROVED', 'Approved'
    REJECTED_REWORK = 'REJECTED_REWORK', 'Rejected / Rework Required'

class SubmissionReview(models.Model):
    submission = models.ForeignKey(TaskSubmission, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_reviews')
    decision = models.CharField(max_length=30, choices=ReviewDecision.choices)
    feedback = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review ({self.decision}) by {self.reviewer.username} for Submission #{self.submission_id}"
