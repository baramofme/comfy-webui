"""Shared LLM prompt-optimization engine (reusable module).

This is the single optimization utility that both integration points call:
  * comfy-webui ``video_gen`` ``process_inputs`` (t_5ddd00c1) — rewrites the prompt
    before it reaches the ComfyUI workflow.
  * the Dock composer (t_8f079531) — rewrites the prompt before submission.

Engine ported verbatim from ComfyUI-MiniMaxH3-Easy's prompt-optimization engine
(the HTTP call, URL normalisation, response parsing, thinking-tag strip,
code-fence strip, sha256 idempotency cache). The engine is model-agnostic; only
the system-prompt content is opinionated. Unlike the standalone ComfyUI node in
``ltx_prompt_optimizer.py`` this module is *not* a node — it is plain importable
functions so any pipeline can call it directly.

The system prompt is H3-specific: it keeps MiniMax H3's ``<Picture N>`` picture-
reference tag and ``<d>...</d>`` spoken-dialogue convention intact (see
``media_ref_prompt.py`` / ``dialog_prompt.py`` in comfy-webui for how those tags
are produced). The optimizer must never renumber or invent content for those
tokens.

Failure behaviour matches the source node: on any HTTP error or timeout the
ORIGINAL prompt is returned unchanged and a warning is logged — never breaking
the submit path.

SECURITY NOTE (inherited gap): the API key is stored in plaintext. It lives in
the module default constant / in whatever config the caller passes, in clear
text — no encryption, no secret store. This is inherited from the upstream repo,
which also stores ``prompt_optimizer_api_key`` as plain text (see t_4a4dc830
spec: ``prompt_optimizer_api_key_stored_plain_text: true``). Documented, not
fixed here. Treat any config that carries ``api_key`` as a secret at rest.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import urllib.parse

import requests

logger = logging.getLogger("prompt_optimizer")


# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_SECONDS = 600.0
DEFAULT_MAX_OUTPUT_TOKENS = 50000

API_FORMATS = ("openai", "responses", "gemini", "ollama")

# The local LLM endpoint comfy-webui / OpenHiggsfield talk to (a local vLLM
# serving qwen3.8-flash-next). No auth required in the local deployment, so the
# api_key default is empty — a caller with a gated endpoint supplies its own.
DEFAULT_API_URL = "http://localhost:8081/v1"
DEFAULT_MODEL = "qwen3.8-flash-next"
DEFAULT_API_FORMAT = "openai"
# Plaintext key, inherited from upstream. Empty by default because the local
# endpoint does not require one. See the SECURITY NOTE in the module docstring.
DEFAULT_API_KEY = ""


# H3-specific system prompt. The ``<Picture N>`` / ``<d>`` convention is MiniMax
# H3's own vocabulary: ``<Picture N>`` binds the Nth reference image by ordinal,
# and ``<d>...</d>`` marks a spoken-dialogue span that also drives H3's audio
# stream. The optimizer MUST preserve both.
DEFAULT_SYSTEM_PROMPT = """\
You are a prompt optimization assistant for MiniMax H3 text-to-audio-video (T2VA) generation.

Given a user's raw prompt, rewrite it so that it:
1. Adds quality cues: cinematic lighting, natural motion, coherent composition, sharp details.
2. Preserves every creative intent the user expressed — do NOT add unrelated subjects, do NOT remove user elements.
3. Restructures for token efficiency: keep under ~300 words. Prefer concrete visual nouns over abstract adjectives.
4. Ensures temporal coherence: mention camera movement, pacing, or motion explicitly if the user implies them.
5. Output ONLY the rewritten prompt text. No preamble, no explanation, no code fences.

H3 tag rules (these are load-bearing — break them and the generation is wrong):
- ``<Picture N>`` tags reference attached images by ordinal (N is the position of the
  reference image in the list, 1-based). Keep every ``<Picture N>`` tag EXACTLY as it
  appears — never renumber them, never add new ones, never drop them.
- ``<d>`` ... ``</d>`` spans mark SPOKEN DIALOGUE that drives the audio stream. Keep
  their contents verbatim — never translate, never paraphrase, never restructure them.
- Never hallucinate details about attached media unless the user explicitly described
  that media's content in text. If the prompt references an image/video/audio asset by
  tag or name, keep that reference intact.

