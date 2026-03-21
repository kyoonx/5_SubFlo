# subscriptions/views.py
#
# Gmail Fetch API
#
# Retrieves the authenticated user's Gmail messages using their Google SSO token
# stored by django-allauth. No token.json file needed — tokens live in the DB.
#
# Endpoints:
#   GET /subscriptions/emails/
#       ?max_results=<int>   — number of emails to return (default: 20, max: 100)
#       ?after=<YYYY-MM-DD>  — only return emails received after this date
#
#   GET /subscriptions/emails/debug/   ← TEMPORARY, remove before prod
#       Dumps allauth token state for the current user so you can diagnose issues.
#
# Returns:
#   200 { "emails": [ { subject, sender, received_date, raw_email_body, message_id }, ... ] }
#   400 Bad query params
#   403 No Google account linked / Gmail scope not granted
#   502 Gmail API error

import base64
import email
import logging
from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# ---------------------------------------------------------------------------
# Helper: build a valid, refreshed Google Credentials object from allauth DB
# ---------------------------------------------------------------------------

def get_google_credentials(user):
    """
    Retrieve and (if needed) refresh the Google OAuth2 credentials for `user`
    using the tokens stored by django-allauth.

    Returns a google.oauth2.credentials.Credentials object, or raises
    ValueError with a human-readable message if something is missing.
    """
    # 1. Find the linked Google social account
    try:
        social_account = SocialAccount.objects.get(user=user, provider="google")
    except SocialAccount.DoesNotExist:
        raise ValueError("No Google account linked to this user.")

    # 2. Get the stored token row
    try:
        token_obj = SocialToken.objects.get(account=social_account)
    except SocialToken.DoesNotExist:
        raise ValueError("No Google token found. The user may need to re-authenticate.")

    # 3. Check that we actually have a refresh token
    #    (absent if the user logged in before the offline scope was added)
    if not token_obj.token_secret:
        raise ValueError(
            "No refresh token available. The user must re-authenticate with Google "
            "to grant offline access."
        )

    # 4. Get the OAuth client ID/secret from the allauth SocialApp config
    try:
        app = SocialApp.objects.get(provider="google")
    except SocialApp.DoesNotExist:
        raise ValueError("Google SocialApp is not configured in the Django admin.")

    # 5. Build the Credentials object
    creds = Credentials(
        token=token_obj.token,
        refresh_token=token_obj.token_secret,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=app.client_id,
        client_secret=app.secret,
        scopes=GMAIL_SCOPES,
    )

    # 6. Refresh if expired
    if creds.expired:
        creds.refresh(Request())
        # Persist the new access token back to the DB
        token_obj.token = creds.token
        token_obj.save(update_fields=["token"])
        logger.info("Refreshed Google access token for user %s", user.username)

    return creds


# ---------------------------------------------------------------------------
# Helper: decode a Gmail message part into plain text
# ---------------------------------------------------------------------------

def decode_message_body(payload):
    """
    Recursively walk a Gmail message payload and return the plain-text body.
    Falls back to HTML body if no text/plain part is found.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    if mime_type == "text/html" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    # Multipart: recurse into parts
    for part in payload.get("parts", []):
        result = decode_message_body(part)
        if result:
            return result

    return ""


# ---------------------------------------------------------------------------
# Helper: extract a specific header value from a Gmail message
# ---------------------------------------------------------------------------

def get_header(headers, name):
    """Return the value of the first header matching `name` (case-insensitive)."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


# ---------------------------------------------------------------------------
# DEBUG view — remove before production
# ---------------------------------------------------------------------------

