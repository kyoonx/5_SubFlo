# README_AI.md — SubFlo AI Integration

> **Part 2: Design & Local Django Integration**
> This document describes how AI is integrated into SubFlo, covering the full pipeline from raw user data all the way to the final AI-generated output.

---

## Overview

SubFlo uses **two AI features** working in a hybrid pipeline:

| # | Feature | Model / API | Purpose |
|---|---------|-------------|---------|
| 1 | Subscription Extractor | HuggingFace `distilbert-base-uncased-finetuned-sst-2-english` (local) | Classifies whether an email is subscription-related before sending it downstream |
| 2 | Cancellation Guide Generator | **Google Gemini API** (`gemini-2.5-flash`) | Generates step-by-step, service-specific cancellation guides for the user |

The local HuggingFace model acts as a **filter/gate** — only emails it confidently marks as subscription-related are passed to the Gemini API. This keeps costs low and prompts clean.

---

## 1. Data Input — How is user data captured?

User data enters SubFlo through **two pathways**:

### A. Email Scanning (Gmail OAuth)
- After the user authenticates via **Google SSO** (`accounts` app), SubFlo requests read-only Gmail access using the `google-auth` OAuth2 flow.
- The `subscriptions` app fetches the user's email headers and body snippets via the Gmail API.
- Each email is stored as an `EmailMessage` model instance, linked to the authenticated `User`.

### B. Manual Dashboard Input
- Users can manually add a subscription from the dashboard by filling in the service name, billing cycle, and cost.
- This data is captured via a standard Django `ModelForm` and stored as a `Subscription` model instance.

### What data fields are used?
| Field | Source | Used For |
|-------|--------|----------|
| `email_subject` | Gmail API | Local model classification |
| `email_body_snippet` | Gmail API | Local model classification |
| `subscription_name` | Extracted / Manual | Gemini cancellation guide prompt |
| `billing_cycle` | Extracted / Manual | Displayed in dashboard |

---

## 2. Preprocessing — How is data cleaned before sending to the LLM?

All user data is preprocessed in `subscriptions/preprocessing.py` before being passed to either the local model or the Gemini API.

### Step 1 — Input Sanitization
```python
def sanitize_text(text: str) -> str:
    # Strip HTML tags (emails often contain HTML)
    text = BeautifulSoup(text, "html.parser").get_text()
    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Truncate to max token budget (512 chars for local model)
    return text[:512]
```

### Step 2 — Subject + Body Fusion
The email subject and body snippet are combined into a single string for the local classifier:
```
[SUBJECT]: Cancel your Netflix subscription | [BODY]: Your payment of $15.99 is due...
```

### Step 3 — Prompt Construction for Gemini
The subscription name goes through a keyword blocklist check (see Safety Guardrails below) before being embedded into a structured prompt template:
```
You are a helpful assistant. Provide a clear, numbered, step-by-step guide
for how a user can cancel their {subscription_name} subscription.
Include: website URL, estimated time, and what to watch out for (e.g. hidden
cancellation flows, retention offers). Keep the guide under 300 words.
```

### Why this matters
- Raw email HTML can confuse token-based models — stripping tags prevents wasted context.
- Truncation ensures the local model stays within its 512-token limit.
- Structured prompts make Gemini's output more predictable and easier to render in a Django template.

---

## 3. Safety Guardrails — Preventing malicious inputs and broken outputs

### A. Input Guardrails (Before sending to any model)

| Threat | Mitigation |
|--------|-----------|
| **Prompt injection** | Subscription name is inserted as a plain string inside a fixed template. User input never directly appends instructions to the system prompt. |
| **XSS / HTML injection** | All user-supplied text is HTML-escaped using Django's `escape()` before rendering in templates. |
| **Excessively long inputs** | Inputs are hard-truncated to 512 characters before the local model and 200 characters before Gemini prompt construction. |
| **Keyword blocklist** | A blocklist (`BLOCKED_KEYWORDS`) rejects inputs containing words like `ignore previous instructions`, `jailbreak`, `system:`, `<script>`, etc. |
| **Empty / whitespace-only inputs** | Views return a `400 Bad Request` with a user-friendly error message if the sanitized input is empty after stripping. |

```python
BLOCKED_KEYWORDS = [
    "ignore previous", "jailbreak", "system:", "<script>",
    "forget instructions", "pretend you are", "act as"
]

def is_safe_input(text: str) -> bool:
    lower = text.lower()
    return not any(kw in lower for kw in BLOCKED_KEYWORDS)
```

### B. Output Guardrails (After receiving model response)

| Threat | Mitigation |
|--------|-----------|
| **Empty / null API response** | Wrapped in `try/except`; a fallback message ("Guide temporarily unavailable") is shown. |
| **Gemini refusal response** | If the response contains phrases like `"I'm sorry"` or `"I cannot"`, the UI shows a generic fallback instead of the raw refusal. |
| **Runaway token output** | `max_output_tokens=2048` is set in every Gemini API call. |
| **Rate limit / quota errors** | `429` and `503` errors are caught and surfaced to the user as a friendly toast notification. |

### C. Django-Level Security
- All AI views require `@login_required` — unauthenticated users cannot trigger API calls.
- CSRF tokens are enforced on all POST forms.
- The Gemini API key is stored in `.env` and loaded via `python-decouple`; it is **never** committed to version control (see `.gitignore`).

---

## Pipeline Diagram

```
User's Gmail
     │
     ▼
EmailMessage stored in DB
     │
     ▼
┌─────────────────────────────┐
│   PREPROCESSING             │
│  - Strip HTML               │
│  - Truncate to 512 chars    │
│  - Fuse subject + body      │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  LOCAL MODEL (HuggingFace)  │
│  DistilBERT SST-2           │
│  "Is this subscription      │
│   related?"                 │
└────────────┬────────────────┘
             │  POSITIVE (subscription-related)
             ▼
┌─────────────────────────────┐
│  SAFETY CHECK               │
│  - Keyword blocklist        │
│  - Length check             │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  GEMINI API                 │
│  gemini-2.5-flash           │
│  "Generate cancellation     │
│   guide for {service}"      │
└────────────┬────────────────┘
             │
             ▼
      Rendered in Django
      Template as numbered
      step-by-step guide
```

---

## Environment Setup

Add the following to your `.env` file (see `.env.example`):

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

## Dependencies Added

```
# requirements.txt additions
google-genai>=1.0.0
transformers>=4.40.0
torch>=2.0.0
beautifulsoup4>=4.12.0
python-decouple>=3.8
```
