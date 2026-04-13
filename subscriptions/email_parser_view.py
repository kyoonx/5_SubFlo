# subscriptions/email_parser_view.py
#
# Email → JSON via Illinois Chat (UIUC.chat), same API as cancel-guide.
#
# Usage:
#   POST /subscriptions/parse-email/
#   Body: { "raw_email": "From: Netflix <info@netflix.com>..." }
#   Returns: JSON with extracted subscription fields
#
#   GET /subscriptions/parse-email/
#   Renders the email parser UI template

import json
import logging
import os
import time

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.html import escape

from .email_parser import parse_email_to_json
from .preprocessing import clean_text

logger = logging.getLogger(__name__)

INPUT_MAX_CHARS = 2000

EXPECTED_FIELDS = {
    "platform_name": str,
    "service_name": str,
    "start_date": str,
    "end_date": str,
    "is_trial": bool,
    "already_canceled": bool,
    "price": float,
    "currency": str,
    "payment_method": str,
    "unsubscribe_link": str,
}


def normalize_parsed_data(raw: dict) -> dict:
    """Ensure all expected fields exist and have the right types."""
    result = {}
    for field, expected_type in EXPECTED_FIELDS.items():
        value = raw.get(field)
        if value is None or value == "null" or value == "None":
            result[field] = None
            continue
        if expected_type == bool:
            if isinstance(value, bool):
                result[field] = value
            else:
                result[field] = str(value).lower() in ("true", "1", "yes")
        elif expected_type == float:
            try:
                result[field] = float(value)
            except (ValueError, TypeError):
                result[field] = None
        else:
            result[field] = str(value) if value else None
    return result


@method_decorator(login_required, name="dispatch")
class EmailParserView(View):
    """
    GET  /subscriptions/parse-email/ — renders the email parser UI
    POST /subscriptions/parse-email/ — parses raw email via Illinois Chat

    POST body: { "raw_email": "From: Netflix..." }
    Returns: { "parsed": { ...subscription fields... }, "inference_time": 12.3 }
    """

    def get(self, request, *args, **kwargs):
        return render(request, "subscriptions/parse_email.html")

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

        raw_email = body.get("raw_email", "")

        if not raw_email or not str(raw_email).strip():
            return JsonResponse(
                {"error": "Email content cannot be empty."}, status=400
            )

        cleaned = clean_text(str(raw_email), max_chars=INPUT_MAX_CHARS)

        if not cleaned:
            return JsonResponse(
                {
                    "error": (
                        "Email content is empty after cleaning "
                        "(possibly only HTML tags or whitespace)."
                    )
                },
                status=400,
            )

        t0 = time.perf_counter()
        try:
            parsed_raw = parse_email_to_json(cleaned)
        except Exception as exc:
            logger.exception("Illinois Chat email parse failed: %s", exc)
            return JsonResponse(
                {"error": f"Illinois Chat request failed: {exc}"},
                status=503,
            )
        inference_time = time.perf_counter() - t0

        if parsed_raw is None:
            return JsonResponse(
                {
                    "error": (
                        "No subscription data extracted (not a subscription email "
                        "or the model could not produce JSON)."
                    )
                },
                status=422,
            )

        normalized = normalize_parsed_data(parsed_raw)
        safe_result = {}
        for key, value in normalized.items():
            safe_result[key] = escape(value) if isinstance(value, str) else value

        model_label = os.getenv("ILLINOIS_MODEL") or os.getenv("ILLINOIS_CHAT_MODEL") or "qwen3:32b"
        return JsonResponse(
            {
                "parsed": safe_result,
                "inference_time": round(inference_time, 2),
                "model": f"Illinois Chat ({model_label})",
            },
            status=200,
        )
