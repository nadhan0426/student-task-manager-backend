from rest_framework.routers import DefaultRouter
from classes.views import ClassroomViewSet

router = DefaultRouter()
router.register(r'classrooms', ClassroomViewSet, basename='classroom')

urlpatterns = router.urls
