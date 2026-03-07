# subscriptions/ai_guide_view.py
#
# Part 2 #3 — External API Integration: Google Gemini
# Feature: AI-powered step-by-step cancellation guide generator
#
# Usage:
#   POST /subscriptions/cancel-guide/
#   Body: { "subscription_name": "Netflix" }
#   Returns: JSON with a numbered cancellation guide
#
# Setup:
#   pip install google-genai beautifulsoup4
#   Add GEMINI_API_KEY=your_key to .env

import os
import re
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.html import escape

from google import genai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

MAX_INPUT_LENGTH = 200
MAX_OUTPUT_TOKENS = 2048

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


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Gemini prompt builder
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------

def call_gemini(prompt: str) -> dict:
    """
    Call the Gemini 1.5 Flash model and parse the JSON response.
    Returns a dict on success, raises an exception on failure.
    """
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.3,
        },
    )
    raw_text = response.text.strip()

    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    parsed = json.loads(raw_text)
    return parsed


# ---------------------------------------------------------------------------
# Django View
# ---------------------------------------------------------------------------

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

        # Layer 1: Sanitize
        clean_name = sanitize_input(raw_name)

        if not clean_name:
            return JsonResponse(
                {"error": "Subscription name cannot be empty."}, status=400
            )

        # Layer 2: Safety check
        if not is_safe_input(clean_name):
            logger.warning(
                "Blocked potentially malicious input from user %s: %s",
                request.user.id,
                clean_name,
            )
            return JsonResponse(
                {"error": "Input contains disallowed content."}, status=400
            )

        # Layer 3: Format validation
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

        # Build prompt and call Gemini
        prompt = build_cancellation_prompt(clean_name)

        try:
            guide = call_gemini(prompt)
        except json.JSONDecodeError:
            logger.error("Gemini returned non-JSON response for: %s", clean_name)
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
            logger.exception("Gemini API call failed: %s", exc)
            return JsonResponse(
                {
                    "error": (
                        "Failed to generate guide. "
                        "Check your API key and network connection."
                    )
                },
                status=503,
            )

        # Output guardrails
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
            "service": escape(guide.get("service", clean_name)),
            "estimated_time": escape(guide.get("estimated_time", "Unknown")),
            "cancellation_url": escape(guide.get("cancellation_url", "See steps below")),
            "steps": [escape(step) for step in steps],
            "warnings": [escape(w) for w in guide.get("warnings", [])],
        }

        return JsonResponse({"guide": safe_guide}, status=200)
