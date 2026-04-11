# subscriptions/scrape_view.py
#
# Email Scraping API
#
# Fetches subscription-related emails from Gmail and saves them into EmailMessage model.
# Uses the user's `last_processed_date` as the starting point, then updates it to today
# after a successful scrape.
#
# Endpoint:
#   POST /subscriptions/scrape/
#
# Returns:
#   200 { "saved": <int>, "skipped_duplicates": <int>, "last_processed_date": <YYYY-MM-DD> }
#   403 No Google account linked / no Gmail scope
#   502 Gmail API error

import email
import logging
from datetime import timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone as django_timezone
from django.utils.decorators import method_decorator
from django.views import View

from .models import EmailMessage
from .views import get_google_credentials, decode_message_body, get_header
from accounts.models import UserProfile

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Approach 5: double-gated Gmail query
#
# Gate 1 — sender must look like a transactional/billing sender:
#   billing@, payment@, invoice@, receipt@, subscription@, noreply@, no-reply@
#   These are the addresses that real subscription services send from.
#   This alone cuts newsletters, digests, and promotional mail that happen
#   to mention "unsubscribe" in their footer.
#
# Gate 2 — body/subject must contain subscription-specific phrases:
#   Tighter than bare words — full phrases like "your subscription",
#   "payment confirmation", "next billing date", etc. are extremely unlikely
#   to appear in non-subscription emails.
#
# Both gates must match (AND), so an email needs a billing-type sender
# AND subscription-specific language to pass through.
# ---------------------------------------------------------------------------

_SENDER_FILTER = (
    "from:billing OR "
    "from:payment OR "
    "from:payments OR "
    "from:invoice OR "
    "from:invoices OR "
    "from:receipt OR "
    "from:receipts OR "
    "from:subscription OR "
    "from:subscriptions OR "
    "from:noreply OR "
    "from:no-reply"
)

_KEYWORD_FILTER = (
    '"your subscription" OR '
    '"payment confirmation" OR '
    '"order confirmation" OR '
    '"subscription confirmed" OR '
    '"subscription activated" OR '
    '"subscription canceled" OR '
    '"subscription cancelled" OR '
    '"subscription renewed" OR '
    '"auto-renewal" OR '
    '"auto renewal" OR '
    '"next billing date" OR '
    '"next billing cycle" OR '
    '"trial ends" OR '
    '"trial period" OR '
    '"free trial" OR '
    '"billing summary" OR '
    '"payment failed" OR '
    '"payment declined" OR '
    '"payment received" OR '
    "invoice OR "
    "receipt"
)

# Final query: sender gate AND keyword gate
SUBSCRIPTION_QUERY = f"({_SENDER_FILTER}) ({_KEYWORD_FILTER})"

# Gmail API returns at most 500 per page; we page through all results.
GMAIL_PAGE_SIZE = 500


