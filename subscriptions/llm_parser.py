# subscriptions/llm_parser.py
#
# LLM Email → Subscription Parser
#
# This module is a helper (not a view). It is called directly by GmailScrapeView
# after emails are saved into EmailMessage, to parse them into Subscription records.
#
# Flow:
#   GmailScrapeView saves EmailMessage rows
#       └─► parse_emails_into_subscriptions(user, email_messages)
#               ├─► For each EmailMessage, build prompt + run local LLM
#               ├─► If LLM says not_subscription → mark parsed_data, skip
#               └─► Else → upsert Subscription row, update EmailMessage.parsed_data
#
# The local LLM used:
#   mlx-community/Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32
#   (lazy-loaded and shared with email_parser_view.py via get_model_and_tokenizer)
#
# Returns a summary dict consumed by GmailScrapeView to include in its JSON response.

import json
import logging
import re
import time
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.utils import timezone as django_timezone

from .models import EmailMessage, Subscription
from .preprocessing import clean_text

logger = logging.getLogger(__name__)

# Max characters of email body sent to the LLM.
# Keeps inference fast; most subscription info is in the first 3000 chars.
EMAIL_BODY_MAX_CHARS = 3000

# Sentinel value the LLM returns when an email is not subscription-related.
NOT_SUBSCRIPTION_SENTINEL = "NOT_SUBSCRIPTION"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def build_parse_prompt(subject: str, sender: str, received_date: str, body: str) -> str:
    """
    Many-shot prompt that instructs the LLM to either extract subscription
    fields as JSON, or return the sentinel string if the email is irrelevant.

    Design rationale:
    - Many-shot (5 examples) dramatically improves reliability on a 0.5B model
    - Sentinel output for non-subscription emails avoids hallucinated JSON
    - Explicit null rules prevent the model from inventing data
    - JSON-only output with no preamble makes parsing deterministic
    """
    return f"""You are an AI assistant for SubFlo, a personal subscription tracking app.
SubFlo helps users automatically discover and manage all their recurring subscriptions by
scanning their Gmail inbox. Your job is to read a single email and decide whether it
represents an active subscription event (a sign-up, renewal, payment, trial, or cancellation).
If it does, extract the key subscription fields into a structured JSON object so SubFlo can
track it. If it does not, return a sentinel value so SubFlo can safely ignore it.

CASE A — The email IS about a subscription, billing, payment, trial, renewal, or cancellation:
Return ONLY a JSON object with exactly these fields (use null for unknown values):
{{
  "platform_name":    "<company name, e.g. Netflix>",
  "service_name":     "<plan or product name, e.g. Netflix Standard>",
  "start_date":       "<YYYY-MM-DD or null>",
  "end_date":         "<YYYY-MM-DD or null>",
  "is_trial":         <true if free trial, else false>,
  "already_canceled": <true if subscription was canceled, else false>,
  "price":            <number like 9.99 or null>,
  "currency":         "<3-letter code like USD, EUR — default USD if not stated>",
  "payment_method":   "<e.g. Visa 4242, PayPal, Apple Pay, or null>",
  "unsubscribe_link": "<full URL to manage or cancel subscription, or null>"
}}

CASE B — The email is NOT about a subscription (it is a one-time purchase confirmation,
newsletter, advertisement, promotional offer, social notification, shipping update, or
anything unrelated to a recurring billing/subscription relationship):
Return ONLY this exact string with no other text:
NOT_SUBSCRIPTION

Rules:
- Output ONLY the JSON object or the string NOT_SUBSCRIPTION. No explanation, no markdown.
- Do NOT invent data. Use null when a field is not stated in the email.
- Date extraction priority rules:
    - start_date rules:
        - Use explicit start/order/trial date from body if present.
        - Otherwise, if the email is a subscription activation event (signup, order confirmation, trial start), set start_date = Received Date.

    - end_date rules:
        - Use explicit cancellation end/access date from body if present.
        - Otherwise, if the email explicitly confirms cancellation, set end_date = Received Date.
- Received Date is ONLY used as a fallback anchor date for lifecycle events (activation or cancellation), never for marketing or non-subscription emails.
- Never invent dates that are not either explicitly stated or derived from Received Date under the above rules.
- For price: extract the recurring charge amount (monthly/annual fee). Do NOT use a one-time purchase price.
- already_canceled = true only if the email explicitly confirms the subscription was canceled/cancelled.
- is_trial = true only if the email explicitly mentions a free trial or trial period.
- Use received_date as a hint for context only — do not copy it directly into start_date or end_date unless the body confirms it.

--- EXAMPLES ---

Example 1 (CASE A — free trial with future recurring charge):
Subject: Your YouTube Music Premium membership has started
Sender: noreply@youtube.com
Received Date: 2021-01-22
Body:
Hi Smiles Davis,
Welcome to your 1 month free trial of Music Premium membership! The payment method you provided will be charged monthly starting Feb 22, 2021.
As a member you can explore, manage, and cancel your membership any time by visiting YouTube account settings.
Welcome aboard!
The YouTube Team
Order Date
Jan 22, 2021
Order Number
65000055650650

Billing and cancellations: Billing for your membership will be handled by Apple. You'll receive an email from Apple with your order confirmation and billing details. At the end of your free trial, if any, Apple will automatically charge you $12.99/month, plus applicable taxes. You may cancel your Music Premium membership anytime from your Apple ID account settings. Refund policy

Need help? Contact support or go to our Help Center. Please don't reply to this email.

Help Center Email options
You received this email to provide information and updates around your YouTube product or account.
2021 Google LLC d/b/a YouTube, 901 Cherry Ave, San Bruno, CA 94066
Paid Service Terms of Service

Expected output:
{{"platform_name":"YouTube","service_name":"YouTube Music Premium","start_date":"2021-01-22","end_date":"2021-02-22","is_trial":true,"already_canceled":false,"price":12.99,"currency":"USD","payment_method":null,"unsubscribe_link":null}}

Reasoning (for training only, do not output):
1. Classification: The email explicitly says "free trial of Music Premium membership" and mentions a future monthly charge. This is a subscription trial start event — CASE A.
2. platform_name: The email is from YouTube / Google LLC and the product is "Music Premium". Platform = "YouTube".
3. service_name: The full product name stated in the email is "Music Premium membership" but the subject says "YouTube Music Premium", so service_name = "YouTube Music Premium".
4. start_date: The email states "Order Date: Jan 22, 2021" which is the explicit start of the trial. That maps to "2021-01-22". The received_date also confirms 2021-01-22, consistent.
5. end_date: The email says "charged monthly starting Feb 22, 2021", meaning the trial ends when billing begins — "2021-02-22". This is explicitly stated, so we can use it.
6. is_trial: The email says "1 month free trial" — explicitly a trial, so true.
7. already_canceled: No cancellation language anywhere. false.
8. price: The future recurring charge is "$12.99/month". Even though it hasn't been charged yet, this IS the recurring subscription price, so price = 12.99. We do NOT use a one-time fee here.
9. currency: Not explicitly stated as a currency code, but "$" indicates USD. Default to "USD".
10. payment_method: "The payment method you provided" — vague, no card or service named. null.
11. unsubscribe_link: No URL for managing/canceling subscription is provided in the body. null.

---

Example 2 (CASE A — subscription order confirmation with trial):
Subject: Your order confirmation for "Premium Individual"
Sender: Spotify <no-reply@spotify.com>
Received Date: 2026-04-14

Body:
Thanks for your order!
You'll find your receipt attached.
Item(s)
Premium Individual
Invoice ID
7f8c2323-5ea2-40ef-bc96-95ef1d273780
You agree that if you do not cancel your subscription before the end of your trial period, you will automatically be charged the $12.99 subscription fee + applicable tax for Premium every month until you cancel. You can cancel your Spotify Premium subscription at any time on your Account page following the instructions here. No partial refunds. Terms & Conditions apply.

Get Spotify for: iPhone iPad Android Other
This message was sent to p.michelle@gmail.com. If you have questions or complaints, please contact us.
Terms of Use Technical requirements Contact Us
Spotify USA Inc., 4 World Trade Center, 150 Greenwich Street, 62nd Floor, New York, NY 10007, United States
Tax Reg Number: 80-0555431

Expected output:
{{"platform_name":"Spotify","service_name":"Premium Individual","start_date":"2026-04-14","end_date":null,"is_trial":true,"already_canceled":false,"price":12.99,"currency":"USD","payment_method":null,"unsubscribe_link":null}}

Reasoning (for training only, do not output):
1. Classification: The email is a subscription order confirmation for Spotify Premium Individual. It explicitly mentions a subscription, a trial period, and a future recurring monthly charge. This is a clear CASE A subscription event.
2. platform_name: Sender is Spotify <no-reply@spotify.com>, so platform_name = "Spotify".
3. service_name: The item listed is "Premium Individual", which is the subscription plan name.
4. start_date: The body doesn't say the exact date, so we use the Received Date as the fallback.
5. end_date: No explicit end date is provided for trial or subscription term. The trial is open-ended until cancellation or billing, so end_date = null.
6. is_trial: The email explicitly states "before the end of your trial period" and describes a free/initial trial condition, so is_trial = true.
7. already_canceled: No cancellation confirmation is present. false.
8. price: The recurring subscription fee is clearly stated as "$12.99 subscription fee + applicable tax for Premium every month", so price = 12.99.
9. currency: Dollar symbol implies USD (US-based Spotify entity), so currency = "USD".
10. payment_method: No card or payment instrument is specified. null.
11. unsubscribe_link: No direct URL is provided in the body. null.

---

Example 3 (CASE B — one-time order confirmation, not a subscription):
Subject: Order Confirmation
Sender: noreply@parchment.com
Received Date: 2024-02-23
Body:
Order Confirmation Thank you for your order! Hi Jack, Your order was placed successfully on 02/23/2024. Here is your order summary: Item Ordered: Transcript For: Pitupoom Soontornthanon Document ID: TEYKYUJQ Delivery Method: Electronic FROM: Elgin Community College TO: University of Illinois Urbana-Champaign Once your order has been processed, we will send the official document to its destination. Thank you, The Parchment Team Turn Credentials into Opportunities Parchment's Privacy Policy and Terms of Use

Expected output:
NOT_SUBSCRIPTION

Reasoning (for training only, do not output):
1. Classification: At first glance, "Order Confirmation" could look like a subscription. However, reading carefully: the email is confirming a one-time order for an academic transcript delivery from Elgin Community College to University of Illinois. There is no mention of a recurring charge, a plan, a billing cycle, a trial, or a renewal. This is a single transaction for a document delivery service — not a subscription. CASE B.
2. Key signals that rule out CASE A:
   - No recurring billing language ("monthly", "annual", "renews", "next billing date").
   - No plan or membership name.
   - The "item ordered" is a physical/electronic document (a transcript), not a software plan or membership.
   - No price or payment amount mentioned at all.
   - No cancel or manage subscription link.
3. Output: NOT_SUBSCRIPTION — SubFlo should ignore this email entirely.

---

Example 4 (CASE B — promotional advertisement):
Subject: 50% off all plans this week only!
Sender: deals@someapp.com
Received Date: 2026-04-01
Body:
Don't miss our biggest sale of the year. Subscribe now and save 50% on any plan. Limited time offer. Click here to grab the deal before it expires!

Expected output:
NOT_SUBSCRIPTION

Reasoning (for training only, do not output):
1. Classification: The subject and body are purely promotional. The email is trying to sell a subscription, but the user has NOT yet subscribed. There is no confirmation of an active subscription, no billing date, no payment, no plan name, and no account details. Simply urging someone to subscribe is not the same as confirming they have one. CASE B.
2. Key signals that rule out CASE A:
   - "Subscribe now" — future tense call-to-action, not a confirmation of an existing subscription.
   - No order number, account ID, charge amount, or renewal date.
   - No plan details or service name tied to the user's account.
   - The word "offer" and "sale" indicate marketing, not billing.
3. Output: NOT_SUBSCRIPTION — SubFlo should ignore this email entirely.

--- NOW PROCESS THIS EMAIL ---

Subject: {subject}
Sender: {sender}
Received Date: {received_date}

Body:
{body}
"""




