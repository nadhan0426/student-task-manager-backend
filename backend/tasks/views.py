from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model
from tasks.models import Task, TaskAssignment, AssignmentStatus
from tasks.serializers import TaskSerializer, TaskAssignmentSerializer, TaskCreateSerializer
from classes.models import Classroom, ClassEnrollment
from notifications.models import Notification, NotificationType

User = get_user_model()

class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_teacher():
            return Task.objects.filter(created_by=user).order_by('-created_at')
        elif user.is_student():
            task_ids = TaskAssignment.objects.filter(student=user).values_list('task_id', flat=True)
            return Task.objects.filter(id__in=task_ids, is_archived=False).order_by('due_date')
        return Task.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        if not self.request.user.is_teacher():
            raise permissions.PermissionDenied("Only teachers can create tasks.")

        student_ids = serializer.validated_data.pop('student_ids', [])
        assign_to_class = serializer.validated_data.pop('assign_to_class', False)

        task = serializer.save(created_by=self.request.user)

        target_students = set()

        if assign_to_class and task.classroom:
            class_students = ClassEnrollment.objects.filter(
                classroom=task.classroom, is_active=True
            ).values_list('student_id', flat=True)
            target_students.update(class_students)

        if student_ids:
            valid_students = User.objects.filter(id__in=student_ids, role='STUDENT').values_list('id', flat=True)
            target_students.update(valid_students)

        # Create individual TaskAssignment records for each student
        assignments = []
        notifications = []
        for student_id in target_students:
            assignment, created = TaskAssignment.objects.get_or_create(
                task=task,
                student_id=student_id,
                defaults={'status': AssignmentStatus.ASSIGNED}
            )
            if created:
                assignments.append(assignment)
                notifications.append(Notification(
                    recipient_id=student_id,
                    title=f"New Task Assigned: {task.title}",
                    message=f"You have been assigned task '{task.title}' due on {task.due_date.strftime('%b %d, %Y %H:%M')}.",
                    notification_type=NotificationType.TASK_ASSIGNED,
                    related_assignment=assignment
                ))

        if notifications:
            Notification.objects.bulk_create(notifications)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def assign_students(self, request, pk=None):
        task = self.get_object()
        if not request.user.is_teacher() or task.created_by != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        student_ids = request.data.get('student_ids', [])
        assign_all_class = request.data.get('assign_all_class', False)

        target_students = set()
        if assign_all_class and task.classroom:
            class_students = ClassEnrollment.objects.filter(
                classroom=task.classroom, is_active=True
            ).values_list('student_id', flat=True)
            target_students.update(class_students)

        if student_ids:
            valid_students = User.objects.filter(id__in=student_ids, role='STUDENT').values_list('id', flat=True)
            target_students.update(valid_students)

        created_count = 0
        for student_id in target_students:
            assignment, created = TaskAssignment.objects.get_or_create(
                task=task,
                student_id=student_id,
                defaults={'status': AssignmentStatus.ASSIGNED}
            )
            if created:
                created_count += 1
                Notification.objects.create(
                    recipient_id=student_id,
                    title=f"New Task Assigned: {task.title}",
                    message=f"You have been assigned task '{task.title}'.",
                    notification_type=NotificationType.TASK_ASSIGNED,
                    related_assignment=assignment
                )

        return Response({'message': f'Assigned to {created_count} new student(s).'}, status=status.HTTP_200_OK)

class TaskAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TaskAssignment.objects.select_related('task', 'student', 'task__created_by').order_by('-assigned_at')
        if user.is_teacher():
            return qs.filter(task__created_by=user)
        elif user.is_student():
            return qs.filter(student=user)
        return TaskAssignment.objects.none()

    @action(detail=True, methods=['post'])
    def start_task(self, request, pk=None):
        assignment = self.get_object()
        if assignment.student != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        if assignment.status == AssignmentStatus.ASSIGNED:
            assignment.status = AssignmentStatus.IN_PROGRESS
            assignment.started_at = timezone.now()
            assignment.save()

        return Response(TaskAssignmentSerializer(assignment).data)
