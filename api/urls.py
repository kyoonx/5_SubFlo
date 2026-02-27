from django.urls import path
from api.views import top_subscriptions_by_platform

urlpatterns = [
    path("subscriptions/top-by-platform/", top_subscriptions_by_platform),
]