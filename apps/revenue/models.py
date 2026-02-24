from django.db import models
from apps.account.models import BaseModel, User
from decimal import Decimal

class CarCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    company = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_categories')

    class Meta:
        db_table = 'car_categories'
        verbose_name_plural = 'Car Categories'

    def __str__(self):
        return self.name

class Car(BaseModel):
    category = models.ForeignKey(CarCategory, on_delete=models.SET_NULL, null=True, related_name='cars')
    # name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    model = models.CharField(max_length=100)
    chassis_number = models.CharField(max_length=50, unique=True)
    year = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars')

    class Meta: 
        db_table = 'cars'

    def __str__(self):
        return f"{self.category} - {self.chassis_number}"

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
    auction = models.ForeignKey('Auction', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    saler = models.ForeignKey('Saler', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    company_account = models.ForeignKey('CompanyAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    transaction = models.ForeignKey('Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    class Meta:
        db_table = 'orders'
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.order_number} - {self.transaction_type}"

class OrderItem(BaseModel):
    TAX_RATE = Decimal('0.10')  # 10% consumption tax
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    car_category = models.ForeignKey(CarCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    venue = models.CharField(max_length=100, blank=True)  # 会場 Auction Venue
    notes = models.TextField(blank=True)
    
    # Vehicle price and tax
    vehicle_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    vehicle_price_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Recycle fee (no tax)
    recycle_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Listing fee and tax
    listing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    listing_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Successful bid and tax
    successful_bid = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    successful_bid_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Commission fee and tax
    commission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    commission_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Transport fee and tax
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    transport_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Registration fee and tax
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    registration_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Canceling fee (no tax)
    canceling_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    
    # Legacy fields (kept for backward compatibility)
    year_type = models.CharField(max_length=20, blank=True)  # 平成年式 Year
    auction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # 落札料 Auction Fee
    consumption_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # 消費税 Consumption Tax
    recycling_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # リサイクル料 Recycling Fee
    automobile_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # 自動車税 Automobile Tax
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # 落札手数料 Winning Bid Service Fee
    service_fee_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)  # 消費税 Tax on Service Fee
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)  # 合計 Total

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.order.order_number} - {self.car.category}"
    
    def save(self, *args, **kwargs):
        # Calculate subtotal using the current fee structure.
        self.subtotal = (
            self.vehicle_price + self.vehicle_price_tax +
            self.recycle_fee +
            self.listing_fee + self.listing_fee_tax +
            self.canceling_fee -
            self.successful_bid - self.successful_bid_tax -
            self.commission_fee - self.commission_fee_tax -
            self.transport_fee - self.transport_fee_tax -
            self.registration_fee - self.registration_fee_tax
        )
        
        super().save(*args, **kwargs)

class Customer(BaseModel):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.TextField()
    phone = models.CharField(max_length=50)
    account_number = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=200)
    swift_code = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')

    class Meta:
        db_table = 'customers'

    def __str__(self):
        return self.name

class Saler(BaseModel):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.TextField()
    phone = models.CharField(max_length=50)
    account_number = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=200)
    swift_code = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salers')

    class Meta:
        db_table = 'salers'

    def __str__(self):
        return self.name

class CompanyAccount(BaseModel):
    bank_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=50)
    account_holder = models.CharField(max_length=200)
    swift_code = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_accounts')

    class Meta:
        db_table = 'company_accounts'

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

class Auction(BaseModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions')

    class Meta:
        db_table = 'auctions'

    def __str__(self):
        return self.name

class Transaction(BaseModel):
    date = models.DateField()
    transaction_id = models.CharField(max_length=500, null=True, blank=True)
    withdraw = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    company_account = models.ForeignKey('CompanyAccount', on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')

    class Meta:
        db_table = 'transactions'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.description}"
