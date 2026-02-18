from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.account.models import User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['id', 'email', 'role', 'company_website']