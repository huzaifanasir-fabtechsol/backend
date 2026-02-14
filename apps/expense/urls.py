from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.expense.views import ExpenseViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register('expenses', ExpenseViewSet, basename='expense')
router.register('categories', ExpenseCategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]
