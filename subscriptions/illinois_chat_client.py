"""
Illinois Chat HTTP client — **chat.illinois.edu** ``/chat`` API (course Colab pattern).

Secrets (same idea as Colab ``userdata`` / notebook):

- ``ILLINOIS_API_KEY`` — from https://chat.illinois.edu → Settings → API Keys (**required**)
- ``ILLINOIS_API_URL`` — default ``https://chat.illinois.edu/api/chat-api/chat`` if unset
- ``ILLINOIS_PROJECT_NAME`` — sent as ``course_name``; default ``Subflo`` if unset

Optional: ``OPENAI_API_KEY_FOR_UIUC`` for BYOK OpenAI-backed models per
https://docs.uiuc.chat/api/endpoints

Requests always use ``stream: true`` and ``retrieval_only: false`` (Request Builder
defaults). Model id: ``ILLINOIS_MODEL`` or ``ILLINOIS_CHAT_MODEL``, else default
``qwen3:32b`` (Qwen 3 on Illinois Chat; match the Request Builder model dropdown).

Legacy fallbacks (still read if present): ``ILLINOIS_CHAT_API_KEY``,
``ILLINOIS_CHAT_URL``, ``ILLINOIS_CHAT_COURSE_NAME``, ``UIUC_CHAT_COURSE_NAME``.
"""

from __future__ import annotations

import json
import os
import requests

DOCS_ENDPOINTS = "https://docs.uiuc.chat/api/endpoints"
DEFAULT_CHAT_URL = "https://chat.illinois.edu/api/chat-api/chat"
DEFAULT_MODEL = "gpt-oss:20b"
DEFAULT_COURSE_NAME = "Subflo"


def _normalize_env_string(value: str | None) -> str:
    """Strip whitespace, UTF-8 BOM, and a single pair of surrounding quotes (common .env mistakes)."""
    s = (value or "").strip()
    if s.startswith("\ufeff"):
        s = s[1:].strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _choice_dicts(chunk: dict) -> list[dict]:
    """Normalize ``choices`` to a list of dicts (Illinois / OpenAI-like streams vary)."""
    ch = chunk.get("choices")
    if isinstance(ch, list):
        return [x for x in ch if isinstance(x, dict)]
    if isinstance(ch, dict):
        return [x for x in ch.values() if isinstance(x, dict)]
    return []


def _text_from_choice(c: dict) -> str:
    d = c.get("delta")
    if isinstance(d, dict):
        for k in ("content", "reasoning_content"):
            v = d.get(k)
            if isinstance(v, str) and v:
                return v
    for k in ("text", "content"):
        v = c.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _text_from_chunk(chunk: dict) -> str:
    parts = [_text_from_choice(c) for c in _choice_dicts(chunk)]
    if any(parts):
        return "".join(parts)
    d = chunk.get("delta")
    if isinstance(d, dict):
        v = d.get("content")
        if isinstance(v, str):
            return v
    for k in ("content", "text", "message"):
        v = chunk.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _accumulate_sse_stream(response: requests.Response) -> str:
    """Accumulate streamed SSE chunks into assistant text (Colab ``_call_illinois`` pattern)."""
    full_text = ""
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8", errors="replace")
        if line.startswith("data:"):
            line = line[5:].lstrip()
        if line in ("[DONE]", ""):
            continue
        for part in line.replace("\r\n", "\n").split("\n"):
            part = part.strip()
            if not part or part == "[DONE]":
                continue
            try:
                chunk = json.loads(part)
            except json.JSONDecodeError:
                # Illinois GPT-OSS streams plain-text lines (and <think>… blocks), not only SSE JSON.
                low = part.lower()
                if "redacted_thinking" in low or part.strip().startswith("<think"):
                    continue
                full_text += part
                continue
            if isinstance(chunk, dict):
                full_text += _text_from_chunk(chunk)
    return full_text.strip()


def call_illinois_chat_messages(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    timeout: int = 120,
) -> str:
    """
    Streaming chat completion; returns assistant text (raw string).
    Raises RuntimeError on HTTP errors or empty streamed content.
    """
    api_key = _normalize_env_string(
        os.getenv("ILLINOIS_API_KEY") or os.getenv("ILLINOIS_CHAT_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "ILLINOIS_API_KEY is not set. Add it to .env (from chat.illinois.edu → Settings → API Keys)."
        )

    url = (
        _normalize_env_string(os.getenv("ILLINOIS_API_URL") or os.getenv("ILLINOIS_CHAT_URL"))
        or DEFAULT_CHAT_URL
    )
    model = (
        _normalize_env_string(os.getenv("ILLINOIS_MODEL") or os.getenv("ILLINOIS_CHAT_MODEL"))
        or DEFAULT_MODEL
    )
    course_name = _normalize_env_string(
        os.getenv("ILLINOIS_PROJECT_NAME")
        or os.getenv("ILLINOIS_CHAT_COURSE_NAME")
        or os.getenv("UIUC_CHAT_COURSE_NAME")
    ) or DEFAULT_COURSE_NAME

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
        "course_name": course_name,
        "stream": True,
        "temperature": temperature,
        "retrieval_only": False,
    }
    openai_key = _normalize_env_string(os.getenv("OPENAI_API_KEY_FOR_UIUC"))
    if openai_key:
        payload["openai_key"] = openai_key

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "SubFlo/1.0 (Illinois Chat API client)",
    }
    if "chat.illinois.edu" in url.lower():
        headers["Origin"] = "https://chat.illinois.edu"
        headers["Referer"] = "https://chat.illinois.edu/"
    if os.getenv("ILLINOIS_CHAT_SEND_BEARER", "").strip().lower() in ("1", "true", "yes"):
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
            stream=True,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Illinois Chat request failed: {e}") from e

    if r.status_code >= 400:
        body = (r.text or "")[:2000]
        hint = ""
        if r.status_code == 403:
            hint = (
                " If invalid API key: copy ILLINOIS_API_KEY from chat.illinois.edu → Settings → API Keys; "
                "set ILLINOIS_PROJECT_NAME to the Request Builder `course_name` (e.g. Subflo). "
                f"See {DOCS_ENDPOINTS}. For OpenAI-backed models set OPENAI_API_KEY_FOR_UIUC."
            )
        try:
            r.close()
        except Exception:
            pass
        raise RuntimeError(f"Illinois Chat HTTP {r.status_code}: {body}{hint}")

    try:
        text = _accumulate_sse_stream(r)
    finally:
        try:
            r.close()
        except Exception:
            pass

    if not text:
        raise RuntimeError("Illinois Chat streaming response contained no assistant text")

    return text
