from django.db import models
from apps.account.models import BaseModel, User


class Employee(BaseModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50)
    role = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    employment_start_month = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')

    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.role})"


class Salary(BaseModel):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
    ]

    salary_month = models.CharField(max_length=7)  # YYYY-MM format
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salaries')
    leaves = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')

    class Meta:
        db_table = 'salaries'
        ordering = ['-salary_month', '-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.salary_month}"
