from rest_framework import serializers
from apps.expense.models import Expense, ExpenseCategory, Restaurant

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'location', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'title', 'amount', 'description', 'date', 'category', 'category_name', 'transaction', 'restaurant', 'restaurant_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.transaction:
            data['transaction'] = {
                'id': instance.transaction.id,
                'description': instance.transaction.description,
                'withdraw': instance.transaction.withdraw,
                'date': instance.transaction.date
            }
        else:
            data['transaction'] = None
        return data
