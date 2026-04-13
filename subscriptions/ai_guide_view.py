# subscriptions/ai_guide_view.py
#
# External API: Illinois Chat (chat.illinois.edu)
# Feature: AI-powered step-by-step cancellation guide generator
#
# Usage:
#   POST /subscriptions/cancel-guide/
#   Body: { "subscription_name": "Netflix" }
#   Returns: JSON with a numbered cancellation guide
#
# Setup:
#   pip install requests beautifulsoup4
#   Add to .env (chat.illinois.edu → Settings → API Keys):
#     ILLINOIS_API_KEY=...
#     ILLINOIS_API_URL=https://chat.illinois.edu/api/chat-api/chat
#     ILLINOIS_PROJECT_NAME=Subflo

import os
import re
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from subscriptions.illinois_chat_client import call_illinois_chat_messages

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 200

_REDACTED_THINKING = re.compile(
    r"<redacted_thinking\b[^>]*>.*?</think>",
    re.IGNORECASE | re.DOTALL,
)

BLOCKED_KEYWORDS = [
    "ignore previous",
    "jailbreak",
    "system:",
    "<script>",
    "forget instructions",
    "pretend you are",
    "act as",
    "disregard",
    "override",
    "bypass",
]


def sanitize_input(text: str) -> str:
    """Strip dangerous characters, collapse whitespace, truncate."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_INPUT_LENGTH]


def is_safe_input(text: str) -> bool:
    """Return False if the text contains prompt-injection patterns."""
    lower_text = text.lower()
    return not any(kw in lower_text for kw in BLOCKED_KEYWORDS)


def is_valid_service_name(text: str) -> bool:
    """
    Only allow letters, numbers, spaces, hyphens, dots, plus signs,
    and ampersands — reasonable characters for a service name.
    """
    return bool(re.match(r"^[a-zA-Z0-9 \-\.\+\&]{1,100}$", text))


def build_cancellation_prompt(subscription_name: str) -> str:
    """
    Construct a structured, injection-resistant prompt.
    The user value is inserted as DATA — not as an instruction.
    """
    return (
        "You are a consumer-rights assistant that helps users cancel unwanted subscriptions. "
        "Your tone is clear, friendly, and step-by-step. "
        "Do NOT include any personal opinions, marketing language, or off-topic content.\n\n"
        f"SERVICE NAME: {subscription_name}\n\n"
        "TASK: Write a numbered, step-by-step guide (maximum 10 steps) that explains "
        "exactly how a user can cancel their subscription to the service listed above. "
        "Include:\n"
        "  1. The official cancellation URL or app path\n"
        "  2. Estimated time to complete cancellation\n"
        "  3. Any common traps (e.g. 'pause instead of cancel' dark patterns)\n"
        "  4. What confirmation to look for (email receipt, in-app message)\n\n"
        "Format your response ONLY as a JSON object with this exact shape:\n"
        "{\n"
        '  "service": "<service name>",\n'
        '  "estimated_time": "<e.g. 2 minutes>",\n'
        '  "cancellation_url": "<direct URL or \'In-app only\'>",\n'
        '  "steps": ["Step 1 text", "Step 2 text", ...],\n'
        '  "warnings": ["Warning 1", ...]\n'
        "}\n"
        "Return ONLY valid JSON. No markdown code fences, no preamble."
    )


def call_cancellation_llm(prompt: str) -> dict:
    """
    Call Illinois Chat (UIUC.chat) and parse the JSON cancellation guide.
    Raises on HTTP errors, missing key, or invalid JSON.
    """
    system = (
        "You output only one valid JSON object matching the user's schema. "
        "No markdown code fences, no text before or after the JSON."
    )
    raw = call_illinois_chat_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    raw = _REDACTED_THINKING.sub("", raw).strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    if not raw.startswith("{"):
        i, j = raw.find("{"), raw.rfind("}")
        if i != -1 and j != -1 and j > i:
            raw = raw[i : j + 1]
    # Models sometimes emit trailing commas before ] or } (invalid strict JSON).
    raw = re.sub(r",(\s*[\]}])", r"\1", raw)
    return json.loads(raw)


@method_decorator(login_required, name="dispatch")
class CancellationGuideView(View):
    """
    POST /subscriptions/cancel-guide/
    Accepts JSON body: { "subscription_name": "Netflix" }
    Returns JSON with AI-generated cancellation steps.
    """

    def get(self, request, *args, **kwargs):
        return render(request, "subscriptions/cancel_guide.html")

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"error": "Invalid JSON body."}, status=400
            )

        raw_name = body.get("subscription_name", "")

        clean_name = sanitize_input(raw_name)

        if not clean_name:
            return JsonResponse(
                {"error": "Subscription name cannot be empty."}, status=400
            )

        if not is_safe_input(clean_name):
            logger.warning(
                "Blocked potentially malicious input from user %s: %s",
                request.user.id,
                clean_name,
            )
            return JsonResponse(
                {"error": "Input contains disallowed content."}, status=400
            )

        if not is_valid_service_name(clean_name):
            return JsonResponse(
                {
                    "error": (
                        "Subscription name can only contain letters, numbers, "
                        "spaces, hyphens, dots, ampersands, and plus signs."
                    )
                },
                status=400,
            )

        prompt = build_cancellation_prompt(clean_name)

        try:
            guide = call_cancellation_llm(prompt)
        except json.JSONDecodeError:
            logger.error("Illinois Chat returned non-JSON for: %s", clean_name)
            return JsonResponse(
                {
                    "error": (
                        "The AI guide is temporarily unavailable. "
                        "Please try again later."
                    )
                },
                status=503,
            )
        except Exception as exc:
            logger.exception("Illinois Chat API call failed: %s", exc)
            return JsonResponse(
                {
                    "error": (
                        "Failed to generate guide. "
                        "Check ILLINOIS_API_KEY, ILLINOIS_PROJECT_NAME, and network connection."
                    )
                },
                status=503,
            )

        steps = guide.get("steps", [])
        if not steps or any(
            phrase in str(steps).lower()
            for phrase in ["i'm sorry", "i cannot", "i can't", "unable to"]
        ):
            return JsonResponse(
                {
                    "error": (
                        "The AI could not generate a guide for this service. "
                        "Please check the service name and try again."
                    )
                },
                status=422,
            )

        safe_guide = {
            "service": guide.get("service", clean_name),
            "estimated_time": guide.get("estimated_time", "Unknown"),
            "cancellation_url": guide.get("cancellation_url", "See steps below"),
            "steps": list(steps),
            "warnings": list(guide.get("warnings", [])),
        }

        return JsonResponse({"guide": safe_guide}, status=200)
