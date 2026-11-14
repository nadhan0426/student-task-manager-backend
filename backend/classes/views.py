from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from classes.models import Classroom, ClassEnrollment
from classes.serializers import ClassroomSerializer, ClassEnrollmentSerializer
from accounts.permissions import IsApprovedTeacher, IsStudentUser
from accounts.serializers import UserSerializer

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
        identifier = request.data.get('identifier')  # username or email or student_id
        if not identifier:
            return Response({'detail': 'Student username, email or ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        student = User.objects.filter(role='STUDENT').filter(
            models.Q(username__iexact=identifier) |
            models.Q(email__iexact=identifier) |
            models.Q(student_profile__student_id_number__iexact=identifier)
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

        return Response(ClassEnrollmentSerializer(enrollment).data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsApprovedTeacher])
    def students(self, request, pk=None):
        classroom = self.get_object()
        enrollments = ClassEnrollment.objects.filter(classroom=classroom, is_active=True).select_related('student', 'student__student_profile')
        students = [e.student for e in enrollments]
        return Response(UserSerializer(students, many=True).data)

    @action(detail=False, methods=['post'], permission_classes=[IsStudentUser])
    def join_by_code(self, request):
        code = request.data.get('code', '').strip().upper()
        try:
            classroom = Classroom.objects.get(code=code)
        except Classroom.DoesNotExist:
            return Response({'detail': 'Invalid class code.'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, created = ClassEnrollment.objects.get_or_create(
            classroom=classroom,
            student=request.user,
            defaults={'is_active': True}
        )
        if not created and not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save()

        return Response(ClassroomSerializer(classroom).data, status=status.HTTP_200_OK)
