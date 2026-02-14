from django.contrib import admin
from .models import Subscription, EmailMessage

# Register your models here.
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform_name", "service_name", "start_date", "end_date")
    search_fields = ("user__username", "platform_name", "service_name")
    ordering     = ("user", "-end_date", "-start_date", "platform_name", "service_name")

@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "id", "subject", "received_date")
    search_fields = ("user__username", "subject", "sender")
    ordering     = ("user", "-received_date")