@method_decorator(login_required, name="dispatch")
class GmailDebugView(View):
    """
    GET /subscriptions/emails/debug/
    Shows the allauth token state for the current user.
    Use this to diagnose missing token issues. Remove before production.
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        result = {
            "django_user": user.username,
            "django_user_id": user.id,
            "social_accounts": [],
            "social_tokens": [],
            "social_apps": [],
        }

        # All social accounts for this user
        accounts = SocialAccount.objects.filter(user=user)
        for acc in accounts:
            result["social_accounts"].append({
                "id": acc.id,
                "provider": acc.provider,
                "uid": acc.uid,
                "extra_data_keys": list(acc.extra_data.keys()) if acc.extra_data else [],
            })

            # Tokens linked to this account
            tokens = SocialToken.objects.filter(account=acc)
            for tok in tokens:
                result["social_tokens"].append({
                    "account_id": acc.id,
                    "provider": acc.provider,
                    "has_token": bool(tok.token),
                    "token_preview": tok.token[:20] + "..." if tok.token else None,
                    "has_token_secret": bool(tok.token_secret),   # this is the refresh token
                    "token_secret_preview": tok.token_secret[:20] + "..." if tok.token_secret else None,
                    "expires_at": str(tok.expires_at) if tok.expires_at else None,
                })

        # All configured SocialApps
        apps = SocialApp.objects.all()
        for app in apps:
            result["social_apps"].append({
                "id": app.id,
                "provider": app.provider,
                "name": app.name,
                "has_client_id": bool(app.client_id),
                "has_secret": bool(app.secret),
            })

        return JsonResponse(result, json_dumps_params={"indent": 2})


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

@method_decorator(login_required, name="dispatch")
class GmailFetchView(View):
    """
    GET /subscriptions/emails/
    Fetches Gmail messages for the currently logged-in user and returns
    them as JSON shaped to match the EmailMessage model.

    Query params:
        max_results (int, default 20): how many emails to fetch (max 100)
        after (YYYY-MM-DD): only return emails received after this date
    """

    MAX_RESULTS_LIMIT = 100

    def get(self, request, *args, **kwargs):

        # --- Parse query params ---
        try:
            max_results = int(request.GET.get("max_results", 20))
            if not (1 <= max_results <= self.MAX_RESULTS_LIMIT):
                return JsonResponse(
                    {"error": f"max_results must be between 1 and {self.MAX_RESULTS_LIMIT}."},
                    status=400,
                )
        except ValueError:
            return JsonResponse({"error": "max_results must be an integer."}, status=400)

        after_date_str = request.GET.get("after")
        gmail_query = ""
        if after_date_str:
            try:
                after_dt = datetime.strptime(after_date_str, "%Y-%m-%d")
                # Gmail query syntax: after:YYYY/MM/DD
                gmail_query = f"after:{after_dt.strftime('%Y/%m/%d')}"
            except ValueError:
                return JsonResponse(
                    {"error": "after must be a date in YYYY-MM-DD format."},
                    status=400,
                )

        # --- Get Google credentials ---
        try:
            creds = get_google_credentials(request.user)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=403)

        # --- Call Gmail API ---
        try:
            service = build("gmail", "v1", credentials=creds)

            # Step 1: list message IDs
            list_kwargs = {
                "userId": "me",
                "maxResults": max_results,
            }
            if gmail_query:
                list_kwargs["q"] = gmail_query

            list_response = service.users().messages().list(**list_kwargs).execute()
            message_refs = list_response.get("messages", [])

            if not message_refs:
                return JsonResponse({"emails": [], "count": 0})

            # Step 2: fetch full details for each message
            emails = []
            for ref in message_refs:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=ref["id"], format="full")
                    .execute()
                )

                headers = msg.get("payload", {}).get("headers", [])
                subject      = get_header(headers, "Subject") or "(No Subject)"
                sender       = get_header(headers, "From")    or "(Unknown Sender)"
                date_str     = get_header(headers, "Date")    or ""

                # Parse the Date header into an ISO 8601 string
                received_date = None
                if date_str:
                    try:
                        # email.utils.parsedate_to_datetime handles RFC 2822 format
                        parsed_dt = email.utils.parsedate_to_datetime(date_str)
                        # Normalise to UTC
                        received_date = parsed_dt.astimezone(timezone.utc).isoformat()
                    except Exception:
                        received_date = date_str  # Store raw string if parsing fails

                raw_body = decode_message_body(msg.get("payload", {}))

                emails.append({
                    "message_id": ref["id"],   # Gmail's internal ID — useful for deduplication
                    "subject": subject,
                    "sender": sender,
                    "received_date": received_date,
                    "raw_email_body": raw_body,
                })

        except HttpError as exc:
            logger.exception("Gmail API error for user %s: %s", request.user.username, exc)
            return JsonResponse(
                {"error": f"Gmail API error: {exc.reason}"},
                status=502,
            )

        return JsonResponse({
            "emails": emails,
            "count": len(emails),
        })
