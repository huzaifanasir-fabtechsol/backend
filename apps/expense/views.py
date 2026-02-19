from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from apps.expense.models import Expense, ExpenseCategory, Restaurant
from apps.expense.serializers import ExpenseSerializer, ExpenseCategorySerializer, RestaurantSerializer
from apps.revenue.models import Transaction
from apps.revenue.serializers import TransactionSerializer

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def available_transactions(self, request):
        search = request.query_params.get('search', '')
        date = request.query_params.get('date', '')
        account_id = request.query_params.get('account_id', '')
        
        queryset = Transaction.objects.filter(user=request.user)
        
        if account_id:
            queryset = queryset.filter(company_account_id=account_id)
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(notes__icontains=search)
            )
        if date:
            queryset = queryset.filter(date=date)
            
        serializer = TransactionSerializer(queryset, many=True)
        return Response(serializer.data)

class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Restaurant.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
