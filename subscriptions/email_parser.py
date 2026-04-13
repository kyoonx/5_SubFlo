"""
Email-to-JSON parser using Illinois Chat (UIUC.chat), same HTTP API as the
cancellation guide (see subscriptions/illinois_chat_client.py).

Requires ILLINOIS_API_KEY (and optional ILLINOIS_API_URL, ILLINOIS_PROJECT_NAME; see .env.example).
"""

import json
import re
import logging

from .illinois_chat_client import call_illinois_chat_messages

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 4096
EXPECTED_KEYS = {"platform_name", "service_name"}

NOT_SUBSCRIPTION_SENTINEL = "NOT_SUBSCRIPTION"

_REDACTED_THINKING = re.compile(
    r"<redacted_thinking\b[^>]*>.*?</think>",
    re.IGNORECASE | re.DOTALL,
)


def _preprocess(raw_body: str) -> str:
    """
    Clean raw email body before sending to the LLM.
    - Normalize whitespace (trim, collapse repeated newlines/spaces)
    - Truncate to max length
    - Strip null bytes and non-printable control characters
    """
    if not raw_body or not isinstance(raw_body, str):
        return ""
    cleaned = "".join(c for c in raw_body if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127))
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n[\s\n]*\n", "\n\n", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > MAX_INPUT_CHARS:
        cleaned = cleaned[:MAX_INPUT_CHARS]
    return cleaned


def _build_user_prompt(cleaned_body: str) -> str:
    return (
        "Extract subscription fields from this email.\n"
        "If it IS about a subscription, billing, trial, renewal, or cancellation: reply with exactly one JSON object and nothing else. "
        "Keys: platform_name, service_name, start_date, end_date, is_trial, already_canceled, price, currency, "
        "payment_method, unsubscribe_link. Dates as YYYY-MM-DD or null. Booleans true/false. price is a number or null. "
        "Use null for unknown values.\n"
        "If it is NOT about a subscription (newsletter, generic promo, unrelated): reply with exactly this single line, nothing else:\n"
        f"{NOT_SUBSCRIPTION_SENTINEL}\n\n"
        "Email:\n"
        + cleaned_body
    )


def _extract_json_from_output(text: str) -> dict | None:
    """
    Parse model output as JSON. Strip markdown code fences if present.
    Returns dict on success, None on failure.
    """
    if not text or not text.strip():
        return None
    text = _REDACTED_THINKING.sub("", text).strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    start = text.find("{")
    if start != -1:
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            text = text[start:end]
    text = re.sub(r",(\s*[\]}])", r"\1", text)
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        if not EXPECTED_KEYS.intersection(data.keys()):
            logger.warning("Parsed JSON missing expected keys %s: %s", EXPECTED_KEYS, data)
            return None
        return data
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse model output as JSON: %s", text[:200])
        return None


def parse_email_to_json(raw_body: str) -> dict | None:
    """
    Parse raw email body into a JSON-serializable dict using Illinois Chat (UIUC.chat).

    Returns:
        dict suitable for EmailMessage.parsed_data on success;
        None if not subscription-related (NOT_SUBSCRIPTION), on parse failure, or API error.
    """
    cleaned = _preprocess(raw_body)
    if not cleaned:
        return None
    try:
        raw = call_illinois_chat_messages(
            [
                {
                    "role": "system",
                    "content": (
                        "You extract subscription data from email text. "
                        "Follow the user instructions exactly: either one JSON object OR the line NOT_SUBSCRIPTION. "
                        "No markdown fences unless wrapping JSON."
                    ),
                },
                {"role": "user", "content": _build_user_prompt(cleaned)},
            ],
            temperature=0.2,
            timeout=180,
        )
        raw_stripped = raw.strip()
        if NOT_SUBSCRIPTION_SENTINEL in raw_stripped.upper() and "{" not in raw_stripped:
            return None
        return _extract_json_from_output(raw)
    except Exception as e:
        logger.exception("Illinois Chat email parse failed: %s", e)
        return None
