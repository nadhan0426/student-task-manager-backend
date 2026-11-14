from rest_framework.routers import DefaultRouter
from credits.views import CreditTransactionViewSet

router = DefaultRouter()
router.register(r'credits', CreditTransactionViewSet, basename='credit')

urlpatterns = router.urls
