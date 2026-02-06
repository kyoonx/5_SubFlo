# subscriptions/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

class Subscription(models.Model):
    """
    Represents a user's subscription in various platforms.
    This is one of the primary models to store all relevant information about a user's subscription, such as
    platform_name, service_name, start_date, end_date etc. for every user.
    This model will be filled after a LLM processes users' emails.
    Ensure that each user can subscribe to only "one" service from a specific platform during a given period.
    """
    id = models.AutoField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions', verbose_name="User")
    platform_name = models.CharField(max_length=255, verbose_name="Platform Name")
    service_name = models.CharField(max_length=255, verbose_name="Service Name")
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date")
    already_canceled = models.BooleanField(default=False, verbose_name="Already Canceled")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Price")
    currency = models.CharField(max_length=10, default="USD", verbose_name="Currency")
    payment_method = models.CharField(max_length=255, null=True, blank=True, verbose_name="Payment Method")
    email_message_id = models.OneToOneField("EmailMessage", on_delete=models.SET_NULL, related_name='subscription', null=True, blank=True, verbose_name="Email Message ID")
    unsubscribe_link = models.TextField(null=True, blank=True, verbose_name="Unsubscribe Link")
    notes = models.TextField(null=True, blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        return f"{self.platform_name} - {self.user.username}"

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "platform_name", "service_name", "start_date", "end_date"],
                name="unique_user_platform_service_date",
            )
        ]
        ordering = ["user", "-end_date", "-start_date", "platform_name", "service_name"]

class EmailMessage(models.Model):
    """
    Represents a user's email message.
    Ensure that `message_id` is unique for every user.
    `parsed_data` and `created_at` will be filled after the LLM processes emails.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_messages', verbose_name="User")
    message_id = models.CharField(max_length=255, verbose_name="Message ID", primary_key=True)
    subject = models.CharField(max_length=255, verbose_name="Subject")
    sender = models.CharField(max_length=255, verbose_name="Sender")
    received_date = models.DateTimeField(verbose_name="Received Date")
    raw_email_body = models.TextField(verbose_name="Raw Email Body")
    parsed_data = models.JSONField(null=True, blank=True, verbose_name="Parsed Data")  # Store the LLM output
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")    # Time when `parsed_data` is filled

    def __str__(self):
        name = f"Email from {self.sender} - {self.subject}" if len(self.subject) <= 50 else f"Email from {self.sender} - {self.subject[:50]}..."
        return name

    class Meta:
        verbose_name = "Email Message"
        verbose_name_plural = "Email Messages"
        constraints = [
            models.UniqueConstraint(
                fields=["message_id"],
                name="unique_message_id",
            )
        ]
        ordering = ["user", "-received_date"]