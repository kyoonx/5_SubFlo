from django.urls import path
from . import views
from dashboard.views import (SubscriptionList, subscription_detail, email_message_detail)

urlpatterns = [
    path("subscription", SubscriptionList.as_view(), name="subscription-list-url"),  
    
    path("subscription/<int:pk>", subscription_detail, name="subscription-detail-url"),
    
    path("email_message/<uuid:pk>", email_message_detail, name="email_message_detail-url"),
    
    
    # Function-Based Views
    path(
        "subscriptions/manual/",
        views.subscriptions_manual_html,
        name="subscriptions_manual",
    ),
    path(
        "subscriptions/render/",
        views.subscriptions_render,
        name="subscriptions_render",
    ),

    # Class-Based Views
    path(
        "subscriptions/cbv-base/",
        views.SubscriptionsBaseCBV.as_view(),
        name="subscriptions_cbv_base",
    ),
    path(
        "subscriptions/cbv-generic/",
        views.SubscriptionsGenericListView.as_view(),
        name="subscriptions_cbv_generic",
    ),
]
