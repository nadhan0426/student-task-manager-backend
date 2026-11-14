from rest_framework.routers import DefaultRouter
from tasks.views import TaskViewSet, TaskAssignmentViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'assignments', TaskAssignmentViewSet, basename='task-assignment')

urlpatterns = router.urls
