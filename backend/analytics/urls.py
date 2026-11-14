from django.urls import path
from analytics.views import TeacherDashboardAnalyticsView, StudentDashboardAnalyticsView

urlpatterns = [
    path('analytics/teacher-dashboard/', TeacherDashboardAnalyticsView.as_view(), name='teacher-analytics'),
    path('analytics/student-dashboard/', StudentDashboardAnalyticsView.as_view(), name='student-analytics'),
]
