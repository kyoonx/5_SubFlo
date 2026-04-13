# subscriptions/save_parsed_view.py
#
# Saves the LLM-parsed subscription data into the database.
# Called after the local model extracts fields from a raw email.

import json
import logging
from datetime import datetime

from django.db import IntegrityError
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import Subscription, EmailMessage

logger = logging.getLogger(__name__)

# Hard cap on raw email body stored via this endpoint.
# The scrape pipeline handles its own truncation separately.
RAW_EMAIL_MAX_CHARS = 50_000

# Reasonable field length caps matching the model's max_length values.
PLATFORM_NAME_MAX  = 255
SERVICE_NAME_MAX   = 255
PAYMENT_METHOD_MAX = 255
CURRENCY_MAX       = 10


def parse_date(date_str):
    """Attempt to parse a date string in YYYY-MM-DD format. Returns None on any failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_price(value):
    """Coerce price to float, returning None on any failure."""
    if value is None:
        return None
    try:
        f = float(value)
        # Reject obviously bogus values (negative or astronomically large)
        if f < 0 or f > 1_000_000:
            return None
        return f
    except (ValueError, TypeError):
        return None


def truncate(value, max_len, fallback="Unknown"):
    """Return value as a string truncated to max_len, or fallback if empty/None."""
    if value is None:
        return fallback
    s = str(value).strip()[:max_len]
    return s if s else fallback


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

        # ── 1. Parse request body ──────────────────────────────────────────
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

        parsed   = body.get("parsed", {})
        raw_email = body.get("raw_email", "")

        # ── 2. Validate parsed payload ─────────────────────────────────────
        if not parsed or not isinstance(parsed, dict):
            return JsonResponse({"error": "Missing or invalid 'parsed' field."}, status=400)

        platform_name = str(parsed.get("platform_name") or "").strip()
        service_name  = str(parsed.get("service_name")  or "").strip()

        if not platform_name:
            return JsonResponse(
                {"error": "Parsed data must include a non-empty 'platform_name'."}, status=400
            )
        if not service_name:
            return JsonResponse(
                {"error": "Parsed data must include a non-empty 'service_name'."}, status=400
            )

        # ── 3. Sanitize / coerce all fields ───────────────────────────────
        raw_email_safe = str(raw_email)[:RAW_EMAIL_MAX_CHARS]

        price    = parse_price(parsed.get("price"))
        currency = truncate(parsed.get("currency"), CURRENCY_MAX, fallback="USD") or "USD"

        is_trial         = bool(parsed.get("is_trial", False))
        already_canceled = bool(parsed.get("already_canceled", False))

        start_date = parse_date(parsed.get("start_date"))
        end_date   = parse_date(parsed.get("end_date"))

        payment_method  = truncate(parsed.get("payment_method"),  PAYMENT_METHOD_MAX, fallback=None)
        unsubscribe_link = str(parsed.get("unsubscribe_link") or "").strip() or None

        # ── 4. Create EmailMessage ─────────────────────────────────────────
        try:
            email_msg = EmailMessage.objects.create(
                user=request.user,
                subject=truncate(service_name, 255, fallback="Parsed Email"),
                sender=truncate(platform_name, 255, fallback="Unknown"),
                received_date=timezone.now(),
                raw_email_body=raw_email_safe,
                parsed_data=parsed,
            )
        except Exception as exc:
            logger.exception("Failed to create EmailMessage for user %s: %s", request.user.id, exc)
            return JsonResponse(
                {"error": "Failed to save email record. Please try again."}, status=500
            )

        # ── 5. Create Subscription (with duplicate handling) ───────────────
        try:
            subscription = Subscription.objects.create(
                user=request.user,
                platform_name=truncate(platform_name, PLATFORM_NAME_MAX),
                service_name=truncate(service_name,   SERVICE_NAME_MAX),
                start_date=start_date,
                end_date=end_date,
                is_trial=is_trial,
                already_canceled=already_canceled,
                price=price,
                currency=currency,
                payment_method=payment_method,
                email_message_id=email_msg,
                unsubscribe_link=unsubscribe_link,
            )
        except IntegrityError:
            # UniqueConstraint(user, platform_name, service_name, start_date, end_date) hit.
            # The email record is still saved; inform the caller rather than crashing.
            logger.warning(
                "Duplicate subscription for user %s: %s / %s (%s → %s)",
                request.user.id, platform_name, service_name, start_date, end_date,
            )
            return JsonResponse(
                {
                    "error": "A subscription for this service and date range already exists.",
                    "email_message_id": str(email_msg.id),
                },
                status=409,  # Conflict
            )
        except Exception as exc:
            logger.exception("Failed to create Subscription for user %s: %s", request.user.id, exc)
            return JsonResponse(
                {"error": "Failed to save subscription record. Please try again."}, status=500
            )

        return JsonResponse({
            "message": "Subscription saved successfully.",
            "subscription_id": str(subscription.id),
            "email_message_id": str(email_msg.id),
        }, status=201)
