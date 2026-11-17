from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from classes.models import Classroom, ClassEnrollment, ClassJoinRequest
from classes.serializers import ClassroomSerializer, ClassEnrollmentSerializer, ClassJoinRequestSerializer
from accounts.permissions import IsApprovedTeacher, IsStudentUser
from accounts.serializers import UserSerializer
from notifications.models import Notification

User = get_user_model()

class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_teacher():
            return Classroom.objects.filter(teacher=user).order_by('-created_at')
        elif user.is_student():
            enrolled_ids = ClassEnrollment.objects.filter(student=user, is_active=True).values_list('classroom_id', flat=True)
            return Classroom.objects.filter(id__in=enrolled_ids).order_by('-created_at')
        return Classroom.objects.none()

    def perform_create(self, serializer):
        if not self.request.user.is_teacher():
            raise permissions.PermissionDenied("Only teachers can create classrooms.")
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedTeacher])
    def add_student(self, request, pk=None):
        classroom = self.get_object()
        identifier = request.data.get('identifier')
        if not identifier:
            return Response({'detail': 'Student username or email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        student = User.objects.filter(role='STUDENT').filter(
            models.Q(username__iexact=identifier) |
            models.Q(email__iexact=identifier)
        ).first()

        if not student:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, created = ClassEnrollment.objects.get_or_create(
            classroom=classroom,
            student=student,
            defaults={'is_active': True}
        )
        if not created and not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save()

        Notification.objects.create(
            recipient=student,
            title="Enrolled in Class",
            message=f"You have been enrolled in '{classroom.name}' by your teacher.",
            notification_type='SYSTEM'
        )

        return Response(ClassEnrollmentSerializer(enrollment).data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsApprovedTeacher])
    def students(self, request, pk=None):
        classroom = self.get_object()
        enrollments = ClassEnrollment.objects.filter(classroom=classroom, is_active=True).select_related('student', 'student__student_profile')
        students = [e.student for e in enrollments]
        return Response(UserSerializer(students, many=True).data)

    @action(detail=False, methods=['post'], permission_classes=[IsStudentUser])
    def check_code(self, request):
        code = request.data.get('code', '').strip().upper()
        if not code:
            return Response({'detail': 'Class code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            classroom = Classroom.objects.get(code=code)
        except Classroom.DoesNotExist:
            return Response({'detail': 'Invalid class join code.'}, status=status.HTTP_404_NOT_FOUND)

        if not classroom.is_joining_enabled:
            return Response({'detail': 'Joining for this class has been disabled by the teacher.'}, status=status.HTTP_400_BAD_REQUEST)

        if ClassEnrollment.objects.filter(classroom=classroom, student=request.user, is_active=True).exists():
            return Response({'detail': 'You are already enrolled in this class.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ClassroomSerializer(classroom).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsStudentUser])
    def request_join(self, request):
        code = request.data.get('code', '').strip().upper()
        if not code:
            return Response({'detail': 'Class code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            classroom = Classroom.objects.get(code=code)
        except Classroom.DoesNotExist:
            return Response({'detail': 'Invalid class join code.'}, status=status.HTTP_404_NOT_FOUND)

        if not classroom.is_joining_enabled:
            return Response({'detail': 'Joining for this class is disabled.'}, status=status.HTTP_400_BAD_REQUEST)

        if ClassEnrollment.objects.filter(classroom=classroom, student=request.user, is_active=True).exists():
            return Response({'detail': 'You are already enrolled in this class.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_req = ClassJoinRequest.objects.filter(classroom=classroom, student=request.user).first()
        if existing_req:
            if existing_req.status == 'PENDING':
                return Response({'detail': 'You already have a pending join request for this class.'}, status=status.HTTP_400_BAD_REQUEST)
            elif existing_req.status == 'APPROVED':
                return Response({'detail': 'You are already approved for this class.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                existing_req.status = 'PENDING'
                existing_req.requested_at = timezone.now()
                existing_req.save()
                join_req = existing_req
        else:
            join_req = ClassJoinRequest.objects.create(classroom=classroom, student=request.user, status='PENDING')

        Notification.objects.create(
            recipient=classroom.teacher,
            title="New Class Join Request",
            message=f"{request.user.first_name or request.user.username} requested to join '{classroom.name}'.",
            notification_type='SYSTEM'
        )

        return Response(ClassJoinRequestSerializer(join_req).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsApprovedTeacher])
    def pending_requests(self, request):
        managed_classes = Classroom.objects.filter(teacher=request.user)
        requests = ClassJoinRequest.objects.filter(
            classroom__in=managed_classes, status='PENDING'
        ).select_related('student', 'classroom').order_by('-requested_at')
        return Response(ClassJoinRequestSerializer(requests, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedTeacher])
    def approve_request(self, request, pk=None):
        classroom = self.get_object()
        request_id = request.data.get('request_id')
        try:
            join_req = ClassJoinRequest.objects.get(id=request_id, classroom=classroom)
        except ClassJoinRequest.DoesNotExist:
            return Response({'detail': 'Join request not found.'}, status=status.HTTP_404_NOT_FOUND)

        join_req.status = 'APPROVED'
        join_req.reviewed_at = timezone.now()
        join_req.save()

        ClassEnrollment.objects.get_or_create(
            classroom=classroom,
            student=join_req.student,
            defaults={'is_active': True}
        )

        Notification.objects.create(
            recipient=join_req.student,
            title="Join Request Approved",
            message=f"Your request to join '{classroom.name}' has been approved by your teacher!",
            notification_type='SYSTEM'
        )

        return Response(ClassJoinRequestSerializer(join_req).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedTeacher])
    def reject_request(self, request, pk=None):
        classroom = self.get_object()
        request_id = request.data.get('request_id')
        try:
            join_req = ClassJoinRequest.objects.get(id=request_id, classroom=classroom)
        except ClassJoinRequest.DoesNotExist:
            return Response({'detail': 'Join request not found.'}, status=status.HTTP_404_NOT_FOUND)

        join_req.status = 'REJECTED'
        join_req.reviewed_at = timezone.now()
        join_req.save()

        Notification.objects.create(
            recipient=join_req.student,
            title="Join Request Status",
            message=f"Your request to join '{classroom.name}' was not approved.",
            notification_type='SYSTEM'
        )

        return Response(ClassJoinRequestSerializer(join_req).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedTeacher])
    def regenerate_code(self, request, pk=None):
        classroom = self.get_object()
        new_code = classroom.regenerate_code()
        return Response({'code': new_code, 'detail': 'Join code successfully regenerated.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprovedTeacher])
    def toggle_joining(self, request, pk=None):
        classroom = self.get_object()
        classroom.is_joining_enabled = not classroom.is_joining_enabled
        classroom.save()
        return Response({'is_joining_enabled': classroom.is_joining_enabled}, status=status.HTTP_200_OK)
