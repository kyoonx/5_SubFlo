# README_AI.md — SubFlo AI Integration

> **Part 2: Design & Local Django Integration**
> This document describes how AI is integrated into SubFlo, covering the full pipeline from raw user data all the way to the final AI-generated output.

---

## Overview

SubFlo uses **two AI features** working in a hybrid pipeline:

| # | Feature | Model / API | Purpose |
|---|---------|-------------|---------|
| 1 | Subscription Extractor | **Illinois Chat** — model from `ILLINOIS_MODEL` (default `qwen3:32b`) | Extracts structured subscription JSON from raw email bodies via API |
| 2 | Cancellation Guide Generator | **Illinois Chat** — same client / model env as email parser | Generates step-by-step, service-specific cancellation guides for the user |

**Illinois Chat** handles both the email extraction task (via `parse_email_to_json` in `subscriptions/email_parser.py`) and the user-facing cancellation guide (`POST /subscriptions/cancel-guide/` in `subscriptions/ai_guide_view.py`), using `subscriptions/illinois_chat_client.py` for HTTP calls.

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
| `subscription_name` | Extracted / Manual | Illinois Chat cancellation guide prompt |
| `billing_cycle` | Extracted / Manual | Displayed in dashboard |

---

## 2. Preprocessing — How is data cleaned before sending to the LLM?

All user data is preprocessed in `subscriptions/preprocessing.py` before being passed to Illinois Chat (email extraction and cancellation guide).

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

### Step 3 — Prompt construction for cancellation guide
The subscription name goes through a keyword blocklist check (see Safety Guardrails below) before being embedded into the structured JSON prompt in `build_cancellation_prompt()` (`subscriptions/ai_guide_view.py`).

### Why this matters
- Raw email HTML can confuse token-based models — stripping tags prevents wasted context.
- Truncation ensures the local model stays within its 512-token limit.
- Structured prompts make the hosted model’s JSON output easier to validate and render in a Django template.

---

## 3. Safety Guardrails — Preventing malicious inputs and broken outputs

### A. Input Guardrails (Before sending to any model)

| Threat | Mitigation |
|--------|-----------|
| **Prompt injection** | Subscription name is inserted as a plain string inside a fixed template. User input never directly appends instructions to the system prompt. |
| **XSS / HTML injection** | All user-supplied text is HTML-escaped using Django's `escape()` before rendering in templates. |
| **Excessively long inputs** | Inputs are hard-truncated to 512 characters before the local model and 200 characters before the cancellation-guide prompt. |
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
| **Model refusal response** | If the response contains phrases like `"I'm sorry"` or `"I cannot"`, the UI shows a generic fallback instead of the raw refusal. |
| **Runaway token output** | Illinois Chat request uses non-streaming mode; the prompt caps steps and the client uses a HTTP timeout. |
| **Rate limit / quota errors** | `429` and `503` errors are caught and surfaced to the user as a friendly toast notification. |

### C. Django-Level Security
- All AI views require `@login_required` — unauthenticated users cannot trigger API calls.
- CSRF tokens are enforced on all POST forms.
- The Illinois Chat API key (`ILLINOIS_API_KEY`) is stored in `.env` and loaded via `django-environ`; it is **never** committed to version control (see `.gitignore`).

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
│  ILLINOIS CHAT (UIUC.chat)  │
│  Extract subscription JSON  │
│  from email body            │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  NORMALIZE + VALIDATE       │
│  - Type coercion            │
│  - Field mapping to models  │
└────────────┬────────────────┘
             │
             ▼
   Saved to DB as Subscription
   + EmailMessage records
             │
             ▼