# ---------------------------------------------------------------------------
# LLM inference (reuses the lazy-loaded model from email_parser_view.py)
# ---------------------------------------------------------------------------

def _run_llm(prompt: str) -> str:
    """
    Run the local LLM and return its raw string output.
    Raises RuntimeError if the model cannot be loaded.
    """
    # Import lazily — same model instance as email_parser_view.py
    from .email_parser_view import get_model_and_tokenizer

    model, tokenizer = get_model_and_tokenizer()

    messages = [{"role": "user", "content": prompt}]

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        text = prompt

    model_inputs = tokenizer([text], return_tensors="pt", padding=True).to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=300,
        do_sample=False,        # greedy — deterministic output
    )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    raw = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    # Strip markdown fences if model wraps output in ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()

    return raw


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def _extract_json_from_output(raw: str) -> dict | None:
    """
    Try to extract a JSON dict from the raw LLM output.
    Returns None if no valid JSON object is found.
    """
    brace_start = raw.find("{")
    brace_end   = raw.rfind("}") + 1
    if brace_start == -1 or brace_end <= brace_start:
        return None
    try:
        return json.loads(raw[brace_start:brace_end])
    except json.JSONDecodeError:
        return None


def _is_not_subscription(raw: str) -> bool:
    """Return True if the LLM flagged this email as irrelevant."""
    return NOT_SUBSCRIPTION_SENTINEL in raw.upper()


