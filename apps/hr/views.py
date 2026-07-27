from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from apps.hr.models import Employee, Salary
from apps.hr.serializers import EmployeeSerializer, SalarySerializer
from project.pagination import CustomPageNumberPagination


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Employee.objects.filter(admin=self.request.user)

        search = self.request.query_params.get('search', '').strip()
        role = self.request.query_params.get('role', '').strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        if role:
            queryset = queryset.filter(role__iexact=role)

        return queryset

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

    @action(detail=False, methods=['get'], url_path='roles')
    def roles(self, request):
        """Return distinct roles for the authenticated admin's employees."""
        roles = (
            Employee.objects
            .filter(admin=request.user)
            .exclude(role='')
            .values_list('role', flat=True)
            .distinct()
            .order_by('role')
        )
        return Response(list(roles))

    @action(detail=False, methods=['get'], url_path='all')
    def all_employees(self, request):
        """Return all employees (no pagination) for dropdown use in Salary module."""
        employees = Employee.objects.filter(admin=request.user, status='active').order_by('name')
        serializer = self.get_serializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """Toggle employee status between active and inactive."""
        employee = self.get_object()
        employee.status = 'inactive' if employee.status == 'active' else 'active'
        employee.save()
        serializer = self.get_serializer(employee)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='salary-report')
    def salary_report(self, request, pk=None):
        """Return detailed salary report for an employee filtered by year or month."""
        employee = self.get_object()
        user = request.user

        year = request.query_params.get('year', '').strip()
        month = request.query_params.get('month', '').strip()

        queryset = Salary.objects.filter(employee=employee, admin=user)

        if month:
            queryset = queryset.filter(salary_month=month)
        elif year:
            queryset = queryset.filter(salary_month__startswith=year)

        queryset = queryset.order_by('salary_month')
        salaries_data = SalarySerializer(queryset, many=True).data

        total_leaves = sum(float(s.leaves) for s in queryset)
        total_leave_deduction = sum(float(s.leave_deduction) for s in queryset)
        total_allowances = sum(float(s.allowances) for s in queryset)
        total_other_deductions = sum(float(s.other_deductions) for s in queryset)
        total_net_amount = sum(float(s.net_amount) for s in queryset)
        paid_count = queryset.filter(status='paid').count()
        unpaid_count = queryset.filter(status='unpaid').count()

        admin_company = {
            'company_name': user.company_name or 'Smart Ledger',
            'company_email': user.company_email or user.email,
            'company_phone': user.company_phone or '',
            'company_address': user.company_address or '',
            'business_registration': user.business_registration or '',
        }

        response_data = {
            'employee': EmployeeSerializer(employee).data,
            'admin_company': admin_company,
            'year': year,
            'month': month,
            'salaries': salaries_data,
            'summary': {
                'total_records': len(salaries_data),
                'total_leaves': total_leaves,
                'total_leave_deduction': total_leave_deduction,
                'total_allowances': total_allowances,
                'total_other_deductions': total_other_deductions,
                'total_net_amount': total_net_amount,
                'paid_count': paid_count,
                'unpaid_count': unpaid_count,
            }
        }
        return Response(response_data)



class SalaryViewSet(viewsets.ModelViewSet):
    serializer_class = SalarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Salary.objects.filter(admin=self.request.user).select_related('employee')

        search = self.request.query_params.get('search', '').strip()
        employee_id = self.request.query_params.get('employee', '').strip()
        salary_month = self.request.query_params.get('salary_month', '').strip()
        salary_status = self.request.query_params.get('status', '').strip()

        if search:
            queryset = queryset.filter(
                Q(employee__name__icontains=search) |
                Q(employee__role__icontains=search)
            )
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if salary_month:
            queryset = queryset.filter(salary_month=salary_month)
        if salary_status:
            queryset = queryset.filter(status=salary_status)

        return queryset

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