┌─────────────────────────────┐
│  ILLINOIS CHAT (UIUC.chat)  │
│  e.g. qwen3:32b (ILLINOIS_MODEL) │
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
ILLINOIS_API_KEY=your_key_from_chat.illinois.edu_Settings_API_Keys
ILLINOIS_API_URL=https://chat.illinois.edu/api/chat-api/chat
ILLINOIS_PROJECT_NAME=Subflo
ILLINOIS_MODEL=qwen3:32b
```

`ILLINOIS_PROJECT_NAME` is the Request Builder `course_name` for your project (this app defaults to **Subflo**). Set **`ILLINOIS_MODEL`** to the exact model id from the Request Builder / LLMs tab (default **qwen3:32b**). The client always uses **streaming**. See [UIUC.chat API endpoints](https://docs.uiuc.chat/api/endpoints) and `.env.example`.

## Dependencies Added

```
# requirements.txt (partial; see file)
requests
transformers>=4.40.0
torch>=2.0.0
accelerate>=0.30.0
beautifulsoup4>=4.12.0
```

---
---

# Part 3: Production Reflection

## 1. The Size vs. Quality Trade-off

We tested **15 models** across 5 size categories against our subscription email extraction task. Every model received the same 3 test emails (YouTube Premium, Spotify, Netflix) and was evaluated on JSON structure correctness, field accuracy, and inference time.

### Results Matrix

| Category | Model | Inference Time | JSON Valid? | Fields Correct |
|----------|-------|---------------|-------------|----------------|
| **Ultra-Light (<1B)** | `qwen/Qwen2.5-0.5B-Instruct` | 200.0s | Yes (1/3) | Partial — hallucinated on emails 2–3 |
| | `JayHyeon/Qwen_0.5-MDPO` | 107.4s | Mixed | Missing fields, extra keys |
| | `mlx-community/Josiefied-Qwen2.5-0.5B-Instruct` | **135.5s** | **Yes (3/3)** | **Most fields correct with many-shot** |
| **Small (1B–3B)** | `ibm-granite/granite-3.1-2b-instruct` | 550.3s | Yes | Good but slower |
| | `iFaz/llama32_3B_en_emo_v1` | 912.9s | Partial | Verbose, extra commentary |
| | `DeepMount00/Qwen2-1.5B-Ita` | 356.3s | Yes | Good but 2.6x slower than winner |
| **Medium (3B–7B)** | `weathermanj/Menda-3B-500` | 498.5s | Yes | Accurate but slow |
| | `MaziyarPanahi/calme-2.1-phi3-4b` | 968.9s | Yes | Over-engineered output |
| | `MaziyarPanahi/calme-3.3-baguette-3b` | 537.6s | Yes | Good quality, 4x slower |
| **Large (7B–9B)** | `ZeroXClem/Qwen2.5-7B-HomerAnvita-NerdMix` | 684.8s | Yes | Very accurate |
| | `ibm-granite/granite-3.2-8b-instruct` | 1,892.0s | Yes | Excellent but 14x slower |
| | `Goekdeniz-Guelmez/josie-7b-v6.0` | 3,797.3s | Yes | Excellent but 28x slower |
| **Ultra-Large (9–12B)** | `recoilme/recoilme-gemma-2-9B-v0.3` | 6,185.9s | Yes | Near-perfect |
| | `princeton-nlp/gemma-2-9b-it-DPO` | 1,584.3s | Yes | Near-perfect |
| | `01-ai/Yi-1.5-9B-Chat` | 5,066.3s | Yes | Near-perfect |

### Sweet Spot: Ultra-Light (<1B)

The **Ultra-Light category** provided the clear sweet spot for our specific task. Our chosen model (`Josiefied-Qwen2.5-0.5B-Instruct`) at only **0.5B parameters** produced correct JSON with all required fields populated when given the many-shot prompt — the same quality as models 14–18x its size.

**Why?** Our task is structured extraction, not creative reasoning. The email format is predictable (sender, subject, price, date), and the many-shot examples teach the model the exact output schema. A massive 9B model doesn't understand "extract the price from this email" fundamentally better than a 0.5B model — both are pattern matching. The 9B model just takes 45x longer to do it.

### Estimated Server Costs by Model Size

| Category | Params | RAM Required | GPU Needed? | Est. Monthly Server Cost |
|----------|--------|-------------|-------------|-------------------------|
| Ultra-Light (<1B) | 0.5B | ~2 GB | No (CPU-only) | **$5–15** (shared VPS) |
| Small (1B–3B) | 1.5–3B | ~6–12 GB | Recommended | $50–100 (4-core + 16 GB RAM) |
| Medium (3B–7B) | 3–7B | ~14–28 GB | Yes | $150–300 (GPU instance) |
| Large (7B–9B) | 7–9B | ~28–36 GB | Yes (16 GB VRAM) | $300–500 (A10G or T4 GPU) |
| Ultra-Large (9–12B) | 9–12B | ~36–48 GB | Yes (24 GB VRAM) | $500–1,000 (A100 GPU) |

---

## 2. Cost & Scaling — 10,000 Daily Users

### Local Model (Current Setup)

Our 0.5B model takes ~43 seconds per email on CPU. At 10,000 users averaging 5 emails each:

| Metric | Value |
|--------|-------|
| Daily requests | 50,000 |
| Time per request | ~43 seconds (CPU) / ~5 seconds (GPU) |
| Sequential throughput | ~2,000 requests/day (1 CPU core) |
| Cores needed (CPU) | **25 cores** to handle daily load |
| Server cost (CPU) | ~$200–400/month (e.g., AWS c6i.8xlarge) |
| Server cost (GPU) | ~$150–300/month (1x T4 GPU handles ~17,000 req/day) |

### API alternative (hosted cancellation guide — Illinois Chat)

| Metric | Value |
|--------|-------|
| Daily requests | 50,000 |
| Avg tokens per request | ~800 input + ~200 output = 1,000 tokens |
| Daily tokens | 50,000,000 (50M) |
| Pricing | Depends on provider; many **UIUC.chat** hosted models are **free within campus quota** (see UIUC.chat docs). Commercial APIs (e.g. GPT‑4 class) are often ~$0.075–$0.30 per 1M tokens (illustrative). |
| **Daily API cost** | Highly variable — **often near $0** for campus-hosted models at project scale |
| **Monthly API cost** | Compare UIUC.chat / provider pricing vs. a fixed GPU server |

### Verdict

At 10,000 daily users, cost and quota planning depend on **UIUC.chat** terms for your project. The **current SubFlo codebase** routes **both** email JSON extraction and cancellation guides through **Illinois Chat**, so there is no separate local HF server for email in this branch—only preprocessing and Django orchestration run locally.

---

## 3. Current pipeline (Illinois Chat for both paths)

```
┌─────────────────────────────────────────────────────┐
│           ILLINOIS CHAT (UIUC.chat)                 │
│                                                     │
│  ├── Email → JSON (`parse_email_to_json`)           │
│  │     Triggered when ingesting / parsing mail      │
│  └── Cancellation guide (`POST …/cancel-guide/`)   │
│        On demand when the user requests a guide      │
│                                                     │
│  Same API client, model, and API key configuration │
└─────────────────────────────────────────────────────┘
```

**Notes:** Volume-sensitive deployments should monitor Illinois Chat usage. Email parsing uses a longer HTTP **timeout** (180s) than the default client timeout for short guide requests (120s).

---

## 4. Cost Comparison — When to Use Pre-Trained vs. Paid API

### Assumed Server Configuration

| Component | Spec |
|-----------|------|
| CPU | 16-core |
| GPU | 16 GB VRAM (e.g., NVIDIA T4) |
| RAM | 64 GB |
| Storage | 1 TB SSD |
| **Est. monthly cost** | **~$400–600/month** (cloud) or **~$2,000 one-time** (on-prem) |

### Decision Framework

| Condition | Use Local Pre-Trained Model | Use Paid API |
|-----------|-----------------------------|--------------|
| **Request volume** | > 5,000 requests/day (amortizes server cost) | < 5,000 requests/day (API is cheaper) |
| **Latency requirement** | Batch/async OK (e.g., overnight email processing) | Real-time required (< 3s response) |
| **Task complexity** | Structured extraction (predictable format) | Creative generation (guides, summaries) |
| **Data sensitivity** | PII in emails — must stay on-premises | Non-sensitive data acceptable to send to third party |
| **Output quality** | 0.5B model output is "good enough" (>90% field accuracy) | Needs near-perfect output (e.g., medical, legal) |
| **Internet dependency** | Must work offline / air-gapped environments | Reliable internet available |
| **Scaling pattern** | Steady, predictable load | Spiky/bursty traffic (API auto-scales) |

### Break-Even Analysis

At our server spec ($500/month), with the local 0.5B model handling ~17,000 GPU requests/day:

| Daily Requests | Local Model Cost/req | Hosted API Cost/req | Winner |
|---------------|---------------------|--------------------| -------|
| 500 | $1.00 | ~$0 (illustrative) | **API** |
| 2,000 | $0.25 | ~$0 (illustrative) | **API** |
| 5,000 | $0.10 | ~$0 (illustrative) | **API** (but close) |
| 10,000 | $0.05 | ~$0 (illustrative) | **Local** (server is amortized) |
| 50,000 | $0.01 | ~$0 (illustrative) | **Local** (3x cheaper) |

**The break-even point is approximately 5,000–10,000 requests per day.** Below that threshold, the fixed server cost makes the local model more expensive per-request than simply calling the API. Above it, the server cost is amortized across enough requests that local inference becomes significantly cheaper.

### Our Recommendation for SubFlo

For our current stage (university project, <100 users), **Illinois Chat** for **both** extraction and guides avoids hosting large models on student hardware while keeping one integration surface (`illinois_chat_client.py`).
