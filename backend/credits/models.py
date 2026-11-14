from django.db import models
from django.conf import settings
from tasks.models import TaskAssignment

class TransactionType(models.TextChoices):
    TASK_APPROVAL = 'TASK_APPROVAL', 'Task Approval'
    TEACHER_ADJUSTMENT = 'TEACHER_ADJUSTMENT', 'Teacher Adjustment'
    BONUS = 'BONUS', 'Bonus'

class CreditTransaction(models.Model):
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, null=True, blank=True, related_name='credit_transactions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices, default=TransactionType.TASK_APPROVAL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='awarded_credit_transactions')
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Constraint to ensure no duplicate TASK_APPROVAL credit transactions exist for the same assignment
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'transaction_type'],
                condition=models.Q(transaction_type='TASK_APPROVAL'),
                name='unique_task_approval_credit'
            )
        ]

    def __str__(self):
        return f"{self.amount} Credits -> {self.student.username} ({self.transaction_type})"
