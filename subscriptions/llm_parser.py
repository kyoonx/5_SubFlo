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

def build_parse_prompt(subject: str, sender: str, body: str) -> str:
    """
    Many-shot prompt that instructs the LLM to either extract subscription
    fields as JSON, or return the sentinel string if the email is irrelevant.

    Design rationale:
    - Many-shot (5 examples) dramatically improves reliability on a 0.5B model
    - Sentinel output for non-subscription emails avoids hallucinated JSON
    - Explicit null rules prevent the model from inventing data
    - JSON-only output with no preamble makes parsing deterministic
    """
    return f"""You are a subscription data extractor. Read the email below and decide:

CASE A — The email is about a subscription, billing, payment, trial, renewal, or cancellation:
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

CASE B — The email is NOT about a subscription (it is a newsletter, advertisement,
promotional offer, social notification, or anything unrelated to billing/subscription):
Return ONLY this exact string with no other text:
NOT_SUBSCRIPTION

Rules:
- Output ONLY the JSON object or the string NOT_SUBSCRIPTION. No explanation, no markdown.
- Do NOT invent data. Use null when a field is not stated in the email.
- For start_date/end-date: only fill if an explicit date appears. Do not calculate dates.
- For price: extract the recurring charge amount (monthly/annual), NOT a one-time fee.
- already_canceled = true if the email says the subscription was canceled/cancelled.
- is_trial = true only if the email explicitly mentions a free trial or trial period.

--- EXAMPLES ---

Example 1 (active subscription confirmation):
Subject: Your Netflix subscription
Sender: info@mailer.netflix.com
Body: 

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Notification</title>
 
</head>
<body>
  <div class="container">
    Hi, your Netflix Standard plan is active at $15.49/month. Next billing: March 15, 2026. Manage: 
    <a href="https://netflix.com/account">https://netflix.com/account</a>
  </div>
</body>
</html>

Then, you should return this pure JSON object (as a string, not a dict):

{{"platform_name":"Netflix","service_name":"Netflix Standard","start_date":null,"end_date":"2026-03-15","is_trial":false,"already_canceled":false,"price":15.49,"currency":"USD","payment_method":null,"unsubscribe_link":"https://netflix.com/account"}}

Below is the explaination. Note that you should NOT return the explanation — only the JSON object above.
**CHAIN-OF-THOUGHT:**

1.  **Email Type Identification**: The email is about an active subscription, specifically confirming the user's Netflix Standard plan. This aligns with CASE A.
2.  **Field Extraction**:
    *   `platform_name`:  Identified as "Netflix" from the subject and body.
    *   `service_name`:  Identified as "Netflix Standard" from the body.
    *   `start_date`:  Not explicitly mentioned in the body, so it's `null`.
    *   `end_date`:  The email explicitly states "Next billing: March 15, 2026," so the end date is "2026-03-15".
    *   `is_trial`:  The email does not mention a trial, so it's `false`.
    *   `already_canceled`: The email confirms the subscription is active, so it's `false`.
    *   `price`: The email states the price is $15.49/month, so it's `15.49`.
    *   `currency`: The currency is not mentioned, the default is USD, so it's `USD`.
    *   `payment_method`: Not mentioned, so it's `null`.
    *   `unsubscribe_link`: The email contains a link to manage the account, so it's `https://netflix.com/account`.
3.  **JSON Formation**: The extracted values are formatted into the required JSON object.

---

Example 2 (free trial started):
Subject: Your Spotify Premium trial has started
Sender: noreply@spotify.com
Body: 

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Receipt</title>
 
</head>
<body>
  <div class="container">
    <div class="header">Thanks for your order!</div>
    <div class="subtext">You'll find your receipt attached.</div>

    <div class="details">
      <div><span class="label">Item(s):</span> Premium Individual</div>
      <div><span class="label">Date:</span> January 02, 2026</div>
    </div>

    <div class="footer">
      You agree that if you do not cancel your subscription before the end of your trial period,
      you will automatically be charged the $12.99 subscription fee + applicable tax for Premium
      every month until you cancel. You can cancel your Spotify Premium subscription at any time
      on your Account page following the instructions here. No partial refunds. Terms & Conditions apply.
    </div>
  </div>
</body>
</html>

Then, you should return this pure JSON object (as a string, not a dict):

{{"platform_name":"Spotify","service_name":"Spotify Premium","start_date":"2026-01-02","end_date":"2026-02-02","is_trial":true,"already_canceled":false,"price":null,"currency":"USD","payment_method":null,"unsubscribe_link":null}}

Below is the explaination. Note that you should NOT return the explanation — only the JSON object above.
**CHAIN-OF-THOUGHT:**

1.  **Email Type Identification**: The email confirms a trial has started for Spotify Premium, matching CASE A.
2.  **Field Extraction**:
    *   `platform_name`:  Identified as "Spotify" from the subject.
    *   `service_name`:  Identified as "Spotify Premium" from the body.
    *   `start_date`:  The body mentions the date as "January 02, 2026," so it's "2026-01-02".
    *   `end_date`: Since it is a trial, the end date should be a month after, "2026-02-02".
    *   `is_trial`:  The subject clearly indicates a trial has started, so it's `true`.
    *   `already_canceled`:  The email doesn't mention cancellation, so it's `false`.
    *   `price`:  Although the footer mentions a future price, there is no recurring charge amount present now so it is `null`.
    *   `currency`: Not explicitly mentioned, so it defaults to "USD".
    *   `payment_method`: Not mentioned, so it's `null`.
    *   `unsubscribe_link`: There is no manage or cancel link, so it's `null`.
3.  **JSON Formation**: The extracted values are formatted into the required JSON object.

---

Example 3 (cancellation confirmed):
Subject: Your Dropbox subscription has been canceled
Sender: no-reply@dropbox.com
Body: 

<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" style="margin: 0; padding: 0">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title></title>

</head>

<body style="-webkit-font-smoothing: antialiased; width: 100% !important; margin: 0; padding: 0; background-color:#ffffff;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" align="center" style="width:100%; max-width:480px;">
    <tr>
        <td align="center" style="font-family:'Circular','Helvetica Neue',Helvetica,Arial,sans-serif; font-size:14px; color:#555555;">

            <div id="main">

                <!-- Header -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr><td height="30"></td></tr>
                    <tr>
                        <td style="padding:0 6.25%;">
                            <h2 style="margin:0; font-size:28px; line-height:36px; color:#555555;">
                                Subscription Update
                            </h2>
                        </td>
                    </tr>
                    <tr><td height="20"></td></tr>
                </table>

                <!-- Body Content -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%; font-size:14px; line-height:20px; color:#616467;">
                            
                            You've canceled Dropbox Plus. You'll keep access until May 31, 2026. Annual price was $119.99. Cancel was successful.
                        
                        </td>
                    </tr>
                    <tr><td height="30"></td></tr>
                </table>

                <!-- Footer divider -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%;">
                            <hr style="border:none; height:1px; background:#D1D5D9;">
                        </td>
                    </tr>
                    <tr><td height="20"></td></tr>
                </table>

                <!-- Footer -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%; font-size:11px; color:#88898c; line-height:1.6;">
                            This is an automated message regarding your subscription status.
                        </td>
                    </tr>
                    <tr><td height="30"></td></tr>
                </table>

            </div>

        </td>
    </tr>
</table>
</body>
</html>


Then, you should return this pure JSON object (as a string, not a dict):

{{"platform_name":"Dropbox","service_name":"Dropbox Plus","start_date":null,"end_date":"2026-05-31","is_trial":false,"already_canceled":true,"price":119.99,"currency":"USD","payment_method":null,"unsubscribe_link":null}}

Below is the explaination. Note that you should NOT return the explanation — only the JSON object above.
**CHAIN-OF-THOUGHT:**

1.  **Email Type Identification**: This email confirms the cancellation of a Dropbox subscription, aligning with CASE A.
2.  **Field Extraction**:
    *   `platform_name`: Identified as "Dropbox" from the subject and body.
    *   `service_name`: Identified as "Dropbox Plus" from the body.
    *   `start_date`: Not explicitly mentioned, so `null`.
    *   `end_date`: The email states, "You'll keep access until May 31, 2026," so it's "2026-05-31".
    *   `is_trial`:  The email doesn't mention a trial, so it's `false`.
    *   `already_canceled`: The email explicitly states "You've canceled Dropbox Plus" and "Cancel was successful", so it's `true`.
    *   `price`:  The email indicates "Annual price was $119.99," so it's `119.99`.
    *   `currency`: Not explicitly mentioned, so it defaults to "USD".
    *   `payment_method`: Not mentioned, so it's `null`.
    *   `unsubscribe_link`: There is no manage or cancel link, so it's `null`.
3.  **JSON Formation**: The extracted values are formatted into the required JSON object.

---


Example 4 (payment receipt):
Subject: Receipt for Adobe Creative Cloud
Sender: message@adobe.com
Body: 
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" style="margin: 0; padding: 0">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title></title>

</head>

<body style="-webkit-font-smoothing: antialiased; width: 100% !important; margin: 0; padding: 0; background-color:#ffffff;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" align="center" style="width:100%; max-width:480px;">
    <tr>
        <td align="center" style="font-family:'Circular','Helvetica Neue',Helvetica,Arial,sans-serif; font-size:14px; color:#555555;">

            <div id="main">

                <!-- Header -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr><td height="30"></td></tr>
                    <tr>
                        <td style="padding:0 6.25%;">
                            <h2 style="margin:0; font-size:28px; line-height:36px; color:#555555;">
                                Payment Confirmation
                            </h2>
                        </td>
                    </tr>
                    <tr><td height="20"></td></tr>
                </table>

                <!-- Body Content -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%; font-size:14px; line-height:20px; color:#616467;">
                            
                            Thank you for your payment of $54.99 on Feb 1, 2026 for Creative Cloud All Apps. Paid with Mastercard 5678. Manage your plan: 
                            <a href="https://account.adobe.com/plans" style="color:#1a73e8; text-decoration:none;">https://account.adobe.com/plans</a>
                        
                        </td>
                    </tr>
                    <tr><td height="30"></td></tr>
                </table>

                <!-- Footer divider -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%;">
                            <hr style="border:none; height:1px; background:#D1D5D9;">
                        </td>
                    </tr>
                    <tr><td height="20"></td></tr>
                </table>

                <!-- Footer -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:0 6.25%; font-size:11px; color:#88898c; line-height:1.6;">
                            This is an automated message regarding your recent payment.
                        </td>
                    </tr>
                    <tr><td height="30"></td></tr>
                </table>

            </div>

        </td>
    </tr>
</table>
</body>
</html>

Then, you should return this pure JSON object (as a string, not a dict):

{{"platform_name":"Adobe","service_name":"Creative Cloud All Apps","start_date":"2026-02-01","end_date":null,"is_trial":false,"already_canceled":false,"price":54.99,"currency":"USD","payment_method":"Mastercard 5678","unsubscribe_link":"https://account.adobe.com/plans"}}

Below is the explaination. Note that you should NOT return the explanation — only the JSON object above.
**CHAIN-OF-THOUGHT:**

1.  **Email Type Identification**: The email is a payment receipt for Adobe Creative Cloud, which is related to a subscription, thus matching CASE A.
2.  **Field Extraction**:
    *   `platform_name`: Identified as "Adobe" from the subject and body.
    *   `service_name`:  Identified as "Creative Cloud All Apps" from the body.
    *   `start_date`: The payment date is Feb 1, 2026 so it should be "2026-02-01".
    *   `end_date`: Not explicitly stated, so `null`.
    *   `is_trial`:  The email doesn't mention a trial, so it's `false`.
    *   `already_canceled`:  The email doesn't mention cancellation, so it's `false`.
    *   `price`: The payment is $54.99, so it's `54.99`.
    *   `currency`: Not explicitly mentioned, so it defaults to "USD".
    *   `payment_method`: The payment method is "Mastercard 5678" per the email, so it's "Mastercard 5678".
    *   `unsubscribe_link`: The email provides a link "https://account.adobe.com/plans" to manage the account, so it's `https://account.adobe.com/plans`.
3.  **JSON Formation**: The extracted values are formatted into the required JSON object.

---

Example 5 (not a subscription — advertisement):
Subject: 50% off all plans this week only!
Sender: deals@someapp.com
Body: Don't miss our biggest sale of the year. Subscribe now and save 50%. Limited time offer.

Then, you should return this pure string with no JSON:

NOT_SUBSCRIPTION

Below is the explaination. Note that you should NOT return the explanation — only the JSON object above.
**CHAIN-OF-THOUGHT:**

1.  **Email Type Identification**: This is an advertisement offering a discount, not a subscription confirmation, bill, or cancellation. This matches CASE B.
2.  **Output**:  The correct output is the string "NOT_SUBSCRIPTION".

--- NOW PROCESS THIS EMAIL ---

Subject: {subject}
Sender: {sender}
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
        prompt = build_parse_prompt(
            subject=em.subject,
            sender=em.sender,
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