# ---------------------------------------------------------------------------
# Field coercion — safely map raw LLM values to Django model field types
# ---------------------------------------------------------------------------

def _to_date(value) -> date | None:
    """Parse a YYYY-MM-DD string into a date, or return None."""
    if not value or str(value).lower() in ("null", "none", ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _to_decimal(value) -> Decimal | None:
    """Parse a numeric value into a Decimal, or return None."""
    if value is None or str(value).lower() in ("null", "none", ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _to_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return default


def _to_str(value, max_len: int = None) -> str | None:
    if value is None or str(value).lower() in ("null", "none", ""):
        return None
    s = str(value).strip()
    if max_len:
        s = s[:max_len]
    return s or None


def _coerce_fields(raw: dict) -> dict:
    """Map raw LLM JSON dict into Django-safe typed values."""
    return {
        "platform_name":    _to_str(raw.get("platform_name"), 255) or "Unknown",
        "service_name":     _to_str(raw.get("service_name"),  255) or "Unknown",
        "start_date":       _to_date(raw.get("start_date")),
        "end_date":         _to_date(raw.get("end_date")),
        "is_trial":         _to_bool(raw.get("is_trial"), False),
        "already_canceled": _to_bool(raw.get("already_canceled"), False),
        "price":            _to_decimal(raw.get("price")),
        "currency":         _to_str(raw.get("currency"), 10) or "USD",
        "payment_method":   _to_str(raw.get("payment_method"), 255),
        "unsubscribe_link": _to_str(raw.get("unsubscribe_link")),
    }


# ---------------------------------------------------------------------------
# Subscription upsert
# ---------------------------------------------------------------------------

def _upsert_subscription(user, email_message: EmailMessage, fields: dict) -> tuple[Subscription, bool]:
    """
    Create or update a Subscription record tied to this EmailMessage.

    Since EmailMessage.subscription is a OneToOneField, we first check if
    a Subscription already points to this email (re-parse scenario), and
    update it. Otherwise we try to create a new one.

    Returns (subscription_instance, created: bool).
    """
    # Re-parse path: subscription already linked to this email
    existing = getattr(email_message, "subscription", None)
    if existing is not None:
        for attr, val in fields.items():
            setattr(existing, attr, val)
        existing.save()
        return existing, False

    # New path: create subscription
    try:
        sub = Subscription.objects.create(
            user=user,
            email_message_id=email_message,
            **fields,
        )
        return sub, True
    except IntegrityError:
        # Unique constraint hit (same user+platform+service+dates already exists).
        # Find and update it instead, but leave email_message_id pointing to the
        # first email that created it (do not overwrite).
        try:
            sub = Subscription.objects.get(
                user=user,
                platform_name=fields["platform_name"],
                service_name=fields["service_name"],
                start_date=fields["start_date"],
                end_date=fields["end_date"],
            )
            # Update mutable fields only
            for attr in ("is_trial", "already_canceled", "price", "currency",
                         "payment_method", "unsubscribe_link"):
                setattr(sub, attr, fields[attr])
            sub.save()
            return sub, False
        except Subscription.DoesNotExist:
            logger.warning(
                "IntegrityError but could not find conflicting Subscription for user %s, "
                "platform=%s service=%s", user.username,
                fields["platform_name"], fields["service_name"],
            )
            raise


# ---------------------------------------------------------------------------
# Public entry point — called by GmailScrapeView
# ---------------------------------------------------------------------------

def parse_emails_into_subscriptions(user, email_messages: list[EmailMessage]) -> dict:
    """
    Process a list of EmailMessage objects through the local LLM and
    upsert Subscription records for those that are subscription-related.

    Args:
        user:           The Django User whose emails are being processed.
        email_messages: List of EmailMessage instances to parse (typically
                        the newly-saved ones from the current scrape run).

    Returns a summary dict:
    {
        "llm_processed":       <int>,   # emails sent to LLM
        "subscriptions_created": <int>, # new Subscription rows created
        "subscriptions_updated": <int>, # existing Subscription rows updated
        "not_subscription":    <int>,   # emails LLM flagged as irrelevant
        "llm_errors":          <int>,   # emails where LLM/parse failed
        "total_inference_sec": <float>, # cumulative inference time
    }
    """
    summary = {
        "llm_processed":         0,
        "subscriptions_created": 0,
        "subscriptions_updated": 0,
        "not_subscription":      0,
        "llm_errors":            0,
        "total_inference_sec":   0.0,
    }

    if not email_messages:
        logger.info("parse_emails_into_subscriptions: no emails to process.")
        return summary

    logger.info(
        "Starting LLM parsing for user %s — %d email(s) to process.",
        user.username, len(email_messages),
    )

    for idx, em in enumerate(email_messages, start=1):
        logger.info(
            "[%d/%d] Parsing EmailMessage %s (subject: %r)",
            idx, len(email_messages), em.id, em.subject,
        )

        # --- Prepare input ---
        cleaned_body = clean_text(em.raw_email_body, max_chars=EMAIL_BODY_MAX_CHARS)
        received_date_str = em.received_date.strftime("%Y-%m-%d") if em.received_date else "Unknown"
        prompt = build_parse_prompt(
            subject=em.subject,
            sender=em.sender,
            received_date=received_date_str,
            body=cleaned_body,
        )

        # --- Run LLM ---
        t0 = time.perf_counter()
        try:
            raw_output = _run_llm(prompt)
        except Exception as exc:
            logger.exception(
                "LLM inference failed for EmailMessage %s: %s", em.id, exc
            )
            summary["llm_errors"] += 1
            em.parsed_data = {"error": str(exc), "status": "llm_error"}
            em.save(update_fields=["parsed_data"])
            continue
        elapsed = time.perf_counter() - t0
        summary["total_inference_sec"] += elapsed
        summary["llm_processed"] += 1

        logger.debug("LLM raw output for %s (%.1fs): %r", em.id, elapsed, raw_output[:200])

        # --- Not a subscription? ---
        if _is_not_subscription(raw_output):
            logger.info("EmailMessage %s flagged as NOT_SUBSCRIPTION.", em.id)
            summary["not_subscription"] += 1
            em.parsed_data = {"status": "not_subscription"}
            em.save(update_fields=["parsed_data"])
            continue

        # --- Parse JSON ---
        raw_dict = _extract_json_from_output(raw_output)
        if raw_dict is None:
            logger.warning(
                "EmailMessage %s: LLM returned non-JSON, non-sentinel output: %r",
                em.id, raw_output[:300],
            )
            summary["llm_errors"] += 1
            em.parsed_data = {
                "status": "parse_error",
                "raw_output": raw_output[:500],
            }
            em.save(update_fields=["parsed_data"])
            continue

        # --- Coerce types ---
        try:
            fields = _coerce_fields(raw_dict)
        except Exception as exc:
            logger.exception("Field coercion failed for EmailMessage %s: %s", em.id, exc)
            summary["llm_errors"] += 1
            em.parsed_data = {"status": "coercion_error", "error": str(exc)}
            em.save(update_fields=["parsed_data"])
            continue

        # --- Upsert Subscription ---
        try:
            sub, created = _upsert_subscription(user, em, fields)
        except Exception as exc:
            logger.exception(
                "Subscription upsert failed for EmailMessage %s: %s", em.id, exc
            )
            summary["llm_errors"] += 1
            em.parsed_data = {"status": "db_error", "error": str(exc)}
            em.save(update_fields=["parsed_data"])
            continue

        if created:
            summary["subscriptions_created"] += 1
            logger.info("Created Subscription %s for EmailMessage %s.", sub.id, em.id)
        else:
            summary["subscriptions_updated"] += 1
            logger.info("Updated Subscription %s for EmailMessage %s.", sub.id, em.id)

        # --- Persist parsed_data on EmailMessage ---
        em.parsed_data = {
            "status": "parsed",
            "subscription_id": str(sub.id),
            **{k: str(v) if v is not None else None for k, v in fields.items()},
        }
        em.save(update_fields=["parsed_data"])

    summary["total_inference_sec"] = round(summary["total_inference_sec"], 2)
    logger.info(
        "LLM parsing complete for user %s: %s",
        user.username, summary,
    )
    return summary