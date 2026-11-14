from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from submissions.models import TaskSubmission, SubmissionImage, SubmissionReview, ReviewDecision
from submissions.serializers import TaskSubmissionSerializer, SubmissionReviewSerializer
from tasks.models import TaskAssignment, AssignmentStatus
from credits.models import CreditTransaction, TransactionType
from notifications.models import Notification, NotificationType
from accounts.models import StudentProfile

class TaskSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TaskSubmission.objects.select_related(
            'assignment', 'assignment__task', 'assignment__student'
        ).prefetch_related('images', 'reviews').order_by('-submitted_at')

        if user.is_teacher():
            return qs.filter(assignment__task__created_by=user)
        elif user.is_student():
            return qs.filter(assignment__student=user)
        return TaskSubmission.objects.none()

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_task(self, request):
        if not request.user.is_student():
            return Response({'detail': 'Only students can submit tasks.'}, status=status.HTTP_403_FORBIDDEN)

        assignment_id = request.data.get('assignment_id')
        student_comments = request.data.get('student_comments', '')
        images = request.FILES.getlist('images')

        if not assignment_id:
            return Response({'detail': 'assignment_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not images:
            return Response({'detail': 'At least one proof image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TaskAssignment.objects.select_related('task', 'task__created_by').get(id=assignment_id, student=request.user)
        except TaskAssignment.DoesNotExist:
            return Response({'detail': 'Task assignment not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Validate assignment state
        if assignment.status == AssignmentStatus.COMPLETED:
            return Response({'detail': 'Completed tasks cannot be resubmitted.'}, status=status.HTTP_400_BAD_REQUEST)

        # File validation
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        max_size = 10 * 1024 * 1024  # 10 MB per image
        for img in images:
            if img.content_type.lower() not in allowed_types:
                return Response({'detail': f'Unsupported file type: {img.content_type}. Allowed: JPEG, PNG, WebP.'}, status=status.HTTP_400_BAD_REQUEST)
            if img.size > max_size:
                return Response({'detail': f'File {img.name} exceeds maximum size limit of 10MB.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Mark previous submissions as not latest
            TaskSubmission.objects.filter(assignment=assignment).update(is_latest=False)

            # Calculate next version
            current_count = TaskSubmission.objects.filter(assignment=assignment).count()
            next_version = current_count + 1

            submission = TaskSubmission.objects.create(
                assignment=assignment,
                version=next_version,
                student_comments=student_comments,
                is_latest=True
            )

            # Create image objects
            for img in images:
                SubmissionImage.objects.create(submission=submission, image=img)

            # Update assignment status to PENDING_APPROVAL
            assignment.status = AssignmentStatus.PENDING_APPROVAL
            assignment.save()

            # Notify teacher
            Notification.objects.create(
                recipient=assignment.task.created_by,
                title=f"New Submission: {assignment.task.title}",
                message=f"Student {request.user.username} submitted proof for task '{assignment.task.title}'.",
                notification_type=NotificationType.NEW_SUBMISSION,
                related_assignment=assignment
            )

        serializer = TaskSubmissionSerializer(submission, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        submission = self.get_object()
        user = request.user

        if not user.is_teacher() or submission.assignment.task.created_by != user:
            return Response({'detail': 'Not authorized to review this submission.'}, status=status.HTTP_403_FORBIDDEN)

        assignment = submission.assignment

        if assignment.status == AssignmentStatus.COMPLETED:
            return Response({'detail': 'Assignment has already been approved and completed.'}, status=status.HTTP_400_BAD_REQUEST)

        award_points = assignment.task.max_credit_points
        feedback = request.data.get('feedback', 'Approved by teacher.')

        with transaction.atomic():
            # Lock assignment record for update
            assignment = TaskAssignment.objects.select_for_update().get(id=assignment.id)
            if assignment.status == AssignmentStatus.COMPLETED:
                return Response({'detail': 'Assignment already approved.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if credit transaction already exists
            existing_tx = CreditTransaction.objects.filter(
                assignment=assignment, transaction_type=TransactionType.TASK_APPROVAL
            ).exists()

            if not existing_tx:
                # Create credit transaction
                CreditTransaction.objects.create(
                    assignment=assignment,
                    student=assignment.student,
                    amount=award_points,
                    transaction_type=TransactionType.TASK_APPROVAL,
                    created_by=user,
                    reason=f"Approved task: {assignment.task.title}"
                )

                # Update student profile cached total
                profile, _ = StudentProfile.objects.get_or_create(user=assignment.student)
                profile.total_credit_points += award_points
                profile.save()

            # Update assignment
            assignment.status = AssignmentStatus.COMPLETED
            assignment.earned_credits = award_points
            assignment.completed_at = timezone.now()
            assignment.save()

            # Record review
            review = SubmissionReview.objects.create(
                submission=submission,
                reviewer=user,
                decision=ReviewDecision.APPROVED,
                feedback=feedback
            )

            # Notify student
            Notification.objects.create(
                recipient=assignment.student,
                title=f"Task Approved: {assignment.task.title}",
                message=f"Your submission for '{assignment.task.title}' was approved! You earned {award_points} credit points.",
                notification_type=NotificationType.SUBMISSION_APPROVED,
                related_assignment=assignment
            )

        return Response({
            'message': 'Submission approved successfully.',
            'earned_credits': award_points,
            'review': SubmissionReviewSerializer(review).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        submission = self.get_object()
        user = request.user

        if not user.is_teacher() or submission.assignment.task.created_by != user:
            return Response({'detail': 'Not authorized to review this submission.'}, status=status.HTTP_403_FORBIDDEN)

        feedback = request.data.get('feedback', '').strip()
        if not feedback:
            return Response({'detail': 'Feedback notes are required when requesting rework.'}, status=status.HTTP_400_BAD_REQUEST)

        assignment = submission.assignment

        with transaction.atomic():
            assignment = TaskAssignment.objects.select_for_update().get(id=assignment.id)
            assignment.status = AssignmentStatus.REWORK_REQUIRED
            assignment.save()

            review = SubmissionReview.objects.create(
                submission=submission,
                reviewer=user,
                decision=ReviewDecision.REJECTED_REWORK,
                feedback=feedback
            )

            # Notify student
            Notification.objects.create(
                recipient=assignment.student,
                title=f"Rework Required: {assignment.task.title}",
                message=f"Teacher feedback: {feedback}",
                notification_type=NotificationType.REWORK_REQUIRED,
                related_assignment=assignment
            )

        return Response({
            'message': 'Submission marked for rework.',
            'review': SubmissionReviewSerializer(review).data
        }, status=status.HTTP_200_OK)
