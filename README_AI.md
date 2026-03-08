# README_AI.md — SubFlo AI Integration

> **Part 2: Design & Local Django Integration**
> This document describes how AI is integrated into SubFlo, covering the full pipeline from raw user data all the way to the final AI-generated output.

---

## Overview

SubFlo uses **two AI features** working in a hybrid pipeline:

| # | Feature | Model / API | Purpose |
|---|---------|-------------|---------|
| 1 | Subscription Extractor | HuggingFace `Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32` (local) | Extracts structured subscription JSON from raw emails using many-shot prompting |
| 2 | Cancellation Guide Generator | **Google Gemini API** (`gemini-2.5-flash`) | Generates step-by-step, service-specific cancellation guides for the user |

The local HuggingFace model handles the core extraction task — converting raw email text into structured subscription data (platform, price, dates, etc.) that is stored in the database. The Gemini API provides a user-facing feature: generating step-by-step cancellation guides on demand.

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
- The Gemini API key is stored in `.env` and loaded via `django-environ`; it is **never** committed to version control (see `.gitignore`).

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
│  Qwen2.5-0.5B-Instruct     │
│  Many-shot prompt           │
│  "Extract subscription      │
│   JSON from this email"     │
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
│  GEMINI API (on demand)     │
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

### API Alternative (Gemini 2.5 Flash)

| Metric | Value |
|--------|-------|
| Daily requests | 50,000 |
| Avg tokens per request | ~800 input + ~200 output = 1,000 tokens |
| Daily tokens | 50,000,000 (50M) |
| Gemini Flash pricing | ~$0.075 per 1M input tokens / ~$0.30 per 1M output tokens |
| **Daily API cost** | ~$3.75 input + $3.00 output = **~$6.75/day** |
| **Monthly API cost** | **~$200/month** |

### Verdict

At 10,000 daily users, **a hybrid approach is best**. The local model is competitive on cost if you already have a GPU server, but the API wins on simplicity — no model hosting, no OOM errors, no PyTorch dependency management. We would keep the local model for the bulk extraction pipeline (running on a scheduled batch job overnight) and use the API for real-time user-facing features like the cancellation guide.

If forced to choose one: **move to the API** at this scale. The $200/month API bill is comparable to the server cost, but you get zero maintenance, automatic scaling, and consistently faster response times (~2s vs. ~43s on CPU).

---

## 3. Hybrid Potential

Our current architecture already demonstrates the hybrid approach:

```
┌─────────────────────────────────────────────────────┐
│              HYBRID PIPELINE                        │
│                                                     │
│  LOCAL MODEL (free, no API costs)                   │
│  ├── Bulk email parsing (batch/overnight)           │
│  ├── Subscription data extraction                   │
│  └── Runs on server CPU — no per-request cost       │
│                                                     │
│  GEMINI API (pay-per-use, real-time)                │
│  ├── Cancellation guide generation (on demand)      │
│  ├── Only called when user clicks "Generate Guide"  │
│  └── ~$0.0003 per guide request                     │
└─────────────────────────────────────────────────────┘
```

### How they minimize costs together:

1. **The local model handles 90%+ of the workload** — every email that enters the system is parsed locally at zero marginal cost. This is the high-volume, predictable task.

2. **The API handles the 10% that requires creativity** — cancellation guides need up-to-date knowledge about specific services (URLs, cancellation flows), which a static local model cannot provide. This is low-volume (only when users actively request it).

3. **The local model could pre-filter for the API** — if we ever needed the API for email parsing (e.g., the local model fails on a complex email), the local model could act as a first-pass filter. Only emails where the local model returns low-confidence or malformed JSON would be escalated to the API, keeping API costs to a minimum.

4. **Cost comparison at scale:**

| Scenario | Monthly Cost |
|----------|-------------|
| All local (50K emails/day, CPU server) | ~$300 server |
| All API (50K emails/day via Gemini) | ~$200 API |
| **Hybrid** (50K local + 500 guides/day via API) | **~$150 server + ~$4 API = $154** |

The hybrid approach saves ~25–50% compared to going all-in on either option.

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

| Daily Requests | Local Model Cost/req | Gemini API Cost/req | Winner |
|---------------|---------------------|--------------------| -------|
| 500 | $1.00 | $0.0003 | **API** |
| 2,000 | $0.25 | $0.0003 | **API** |
| 5,000 | $0.10 | $0.0003 | **API** (but close) |
| 10,000 | $0.05 | $0.0003 | **Local** (server is amortized) |
| 50,000 | $0.01 | $0.0003 | **Local** (3x cheaper) |

**The break-even point is approximately 5,000–10,000 requests per day.** Below that threshold, the fixed server cost makes the local model more expensive per-request than simply calling the API. Above it, the server cost is amortized across enough requests that local inference becomes significantly cheaper.

### Our Recommendation for SubFlo

For our current stage (university project, <100 users), the **API is more practical** — it requires no GPU server, costs pennies per day, and the free tier covers our usage. As SubFlo scales to production, we would transition the email extraction pipeline to a **dedicated GPU server** running the local model in batch mode, while keeping the Gemini API for the user-facing cancellation guide feature. This hybrid approach gives us the best of both worlds: low cost for high-volume extraction and high quality for on-demand generation.
