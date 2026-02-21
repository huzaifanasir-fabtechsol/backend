from django.contrib import admin
from apps.expense.models import Expense, ExpenseCategory, SparePart

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    search_fields = ['name']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'category', 'date', 'user', 'created_at']
    list_filter = ['category', 'date']
    search_fields = ['title', 'description']


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ['name', 'part_number', 'brand', 'user', 'created_at']
    search_fields = ['name', 'part_number', 'brand']
