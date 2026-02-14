from django.contrib import admin
from .models import UserProfile

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ( "id", "user", "email_access_granted", "last_processed_date")
    search_fields = ("user",)
    ordering     = ("user",)
