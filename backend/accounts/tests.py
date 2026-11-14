from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import UserRole

User = get_user_model()

class AccountsSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_student_registration_success(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'student1',
            'email': 'student1@example.com',
            'password': 'password123',
            'role': 'STUDENT'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['role'], 'STUDENT')

    def test_teacher_registration_direct_success(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'teacher1',
            'email': 'teacher1@example.com',
            'password': 'password123',
            'role': 'TEACHER'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['role'], 'TEACHER')
        self.assertTrue(response.data['user']['is_approved_teacher'])

    def test_student_forbidden_on_teacher_analytics(self):
        student = User.objects.create_user(username='std', password='pass', role=UserRole.STUDENT)
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/analytics/teacher-dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
