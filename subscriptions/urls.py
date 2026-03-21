from django.urls import path
from .ai_guide_view import CancellationGuideView
from .email_parser_view import EmailParserView
from .save_parsed_view import SaveParsedSubscriptionView
from .views import GmailFetchView, GmailDebugView

app_name = "subscriptions"

urlpatterns = [
    path(
        "cancel-guide/",
        CancellationGuideView.as_view(),
        name="cancel_guide",
    ),
    path(
        "parse-email/",
        EmailParserView.as_view(),
        name="parse_email",
    ),
    path(
        "save-parsed/",
        SaveParsedSubscriptionView.as_view(),
        name="save_parsed",
    ),
    path(
        "emails/",
        GmailFetchView.as_view(),
        name="gmail_fetch",
    ),
    path(
        "emails/debug/",
        GmailDebugView.as_view(),
        name="gmail_debug",
    ),
]
