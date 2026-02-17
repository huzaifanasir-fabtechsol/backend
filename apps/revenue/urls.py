from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.revenue.views import CarCategoryViewSet, CarViewSet, OrderViewSet, OrderItemViewSet, CustomerViewSet, CompanyAccountViewSet, AuctionViewSet
from apps.revenue.translate_views import translate_text, translate_batch

router = DefaultRouter()
router.register('categories', CarCategoryViewSet, basename='category')
router.register('cars', CarViewSet, basename='car')
router.register('orders', OrderViewSet, basename='order')
router.register('order-items', OrderItemViewSet, basename='order-item')
router.register('customers', CustomerViewSet, basename='customer')
router.register('company-accounts', CompanyAccountViewSet, basename='company-account')
router.register('auctions', AuctionViewSet, basename='auction')

urlpatterns = [
    path('', include(router.urls)),
    path('orders/dashboard/', OrderViewSet.as_view({'get': 'dashboard'}), name='order-dashboard'),
    path('translate/', translate_text, name='translate'),
    path('translate-batch/', translate_batch, name='translate-batch'),
]
