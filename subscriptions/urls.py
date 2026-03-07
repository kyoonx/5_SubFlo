from django.urls import path
from .ai_guide_view import CancellationGuideView

app_name = "subscriptions"

urlpatterns = [
    # POST /subscriptions/cancel-guide/
    # Body: { "subscription_name": "Netflix" }
    path(
        "cancel-guide/",
        CancellationGuideView.as_view(),
        name="cancel_guide",
    ),
]
