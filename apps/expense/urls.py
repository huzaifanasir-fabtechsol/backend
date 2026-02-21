from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.expense.views import ExpenseViewSet, ExpenseCategoryViewSet, RestaurantViewSet, SparePartViewSet

router = DefaultRouter()
router.register('expenses', ExpenseViewSet, basename='expense')
router.register('categories', ExpenseCategoryViewSet, basename='category')
router.register('restaurants', RestaurantViewSet, basename='restaurant')
router.register('spare-parts', SparePartViewSet, basename='spare-part')

urlpatterns = [
    path('', include(router.urls)),
]
