from django.db import models
from django.contrib.auth.models import AbstractUser

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractUser):
    USER_ROLES = [
        ('admin', 'Admin'),
        ('superadmin', 'Super_Admin'),
    ]
    email = models.EmailField(unique=True)
    company_email = models.EmailField(max_length=250, blank=True, null=True)
    company_name = models.CharField(max_length=250, blank=True, null=True)
    company_phone = models.CharField(max_length=250, blank=True, null=True)
    company_website = models.CharField(max_length=250, blank=True, null=True)
    company_address = models.CharField(max_length=250, blank=True, null=True)
    role = models.CharField(max_length=50, choices=USER_ROLES, default='admin')

    
    class Meta:
        db_table = 'users'

