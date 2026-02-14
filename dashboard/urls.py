from django.urls import path
from dashboard.views import (SubscriptionList, api_all_active_subscriptions, email_message_list, subscription_detail, email_message_detail)

urlpatterns = [
    path("", SubscriptionList.as_view(), name="subscription-list-url"),  
    
    path("<uuid:pk>", subscription_detail, name="subscription-detail-url"),
    
    path("email_message/", email_message_list, name="email_message_list-url"),
    path("email_message/<uuid:pk>", email_message_detail, name="email_message_detail-url"),
    
    path("api/subscriptions/active/", api_all_active_subscriptions, name="api-active-subscriptions-url"),
]
