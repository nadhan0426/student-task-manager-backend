from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth import get_user_model
from credits.models import CreditTransaction, TransactionType
from credits.serializers import CreditTransactionSerializer
from accounts.models import StudentProfile
from notifications.models import Notification, NotificationType

User = get_user_model()

class CreditTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreditTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CreditTransaction.objects.select_related('student', 'created_by', 'assignment', 'assignment__task').order_by('-created_at')
        if user.is_teacher():
            return qs
        elif user.is_student():
            return qs.filter(student=user)
        return CreditTransaction.objects.none()

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def adjust_credits(self, request):
        if not request.user.is_teacher():
            return Response({'detail': 'Only teachers can adjust credit points.'}, status=status.HTTP_403_FORBIDDEN)

        student_id = request.data.get('student_id')
        amount = request.data.get('amount')
        reason = request.data.get('reason', '').strip()

        if not student_id or amount is None:
            return Response({'detail': 'student_id and amount are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reason:
            return Response({'detail': 'Written justification reason is required for manual credit adjustments.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = int(amount)
        except ValueError:
            return Response({'detail': 'Amount must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = User.objects.get(id=student_id, role='STUDENT')
        except User.DoesNotExist:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            tx = CreditTransaction.objects.create(
                student=student,
                amount=amount,
                transaction_type=TransactionType.TEACHER_ADJUSTMENT,
                created_by=request.user,
                reason=reason
            )

            profile, _ = StudentProfile.objects.get_or_create(user=student)
            profile.total_credit_points += amount
            profile.save()

            Notification.objects.create(
                recipient=student,
                title=f"Credit Adjustment: {amount:+d} Credits",
                message=f"Teacher {request.user.username} adjusted your credits by {amount:+d}. Reason: {reason}",
                notification_type=NotificationType.CREDIT_AWARDED
            )

        return Response(CreditTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)