Rewrite rules:
- Keep the user's language (do NOT translate unless asked).
- Prefer present-tense, active-voice descriptions.
- Do not invent scene directions the user didn't request.
"""


# ─── URL normalization (ported from source) ──────────────────────────────────

_KNOWN_ENDPOINT_SUFFIXES = (
    "/v1/chat/completions",
    "/chat/completions",
    "/v1/responses",
    "/responses",
)

_GEMINI_ENDPOINT_RE = re.compile(
    r"/(v1beta|v1)/models/[^/?:#]+?:(generateContent|streamGenerateContent)$",
    flags=re.I,
)


def _normalize_base_url(api_url: str) -> str:
    base = str(api_url or "").strip()
    if not base:
        raise ValueError("API URL is required")
    if not re.match(r"^https?://", base, flags=re.I):
        base = "https://" + base
    parsed = urllib.parse.urlsplit(base)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.query, "")
    )


def _endpoint_kind(value: str) -> str:
    lower = urllib.parse.urlsplit(str(value or "")).path.rstrip("/").lower()
    if lower.endswith("/chat/completions"):
        return "chat"
    if lower.endswith("/responses"):
        return "responses"
    if _GEMINI_ENDPOINT_RE.search(lower):
        return "gemini"
    return ""


def _strip_endpoint(base: str) -> str:
    lower = base.lower()
    for suffix in _KNOWN_ENDPOINT_SUFFIXES:
        if lower.endswith(suffix):
            return base[: len(base) - len(suffix)].rstrip("/")
    match = _GEMINI_ENDPOINT_RE.search(lower)
    if match and lower.endswith(match.group(0)):
        return base[: match.start()].rstrip("/")
    return base


def _normalize_gemini_model_id(model: str) -> str:
    raw = urllib.parse.unquote(str(model or "").strip())
    if not raw:
        raise ValueError("Model is required")
    if "://" in raw:
        raw = urllib.parse.urlsplit(raw).path
    raw = raw.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    match = re.search(r"(?:^|/)models/([^/:]+)(?::[A-Za-z]+)?$", raw, flags=re.I)
    if match:
        raw = match.group(1)
    else:
        if raw.lower().startswith("models/"):
            raw = raw[7:]
        raw = raw.rsplit("/", 1)[-1]
        raw = re.sub(r":(?:generateContent|streamGenerateContent)$", "", raw, flags=re.I)
    raw = raw.strip()
    if not raw:
        raise ValueError("Model is required")
    return raw


def _gemini_url_with_query(url: str, query: str) -> str:
    pairs = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(query, keep_blank_values=True)
        if key.lower() != "alt"
    ]
    encoded = urllib.parse.urlencode(pairs)
    return url + (f"?{encoded}" if encoded else "")


def _normalize_gemini_url(api_url: str, model: str) -> str:
    base = _normalize_base_url(api_url)
    parsed = urllib.parse.urlsplit(base)
    clean = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )
    lower = clean.lower()
    model_id = urllib.parse.quote(_normalize_gemini_model_id(model), safe=".-_")

    endpoint_match = _GEMINI_ENDPOINT_RE.search(lower)
    if endpoint_match and lower.endswith(endpoint_match.group(0)):
        version = endpoint_match.group(1)
        clean = clean[: endpoint_match.start()].rstrip("/")
        url = f"{clean}/{version}/models/{model_id}:generateContent"
        return _gemini_url_with_query(url, parsed.query)

    if lower.endswith("/v1beta/models") or lower.endswith("/v1/models"):
        url = f"{clean}/{model_id}:generateContent"
    elif lower.endswith("/v1beta") or lower.endswith("/v1"):
        url = f"{clean}/models/{model_id}:generateContent"
    elif lower.endswith("/models"):
        url = f"{clean}/{model_id}:generateContent"
    else:
        url = f"{clean}/v1beta/models/{model_id}:generateContent"
    return _gemini_url_with_query(url, parsed.query)


def _normalize_url(api_url: str, api_format: str, model: str) -> str:
    if api_format == "gemini":
        return _normalize_gemini_url(api_url, model)
    base = _normalize_base_url(api_url)
    parsed = urllib.parse.urlsplit(base)
    clean = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )
    endpoint = "/v1/responses" if api_format == "responses" else "/v1/chat/completions"
    base_kind = _endpoint_kind(clean)
    endpoint_kind = _endpoint_kind(endpoint)
    if base_kind == endpoint_kind and base_kind != "":
        return clean + (f"?{parsed.query}" if parsed.query else "")
    base = _strip_endpoint(clean)
    if base.lower().endswith("/v1") and endpoint.lower().startswith("/v1/"):
        endpoint = endpoint[3:]
    return base + endpoint + (f"?{parsed.query}" if parsed.query else "")


def _normalize_ollama_unload_url(api_url: str) -> str:
    base = _normalize_base_url(api_url)
    parsed = urllib.parse.urlsplit(base)
    clean = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )
    clean = _strip_endpoint(clean)
    if clean.lower().endswith("/v1"):
        clean = clean[:-3].rstrip("/")
    if clean.lower().endswith("/api/generate"):
        clean = clean[: -len("/api/generate")].rstrip("/")
    return clean + "/api/generate" + (f"?{parsed.query}" if parsed.query else "")


# ─── Response parsing helpers (ported) ───────────────────────────────────────


def _part_is_thought(part) -> bool:
    if not isinstance(part, dict):
        return False

    def flag(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    if flag(part.get("thought")) or flag(part.get("is_thought")):
        return True
    part_type = str(part.get("type") or "").strip().lower()
    if part_type in {"reasoning", "thinking", "thought", "summary_text"}:
        return True
    return flag(part.get("reasoning")) or flag(part.get("thinking"))


def _responses_text(data) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    output = data.get("output")
    chunks: list[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").lower()
            if item_type in {"reasoning", "thinking", "thought"}:
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = str(part.get("type") or "").lower()
                if part_type in {"reasoning", "thinking", "thought", "summary_text"}:
                    continue
                value = part.get("text")
                if isinstance(value, str):
                    chunks.append(value)
                elif isinstance(value, dict) and isinstance(value.get("value"), str):
                    chunks.append(value["value"])
    if chunks:
        return "".join(chunks)
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content", "") if isinstance(message, dict) else ""
        if isinstance(content, str):
            return content
    return ""


def _chat_content_text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for part in content:
        if not isinstance(part, dict) or _part_is_thought(part):
            continue
        value = part.get("text")
        if isinstance(value, str):
            chunks.append(value)
    return "".join(chunks)


def _strip_thoughts(text: str) -> str:
    """Remove inline chain-of-thought blocks emitted by reasoning-capable models."""
    text = re.sub(r"<\|think\|>.*?<\|/think\|>", "", text, flags=re.S)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return text.strip()


# ─── Core HTTP call (ported) ─────────────────────────────────────────────────


def optimizer_http_json(
    api_url: str,
    api_key: str,
    model: str,
    api_format: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> str:
    """Call an LLM API and return the optimized prompt text.

    Raises ``RuntimeError`` on any HTTP/parse failure — the public wrapper turns
    that into the original-prompt fallback with a warning log.
    """
    url = _normalize_url(api_url, api_format, model)
    api_key = str(api_key or "").strip()
    output_budget = max(1, int(max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS))

    if api_format == "gemini":
        if not api_key:
            raise ValueError("API key is required for Gemini native")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-goog-api-key": api_key,
        }
        combined = (
            system_prompt
            + "\n\n=== USER PROMPT TO OPTIMIZE ===\n"
            + user_prompt
            + "\n\nFollow the instructions above. Return only the final rewritten prompt."
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": combined}]}],
            "generationConfig": {"temperature": 0.35, "maxOutputTokens": output_budget},
        }
    elif api_format == "responses":
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "instructions": system_prompt,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": user_prompt}]}],
            "store": False,
            "stream": False,
            "temperature": 0.35,
            "max_output_tokens": output_budget,
        }
    else:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "temperature": 0.35,
            "max_tokens": output_budget,
        }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=max(1.0, float(timeout_seconds))
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else "unknown"
        detail = resp.text if resp is not None else str(exc)
        raise RuntimeError(f"API error ({status}): {detail[:1000]}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("API returned invalid JSON") from exc
    finally:
        if api_format == "ollama":
            try:
                requests.post(
                    _normalize_ollama_unload_url(api_url),
                    json={"model": model, "keep_alive": 0},
                    timeout=5.0,
                )
            except Exception:
                pass

    # Parse response based on format
    if api_format == "gemini":
        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError("Gemini returned no candidates")
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(
            str(p.get("text", ""))
            for p in parts
            if isinstance(p, dict) and not _part_is_thought(p) and p.get("text") is not None
        )
        if not text.strip():
            raise RuntimeError("Gemini returned no text")
    elif api_format == "responses":
        text = _responses_text(data)
    else:
        message = (data.get("choices") or [{}])[0].get("message", {})
        text = _chat_content_text(message.get("content", ""))

    text = _strip_thoughts(text)
    # Strip code fences
    text = re.sub(r"^```(?:text)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text).strip()
    if not text:
        raise RuntimeError("API returned empty response")
    return text


# ─── Idempotency cache ───────────────────────────────────────────────────────

_cache_lock = threading.Lock()
_cache: dict[str, str] = {}  # hash -> optimized text


def _sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _cache_key(prompt: str, api_url: str, api_key: str, model: str, api_format: str, system_prompt: str) -> str:
    """Composite hash for cache identity (same scheme the source hashed)."""
    parts = json.dumps(
        {"p": _sha256(prompt), "u": api_url, "m": model, "f": api_format, "s": _sha256(system_prompt)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(parts)


def cache_clear() -> int:
    """Drop all cached rewrites. Returns the number of entries cleared."""
    with _cache_lock:
        n = len(_cache)
        _cache.clear()
        return n


def cache_size() -> int:
    with _cache_lock:
        return len(_cache)


# ─── Public entry point ──────────────────────────────────────────────────────


def optimize_prompt(
    prompt: str,
    *,
    enabled: bool = True,
    api_url: str = DEFAULT_API_URL,
    api_key: str = DEFAULT_API_KEY,
    model: str = DEFAULT_MODEL,
    api_format: str = DEFAULT_API_FORMAT,
    system_prompt: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> str:
    """Rewrite ``prompt`` via the configured LLM; fall back to the original on any
    failure. Disabled or an empty prompt passes straight through untouched.

    This mirrors the source node's behaviour exactly: a failure never breaks the
    caller's pipeline — the ORIGINAL prompt is returned unchanged and a warning is
    logged. Use :func:`optimize_prompt_result` when you need the richer
    ``changed``/``cached``/``error`` flags (e.g. for a composer warning indicator).
    """
    original = str(prompt or "")
    if not enabled or not original.strip():
        return original

    if system_prompt is None or not system_prompt.strip():
        system_prompt = DEFAULT_SYSTEM_PROMPT

    key = _cache_key(original, api_url, api_key, model, api_format, system_prompt)
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    try:
        optimized = optimizer_http_json(
            api_url=api_url,
            api_key=api_key,
            model=model,
            api_format=api_format,
            system_prompt=system_prompt,
            user_prompt=original,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — every failure becomes the fallback
        logger.warning("[prompt_optimizer] optimization failed, passing through original: %s", exc)
        return original

    with _cache_lock:
        _cache[key] = optimized
    return optimized


def optimize_prompt_result(
    prompt: str,
    *,
    enabled: bool = True,
    api_url: str = DEFAULT_API_URL,
    api_key: str = DEFAULT_API_KEY,
    model: str = DEFAULT_MODEL,
    api_format: str = DEFAULT_API_FORMAT,
    system_prompt: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> dict:
    """Same optimisation, but returns a result dict for UI feedback.

    ``text``    — the rewrite on success, the original on failure.
    ``changed``  — True when the text differs from the input because the LLM rewrote it.
    ``cached``   — True when ``text`` came from the idempotency cache (no HTTP call).
    ``error``    — set only when optimisation failed; the reason logged for the warning.
    """
    original = str(prompt or "")
    if not enabled or not original.strip():
        return {"text": original, "changed": False, "cached": False}

    if system_prompt is None or not system_prompt.strip():
        system_prompt = DEFAULT_SYSTEM_PROMPT

    key = _cache_key(original, api_url, api_key, model, api_format, system_prompt)
    with _cache_lock:
        hit = _cache.get(key)
    if hit is not None:
        return {"text": hit, "changed": True, "cached": True}

    try:
        optimized = optimizer_http_json(
            api_url=api_url,
            api_key=api_key,
            model=model,
            api_format=api_format,
            system_prompt=system_prompt,
            user_prompt=original,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — every failure becomes the fallback
        message = str(exc)
        logger.warning("[prompt_optimizer] optimization failed, passing through original: %s", message)
        return {"text": original, "changed": False, "cached": False, "error": message}

    with _cache_lock:
        _cache[key] = optimized
    return {"text": optimized, "changed": True, "cached": False}
