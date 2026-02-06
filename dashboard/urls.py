from django.urls import path
from . import views
from dashboard.views import (SubscriptionList, subscription_detail, email_message_detail)

urlpatterns = [
    path("", SubscriptionList.as_view(), name="subscription-list-url"),  
    
    path("<int:pk>", subscription_detail, name="subscription-detail-url"),
    
    path("email_message/<uuid:pk>", email_message_detail, name="email_message_detail-url"),
]
