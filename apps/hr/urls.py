from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.hr.views import EmployeeViewSet, SalaryViewSet

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('salaries', SalaryViewSet, basename='salary')

urlpatterns = [
    path('', include(router.urls)),
]
