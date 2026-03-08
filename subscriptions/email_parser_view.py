# subscriptions/email_parser_view.py
#
# Part 2 #2 — Local LLM Integration: HuggingFace Model
# Model: mlx-community/Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32
# Strategy: Many-shot prompting (from ai_prototype.ipynb evaluation)
#
# Usage:
#   POST /subscriptions/parse-email/
#   Body: { "raw_email": "From: Netflix <info@netflix.com>..." }
#   Returns: JSON with extracted subscription fields
#
#   GET /subscriptions/parse-email/
#   Renders the email parser UI template
#
# The model weights are downloaded automatically by the transformers library
# on first run (~1 GB). Subsequent runs use the cached weights.

import re
import json
import logging
import time

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.html import escape

from .preprocessing import clean_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loading (lazy — only loaded on first request)
# ---------------------------------------------------------------------------

MODEL_NAME = "mlx-community/Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32"
_model = None
_tokenizer = None


def get_model_and_tokenizer():
    """Lazy-load the model and tokenizer on first call, then cache."""
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Loading local LLM: %s", MODEL_NAME)
        start = time.perf_counter()

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype="auto",
            device_map="auto",
        )

        elapsed = time.perf_counter() - start
        logger.info("Model loaded in %.1f seconds", elapsed)

    return _model, _tokenizer


# ---------------------------------------------------------------------------
# Many-shot prompt (best strategy from ai_prototype.ipynb evaluation)
# ---------------------------------------------------------------------------

def build_extraction_prompt(email_content: str) -> str:
    """
    Many-shot prompt with 4 examples — proved most reliable for
    structured JSON extraction in the notebook evaluation.
    """
    return f"""Extract subscription information from emails. Return only valid JSON with these exact fields.

Example 1:
Email: "From: Spotify <noreply@spotify.com>\\nTrial started: Jan 10, 2026\\nTrial ends: Feb 10, 2026\\nAfter trial: $9.99/month"
{{
  "platform_name": "Spotify",
  "service_name": "Spotify Premium",
  "start_date": "2026-01-10",
  "end_date": "2026-02-10",
  "is_trial": true,
  "already_canceled": false,
  "price": 9.99,
  "currency": "USD",
  "payment_method": null,
  "unsubscribe_link": null
}}

Example 2:
Email: "From: Apple <noreply@apple.com>\\niCloud+ 50GB\\n$0.99/month\\nStarted: March 1, 2026\\nPayment: Apple Pay"
{{
  "platform_name": "Apple",
  "service_name": "iCloud+ 50GB",
  "start_date": "2026-03-01",
  "end_date": null,
  "is_trial": false,
  "already_canceled": false,
  "price": 0.99,
  "currency": "USD",
  "payment_method": "Apple Pay",
  "unsubscribe_link": null
}}

Example 3:
Email: "From: Dropbox <no-reply@dropbox.com>\\nProfessional Plan\\n$19.99/month\\nCanceled\\nEnds: April 30, 2026"
{{
  "platform_name": "Dropbox",
  "service_name": "Professional Plan",
  "start_date": null,
  "end_date": "2026-04-30",
  "is_trial": false,
  "already_canceled": true,
  "price": 19.99,
  "currency": "USD",
  "payment_method": null,
  "unsubscribe_link": null
}}

Example 4:
Email: "From: Adobe <message@adobe.com>\\nCreative Cloud\\n$54.99/month\\nMastercard 5678\\nManage: adobe.com/account"
{{
  "platform_name": "Adobe",
  "service_name": "Creative Cloud",
  "start_date": null,
  "end_date": null,
  "is_trial": false,
  "already_canceled": false,
  "price": 54.99,
  "currency": "USD",
  "payment_method": "Mastercard 5678",
  "unsubscribe_link": "adobe.com/account"
}}

Now extract from this email:
{email_content}

JSON output:"""


# ---------------------------------------------------------------------------
# Model inference
# ---------------------------------------------------------------------------

def run_local_model(email_content: str) -> dict:
    """
    Run the local HuggingFace model on raw email content.
    Returns a parsed dict of subscription fields.
    """
    model, tokenizer = get_model_and_tokenizer()

    prompt = build_extraction_prompt(email_content)

    messages = [{"role": "user", "content": prompt}]

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        text = prompt

    model_inputs = tokenizer([text], return_tensors="pt", padding=True).to(model.device)

    start = time.perf_counter()
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=256,
        do_sample=False,
    )
    elapsed = time.perf_counter() - start
    logger.info("Inference completed in %.1f seconds", elapsed)

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    raw_output = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
    raw_output = re.sub(r"\s*```$", "", raw_output)

    brace_start = raw_output.find("{")
    brace_end = raw_output.rfind("}") + 1
    if brace_start != -1 and brace_end > brace_start:
        raw_output = raw_output[brace_start:brace_end]

    parsed = json.loads(raw_output)
    return parsed, elapsed


# ---------------------------------------------------------------------------
# Field normalization — align model output with Django model fields
# ---------------------------------------------------------------------------

EXPECTED_FIELDS = {
    "platform_name": str,
    "service_name": str,
    "start_date": str,
    "end_date": str,
    "is_trial": bool,
    "already_canceled": bool,
    "price": float,
    "currency": str,
    "payment_method": str,
    "unsubscribe_link": str,
}


def normalize_parsed_data(raw: dict) -> dict:
    """Ensure all expected fields exist and have the right types."""
    result = {}
    for field, expected_type in EXPECTED_FIELDS.items():
        value = raw.get(field)
        if value is None or value == "null" or value == "None":
            result[field] = None
            continue
        if expected_type == bool:
            if isinstance(value, bool):
                result[field] = value
            else:
                result[field] = str(value).lower() in ("true", "1", "yes")
        elif expected_type == float:
            try:
                result[field] = float(value)
            except (ValueError, TypeError):
                result[field] = None
        else:
            result[field] = str(value) if value else None
    return result


# ---------------------------------------------------------------------------
# Django View
# ---------------------------------------------------------------------------

@method_decorator(login_required, name="dispatch")
class EmailParserView(View):
    """
    GET  /subscriptions/parse-email/ — renders the email parser UI
    POST /subscriptions/parse-email/ — parses raw email with local LLM

    POST body: { "raw_email": "From: Netflix..." }
    Returns: { "parsed": { ...subscription fields... }, "inference_time": 12.3 }
    """

    def get(self, request, *args, **kwargs):
        return render(request, "subscriptions/parse_email.html")

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        raw_email = body.get("raw_email", "")

        if not raw_email or not raw_email.strip():
            return JsonResponse(
                {"error": "Email content cannot be empty."}, status=400
            )

        cleaned = clean_text(raw_email, max_chars=2000)

        try:
            parsed_raw, inference_time = run_local_model(cleaned)
        except json.JSONDecodeError:
            logger.error("Local model returned non-JSON output")
            return JsonResponse(
                {"error": "The model could not extract structured data from this email. Try a different email."},
                status=422,
            )
        except Exception as exc:
            logger.exception("Local model inference failed: %s", exc)
            return JsonResponse(
                {"error": f"Model inference failed: {str(exc)}"},
                status=503,
            )

        normalized = normalize_parsed_data(parsed_raw)

        safe_result = {}
        for key, value in normalized.items():
            if isinstance(value, str):
                safe_result[key] = escape(value)
            else:
                safe_result[key] = value

        return JsonResponse({
            "parsed": safe_result,
            "inference_time": round(inference_time, 2),
            "model": MODEL_NAME,
        }, status=200)
