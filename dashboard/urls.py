from django.urls import path
from . import views
from dashboard.views import (subscription_list)

urlpatterns = [
    path("subscription", subscription_list, name="subscription-list-url"),
    
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
