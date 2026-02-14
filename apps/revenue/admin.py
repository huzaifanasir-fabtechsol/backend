from django.contrib import admin
from apps.revenue.models import CarCategory, Car, Order, OrderItem

@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    search_fields = ['name']

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'chassis_number', 'year', 'category', 'user', 'created_at']
    search_fields = ['name', 'model', 'chassis_number']
    list_filter = ['year', 'category']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_number', 'transaction_type', 'customer_name', 'total_amount', 'transaction_date', 'user', 'created_at']
    search_fields = ['order_number', 'customer_name']
    list_filter = ['transaction_type', 'transaction_date']
    inlines = [OrderItemInline]
