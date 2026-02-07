# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extends the Django User model to store additional user profile information.
    Represents the user's profile information.
    Used to keep track of the latest date a LLM processes emails, so the LLM knows where it left off.
    `user` is globally unique automatically due to Django User model.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', primary_key=True) # Link to Django's built-in User model
    email_access_granted = models.BooleanField(default=False, verbose_name="Email Access Granted") # Flag for email access permission
    last_processed_date = models.DateTimeField(null=True, blank=True, verbose_name="Last Processed Date") # Timestamp of last email processing

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ("user",)

# Signal to create a UserProfile automatically when a new User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# Signal to save the UserProfile when the User is updated
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()