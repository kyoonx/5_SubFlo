# subscriptions/preprocessing.py
#
# Part 2 — Preprocessing pipeline shared by:
#   - Local HuggingFace classifier (is_subscription_related)
#   - Gemini prompt builder (build_cancellation_prompt in ai_guide_view.py)

import re
import logging

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOCAL_MODEL_MAX_CHARS = 512   # DistilBERT's practical input window
GEMINI_NAME_MAX_CHARS = 200   # Hard cap on service name sent to Gemini prompt

SUBSCRIPTION_KEYWORDS = [
    "subscription", "billing", "renew", "renewal", "invoice",
    "receipt", "payment", "your plan", "monthly", "annual",
    "charged", "unsubscribe", "cancel", "free trial", "trial ends",
    "auto-renew", "next billing", "membership",
]


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    """Remove HTML tags from email body snippets."""
    if BS4_AVAILABLE:
        return BeautifulSoup(text, "html.parser").get_text(separator=" ")
    return re.sub(r"<[^>]+>", " ", text)


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace to single spaces and strip edges."""
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str, max_chars: int = LOCAL_MODEL_MAX_CHARS) -> str:
    """Full cleaning pipeline: HTML strip -> normalize -> truncate."""
    text = strip_html(text)
    text = normalize_whitespace(text)
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Email preprocessing for local HuggingFace model
# ---------------------------------------------------------------------------

def prepare_email_for_classifier(subject: str, body_snippet: str) -> str:
    """
    Combine subject and body snippet into a single string for the
    local DistilBERT subscription classifier.

    Format: "[SUBJECT]: {subject} | [BODY]: {body}"
    """
    clean_subject = clean_text(subject, max_chars=100)
    clean_body = clean_text(body_snippet, max_chars=400)

    fused = f"[SUBJECT]: {clean_subject} | [BODY]: {clean_body}"
    return fused[:LOCAL_MODEL_MAX_CHARS]


# ---------------------------------------------------------------------------
# Heuristic pre-filter (runs BEFORE the local model to save compute)
# ---------------------------------------------------------------------------

def has_subscription_keywords(text: str) -> bool:
    """
    Quick keyword scan before invoking the local model.
    Returns True if the email likely relates to a subscription.
    This prevents wasting model inference on obviously irrelevant emails.
    """
    lower = text.lower()
    return any(kw in lower for kw in SUBSCRIPTION_KEYWORDS)


# ---------------------------------------------------------------------------
# Service name preprocessing (for Gemini prompt)
# ---------------------------------------------------------------------------

def prepare_service_name(raw_name: str) -> str:
    """
    Clean and normalize a subscription/service name before injecting
    it into the Gemini cancellation guide prompt.
    """
    name = strip_html(raw_name)
    name = normalize_whitespace(name)
    name = re.sub(r"[^\w\s\-\.\+\&]", "", name)
    name = normalize_whitespace(name)
    return name[:GEMINI_NAME_MAX_CHARS]