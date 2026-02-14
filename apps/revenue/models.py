from django.db import models
from apps.account.models import BaseModel, User

class CarCategory(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_categories')

    class Meta:
        db_table = 'car_categories'
        verbose_name_plural = 'Car Categories'

    def __str__(self):
        return self.name

class Car(BaseModel):
    category = models.ForeignKey(CarCategory, on_delete=models.SET_NULL, null=True, related_name='cars')
    name = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    chassis_number = models.CharField(max_length=50, unique=True)
    year = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars')

    class Meta:
        db_table = 'cars'

    def __str__(self):
        return f"{self.name} - {self.chassis_number}"

class Order(BaseModel):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('auction', 'Auction'),
    ]
    
    TRANSACTION_CATAGORY = [
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ]
    
    PAYMENT_STATUSES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, blank=True, default='pending')
    order_number = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    transaction_catagory = models.CharField(max_length=20, choices=TRANSACTION_CATAGORY)
    transaction_date = models.DateField()
    customer_name = models.CharField(max_length=200, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    other_details = models.JSONField(null=True, blank=True) 
    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    class Meta:
        db_table = 'orders'
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.order_number} - {self.transaction_type}"

class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    venue = models.CharField(max_length=50, blank=True)
    year_type = models.CharField(max_length=10, blank=True)
    auction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vehicle_price = models.DecimalField(max_digits=12, decimal_places=2)
    consumption_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recycling_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    automobile_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bid_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bid_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.order.order_number} - {self.car.name}"
