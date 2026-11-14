from rest_framework.routers import DefaultRouter
from submissions.views import TaskSubmissionViewSet

router = DefaultRouter()
router.register(r'submissions', TaskSubmissionViewSet, basename='submission')

urlpatterns = router.urls
