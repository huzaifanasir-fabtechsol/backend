from django.contrib import admin
from apps.hr.models import Employee, Salary


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'role', 'status', 'basic_salary', 'admin']
    list_filter = ['status', 'role']
    search_fields = ['name', 'email', 'phone']


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'salary_month', 'net_amount', 'status', 'admin']
    list_filter = ['status', 'salary_month']
    search_fields = ['employee__name']
