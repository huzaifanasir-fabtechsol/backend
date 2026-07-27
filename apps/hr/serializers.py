from rest_framework import serializers
from apps.hr.models import Employee, Salary


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'email', 'phone', 'role', 'address',
            'employment_start_month', 'basic_salary', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        """Email must be globally unique across all employees."""
        qs = Employee.objects.filter(email__iexact=value)
        # On update, exclude the current instance
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An employee with this email already exists.")
        return value.lower()

    def validate_basic_salary(self, value):
        if value < 0:
            raise serializers.ValidationError("Basic salary cannot be negative.")
        return value

    def validate_employment_start_month(self, value):
        return value


class SalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_role = serializers.CharField(source='employee.role', read_only=True)

    class Meta:
        model = Salary
        fields = [
            'id', 'salary_month', 'employee', 'employee_name', 'employee_role',
            'leaves', 'leave_deduction', 'allowances', 'other_deductions',
            'net_amount', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_employee(self, value):
        """Employee must belong to the authenticated admin."""
        request = self.context.get('request')
        if request and value.admin != request.user:
            raise serializers.ValidationError("This employee does not belong to your account.")
        return value

    def validate_salary_month(self, value):
        """Must be YYYY-MM format."""
        import re
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', value):
            raise serializers.ValidationError("Salary month must be in YYYY-MM format (e.g. 2025-07).")
        return value

    def validate(self, attrs):
        leaves = attrs.get('leaves', 0)
        if leaves < 0:
            raise serializers.ValidationError({'leaves': 'Leaves cannot be negative.'})
        leave_deduction = attrs.get('leave_deduction', 0)
        if leave_deduction < 0:
            raise serializers.ValidationError({'leave_deduction': 'Leave deduction cannot be negative.'})
        return attrs
