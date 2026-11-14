from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model
from tasks.models import Task, TaskAssignment, AssignmentStatus
from submissions.models import TaskSubmission
from classes.models import Classroom, ClassEnrollment
from credits.models import CreditTransaction

User = get_user_model()

class TeacherDashboardAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_teacher():
            return Response({'detail': 'Teacher access required.'}, status=status.HTTP_403_FORBIDDEN)

        teacher_tasks = Task.objects.filter(created_by=user)
        teacher_class_ids = Classroom.objects.filter(teacher=user).values_list('id', flat=True)
        enrolled_students_count = ClassEnrollment.objects.filter(classroom_id__in=teacher_class_ids, is_active=True).values('student_id').distinct().count()

        assignments = TaskAssignment.objects.filter(task__in=teacher_tasks)
        now = timezone.now()

        total_tasks = teacher_tasks.count()
        total_assigned = assignments.count()
        pending_submissions = assignments.filter(status=AssignmentStatus.PENDING_APPROVAL).count()
        approved_tasks = assignments.filter(status=AssignmentStatus.COMPLETED).count()
        rejected_tasks = assignments.filter(status=AssignmentStatus.REWORK_REQUIRED).count()

        overdue_tasks = assignments.filter(
            Q(status__in=[AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS, AssignmentStatus.REWORK_REQUIRED]),
            task__due_date__lt=now
        ).count()

        total_credits_awarded = CreditTransaction.objects.filter(
            created_by=user
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Submissions awaiting approval
        awaiting_submissions = TaskSubmission.objects.filter(
            assignment__task__created_by=user,
            assignment__status=AssignmentStatus.PENDING_APPROVAL,
            is_latest=True
        ).select_related('assignment', 'assignment__task', 'assignment__student')[:5]

        recent_submissions_data = [{
            'submission_id': s.id,
            'task_title': s.assignment.task.title,
            'student_name': s.assignment.student.username,
            'submitted_at': s.submitted_at,
            'assignment_id': s.assignment.id
        } for s in awaiting_submissions]

        # Class progress analytics
        classrooms = Classroom.objects.filter(teacher=user)
        class_analytics = []
        for c in classrooms:
            class_tasks = teacher_tasks.filter(classroom=c)
            class_assignments = TaskAssignment.objects.filter(task__in=class_tasks)
            total_class_assign = class_assignments.count()
            completed_class_assign = class_assignments.filter(status=AssignmentStatus.COMPLETED).count()
            completion_rate = round((completed_class_assign / total_class_assign * 100), 1) if total_class_assign > 0 else 0.0

            class_analytics.append({
                'class_id': c.id,
                'class_name': c.name,
                'student_count': c.enrollments.filter(is_active=True).count(),
                'total_assignments': total_class_assign,
                'completed_assignments': completed_class_assign,
                'completion_rate': completion_rate
            })

        return Response({
            'total_students': enrolled_students_count,
            'total_tasks': total_tasks,
            'total_assigned_tasks': total_assigned,
            'pending_submissions': pending_submissions,
            'approved_tasks': approved_tasks,
            'rejected_tasks': rejected_tasks,
            'overdue_tasks': overdue_tasks,
            'total_credit_points_awarded': total_credits_awarded,
            'recent_submissions': recent_submissions_data,
            'class_analytics': class_analytics
        })

class StudentDashboardAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_student():
            return Response({'detail': 'Student access required.'}, status=status.HTTP_403_FORBIDDEN)

        assignments = TaskAssignment.objects.filter(student=user)
        now = timezone.now()

        total_assigned = assignments.count()
        pending_tasks = assignments.filter(status=AssignmentStatus.ASSIGNED).count()
        in_progress_tasks = assignments.filter(status=AssignmentStatus.IN_PROGRESS).count()
        pending_approval_tasks = assignments.filter(status=AssignmentStatus.PENDING_APPROVAL).count()
        rework_required_tasks = assignments.filter(status=AssignmentStatus.REWORK_REQUIRED).count()
        completed_tasks = assignments.filter(status=AssignmentStatus.COMPLETED).count()

        completion_percentage = round((completed_tasks / total_assigned * 100), 1) if total_assigned > 0 else 0.0

        earned_credits = hasattr(user, 'student_profile') and user.student_profile.total_credit_points or 0

        upcoming_deadlines = assignments.filter(
            Q(status__in=[AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS, AssignmentStatus.REWORK_REQUIRED]),
            task__due_date__gte=now
        ).select_related('task').order_by('task__due_date')[:5]

        deadlines_data = [{
            'assignment_id': a.id,
            'task_title': a.task.title,
            'due_date': a.task.due_date,
            'priority': a.task.priority,
            'status': a.status
        } for a in upcoming_deadlines]

        return Response({
            'student_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'total_assigned_tasks': total_assigned,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'pending_approval_tasks': pending_approval_tasks,
            'rework_required_tasks': rework_required_tasks,
            'completed_tasks': completed_tasks,
            'completion_percentage': completion_percentage,
            'earned_credits': earned_credits,
            'upcoming_deadlines': deadlines_data
        })
