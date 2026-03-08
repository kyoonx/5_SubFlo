# subscriptions/save_parsed_view.py
#
# Saves the LLM-parsed subscription data into the database.
# Called after the local model extracts fields from a raw email.

import json
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import Subscription, EmailMessage

logger = logging.getLogger(__name__)


def parse_date(date_str):
    """Attempt to parse a date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@method_decorator(login_required, name="dispatch")
class SaveParsedSubscriptionView(View):
    """
    POST /subscriptions/save-parsed/
    Body: {
        "parsed": { ...subscription fields... },
        "raw_email": "original email text"
    }
    Creates EmailMessage + Subscription records in the DB.
    """

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        parsed = body.get("parsed", {})
        raw_email = body.get("raw_email", "")

        if not parsed or not parsed.get("platform_name"):
            return JsonResponse(
                {"error": "No valid parsed data to save."}, status=400
            )

        email_msg = EmailMessage.objects.create(
            user=request.user,
            subject=parsed.get("service_name", "Parsed Email"),
            sender=parsed.get("platform_name", "Unknown"),
            received_date=timezone.now(),
            raw_email_body=raw_email,
            parsed_data=parsed,
        )

        try:
            price = float(parsed["price"]) if parsed.get("price") is not None else None
        except (ValueError, TypeError):
            price = None

        subscription = Subscription.objects.create(
            user=request.user,
            platform_name=parsed.get("platform_name", "Unknown"),
            service_name=parsed.get("service_name", "Unknown"),
            start_date=parse_date(parsed.get("start_date")),
            end_date=parse_date(parsed.get("end_date")),
            is_trial=bool(parsed.get("is_trial", False)),
            already_canceled=bool(parsed.get("already_canceled", False)),
            price=price,
            currency=parsed.get("currency", "USD") or "USD",
            payment_method=parsed.get("payment_method"),
            email_message_id=email_msg,
            unsubscribe_link=parsed.get("unsubscribe_link"),
        )

        return JsonResponse({
            "message": "Subscription saved successfully.",
            "subscription_id": str(subscription.id),
        }, status=201)
