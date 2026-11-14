from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import UserRole, StudentProfile
from tasks.models import Task, TaskAssignment, AssignmentStatus
from submissions.models import TaskSubmission, SubmissionImage
from credits.models import CreditTransaction, TransactionType

User = get_user_model()

class CreditAndApprovalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='prof', email='prof@example.com', password='password123',
            role=UserRole.TEACHER, is_approved_teacher=True
        )
        self.student_a = User.objects.create_user(
            username='studa', email='studa@example.com', password='password123',
            role=UserRole.STUDENT
        )
        StudentProfile.objects.create(user=self.student_a)

        self.student_b = User.objects.create_user(
            username='studb', email='studb@example.com', password='password123',
            role=UserRole.STUDENT
        )
        StudentProfile.objects.create(user=self.student_b)

        self.task = Task.objects.create(
            title='Math Homework',
            description='Solve problems 1-10',
            max_credit_points=50,
            due_date=timezone.now() + timezone.timedelta(days=2),
            created_by=self.teacher
        )

        self.assignment_a = TaskAssignment.objects.create(task=self.task, student=self.student_a)
        self.assignment_b = TaskAssignment.objects.create(task=self.task, student=self.student_b)

        self.submission_a = TaskSubmission.objects.create(
            assignment=self.assignment_a, version=1, student_comments='Done!'
        )

    def test_approval_awards_credits_only_to_approved_student(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(f'/api/submissions/{self.submission_a.id}/approve/', {
            'feedback': 'Great work!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assignment_a.refresh_from_db()
        self.student_a.student_profile.refresh_from_db()
        self.assertEqual(self.assignment_a.status, AssignmentStatus.COMPLETED)
        self.assertEqual(self.assignment_a.earned_credits, 50)
        self.assertEqual(self.student_a.student_profile.total_credit_points, 50)

        # Student B must be unaffected
        self.assignment_b.refresh_from_db()
        self.student_b.student_profile.refresh_from_db()
        self.assertEqual(self.assignment_b.status, AssignmentStatus.ASSIGNED)
        self.assertEqual(self.assignment_b.earned_credits, 0)
        self.assertEqual(self.student_b.student_profile.total_credit_points, 0)

    def test_duplicate_approval_does_not_duplicate_credits(self):
        self.client.force_authenticate(user=self.teacher)
        self.client.post(f'/api/submissions/{self.submission_a.id}/approve/')

        # Second approval attempt
        response2 = self.client.post(f'/api/submissions/{self.submission_a.id}/approve/')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        self.student_a.student_profile.refresh_from_db()
        self.assertEqual(self.student_a.student_profile.total_credit_points, 50)
        self.assertEqual(CreditTransaction.objects.filter(student=self.student_a).count(), 1)

    def test_rejection_requires_feedback_and_awards_zero_credits(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(f'/api/submissions/{self.submission_a.id}/reject/', {
            'feedback': ''
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_valid = self.client.post(f'/api/submissions/{self.submission_a.id}/reject/', {
            'feedback': 'Please redo exercise 3.'
        })
        self.assertEqual(response_valid.status_code, status.HTTP_200_OK)

        self.assignment_a.refresh_from_db()
        self.student_a.student_profile.refresh_from_db()
        self.assertEqual(self.assignment_a.status, AssignmentStatus.REWORK_REQUIRED)
        self.assertEqual(self.student_a.student_profile.total_credit_points, 0)