@method_decorator(login_required, name="dispatch")
class GmailScrapeView(View):
    """
    POST /subscriptions/scrape/

    Scrapes subscription-related emails from the user's Gmail starting from
    `last_processed_date` (inclusive) up to today, saves new ones into
    EmailMessage, then updates `last_processed_date` to today (midnight UTC).

    Idempotent: re-running on the same day is safe — duplicates are skipped
    using the (user, gmail_message_id) unique constraint.
    """

    def get(self, request, *args, **kwargs):
    # def post(self, request, *args, **kwargs):
        user = request.user
        logger.info("Scrape started for user %s", user.username)

        # --- Determine the scrape window ---
        profile = UserProfile.objects.get(user=user)
        after_date = profile.last_processed_date.date()
        gmail_query = f"{SUBSCRIPTION_QUERY} after:{after_date.strftime('%Y/%m/%d')}"
        logger.info("Gmail query: %s", gmail_query)

        # --- Get Google credentials ---
        try:
            creds = get_google_credentials(user)
        except ValueError as exc:
            logger.error("Credentials error for user %s: %s", user.username, exc)
            return JsonResponse({"error": str(exc)}, status=403)

        # --- Fetch all matching message IDs from Gmail (paginated) ---
        try:
            service = build("gmail", "v1", credentials=creds)
            message_refs = []
            page_token = None
            page_num = 0

            while True:
                page_num += 1
                list_kwargs = {
                    "userId": "me",
                    "maxResults": GMAIL_PAGE_SIZE,
                    "q": gmail_query,
                }
                if page_token:
                    list_kwargs["pageToken"] = page_token

                response = service.users().messages().list(**list_kwargs).execute()
                batch = response.get("messages", [])
                message_refs.extend(batch)
                logger.info(
                    "Page %d: got %d message IDs (total so far: %d)",
                    page_num, len(batch), len(message_refs),
                )

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as exc:
            logger.exception("Gmail API list error for user %s: %s", user.username, exc)
            return JsonResponse({"error": f"Gmail API error: {exc.reason}"}, status=502)

        logger.info("Total matching messages found: %d", len(message_refs))

        if not message_refs:
            _update_last_processed_date(profile)
            logger.info("No messages found. last_processed_date updated to today.")
            return JsonResponse({
                "saved": 0,
                "skipped_duplicates": 0,
                "last_processed_date": profile.last_processed_date.date().isoformat(),
            })

        # --- Fetch full details and save to EmailMessage ---
        saved = 0
        skipped_duplicates = 0

        existing_ids = set(
            EmailMessage.objects.filter(user=user).values_list("gmail_message_id", flat=True)
        )
        logger.info("User already has %d EmailMessage(s) in DB", len(existing_ids))

        try:
            for i, ref in enumerate(message_refs, start=1):
                gmail_msg_id = ref["id"]

                if gmail_msg_id in existing_ids:
                    skipped_duplicates += 1
                    continue

                try:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=gmail_msg_id, format="full")
                        .execute()
                    )
                except HttpError as exc:
                    logger.warning("Failed to fetch message %s: %s", gmail_msg_id, exc)
                    continue

                headers  = msg.get("payload", {}).get("headers", [])
                subject  = get_header(headers, "Subject") or "(No Subject)"
                sender   = get_header(headers, "From")    or "(Unknown Sender)"
                date_str = get_header(headers, "Date")    or ""

                received_date = django_timezone.now()
                if date_str:
                    try:
                        parsed_dt = email.utils.parsedate_to_datetime(date_str)
                        received_date = parsed_dt.astimezone(timezone.utc)
                    except Exception:
                        pass

                raw_body = decode_message_body(msg.get("payload", {}))

                EmailMessage.objects.create(
                    user=user,
                    gmail_message_id=gmail_msg_id,
                    subject=subject,
                    sender=sender,
                    received_date=received_date,
                    raw_email_body=raw_body,
                )
                existing_ids.add(gmail_msg_id)
                saved += 1

                if i % 10 == 0:
                    logger.info(
                        "Progress: %d/%d processed (%d saved, %d skipped)",
                        i, len(message_refs), saved, skipped_duplicates,
                    )

        except HttpError as exc:
            logger.exception("Gmail API fetch error for user %s: %s", user.username, exc)
            return JsonResponse({"error": f"Gmail API error: {exc.reason}"}, status=502)

        _update_last_processed_date(profile)
        logger.info(
            "Scrape complete for user %s: saved=%d, skipped=%d, last_processed_date=%s",
            user.username, saved, skipped_duplicates,
            profile.last_processed_date.date().isoformat(),
        )

        return JsonResponse({
            "saved": saved,
            "skipped_duplicates": skipped_duplicates,
            "last_processed_date": profile.last_processed_date.date().isoformat(),
        })


def _update_last_processed_date(profile):
    """Set last_processed_date to today at midnight UTC and save."""
    today_midnight = django_timezone.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    profile.last_processed_date = today_midnight
    profile.save(update_fields=["last_processed_date"])
