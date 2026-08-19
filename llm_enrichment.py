"""LLM-generated editorial sections for Mr. Informer briefings.

Produces three grounded sections on top of the honest RSS-snippet summary:
  1. "Why this matters" — 2-4 sentence framing paragraph
  2. "Technical context" — 2-4 sentence deeper explanation of the underlying technology or trend
  3. "Key takeaways" — 3-5 bullet points summarizing the most important points

Uses the Gemini API (Google AI Studio's free tier) via plain REST — no extra
pip dependency, consistent with the rest of this stdlib-only pipeline.

This is strictly additive: it requires GEMINI_API_KEY, and silently no-ops
(falls back to the template-only article, same as before this file existed)
if the key is missing or the call fails for any reason — the RSS pipeline
must never fail or block publishing on this.
"""
import os
import re
import json
import urllib.request
import urllib.error

MODEL = "gemini-3.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

_LEADING_HEADING_RE = re.compile(
    r'^\**\s*why this matters\s*:?\s*\**\s*', re.IGNORECASE
)


def _clean_output(text):
    text = _LEADING_HEADING_RE.sub('', text).strip()
    text = text.replace('**', '')
    return text.strip()


def _clean_bullets(text):
    """Clean markdown bullets from LLM output into plain text lines."""
    text = text.replace('**', '')
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[-*•]\s*', '', line)
        lines.append(line)
    return '\n'.join(lines)


SYSTEM_PROMPT = (
    "You write editorial analysis for Mr. Informer, a tech news briefing "
    "site. You are given only a headline, a short excerpt from the original "
    "report, and the source outlet's name — that is the entire set of facts "
    "available to you. Ground everything strictly in that material.\n\n"
    "You must produce three clearly separated sections using EXACTLY these "
    "labels on their own lines:\n\n"
    "WHY THIS MATTERS\n"
    "Write 2-4 sentences explaining why this kind of development matters, "
    "how it fits into a broader industry trend, and what a reader should "
    "take away. Phrase general framing as context, not as new factual claims.\n\n"
    "TECHNICAL CONTEXT\n"
    "Write 2-4 sentences explaining the underlying technology, protocol, or "
    "concept at a level an interested non-specialist can follow. Use the "
    "headline and excerpt as your only factual basis.\n\n"
    "KEY TAKEAWAYS\n"
    "Write exactly 4-5 short bullet points (one sentence each) summarizing "
    "the most important points a reader should remember.\n\n"
    "Rules:\n"
    "- Do not invent facts, statistics, quotes, names, or details that are "
    "not present in the provided headline/excerpt.\n"
    "- Plain prose for the first two sections. The third section uses bullet "
    "points (one per line, no numbering, no markdown bold).\n"
    "- If the excerpt is too thin to say anything useful without inventing "
    "facts, respond with exactly: SKIP"
)


def _call_gemini(user_prompt, api_key):
    """Make a single Gemini API call and return extracted text, or None."""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.3},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[LLM Enrichment] Skipped (API error): {e}")
        return None
    except Exception as e:
        print(f"[LLM Enrichment] Skipped (unexpected error): {e}")
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        block_reason = (data.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            print(f"[LLM Enrichment] Skipped (blocked: {block_reason}).")
        return None

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason == "SAFETY":
        print("[LLM Enrichment] Skipped (safety finish reason).")
        return None
    if finish_reason == "MAX_TOKENS":
        print("[LLM Enrichment] Skipped (truncated at max_tokens).")
        return None

    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    return text if text else None


def _parse_sections(raw_text):
    """Parse the three labeled sections from LLM output into a dict."""
    if not raw_text or raw_text.upper().strip() == "SKIP":
        return None

    sections = {"why_this_matters": None, "technical_context": None, "key_takeaways": None}

    # Try labeled parsing first
    patterns = [
        (r"WHY THIS MATTERS\s*\n(.*?)(?=\nTECHNICAL CONTEXT|\Z)", "why_this_matters"),
        (r"TECHNICAL CONTEXT\s*\n(.*?)(?=\nKEY TAKEAWAYS|\Z)", "technical_context"),
        (r"KEY TAKEAWAYS\s*\n(.*?)(?=\Z)", "key_takeaways"),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            if val:
                sections[key] = val

    # If labeled parsing got nothing, fall back to treating entire text as
    # a single "why this matters" paragraph (backward compat with short outputs)
    if not any(sections.values()):
        cleaned = _clean_output(raw_text)
        if cleaned:
            sections["why_this_matters"] = cleaned

    if not any(sections.values()):
        return None
    return sections


def generate_editorial_sections(title, snippet, source_name):
    """Return a dict with keys why_this_matters, technical_context,
    key_takeaways (each a string or None), or None if the LLM is
    unavailable, declines, or the call fails."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    user_prompt = f"Headline: {title}\nSource: {source_name}\nExcerpt: {snippet}"
    raw = _call_gemini(user_prompt, api_key)
    if not raw:
        return None

    sections = _parse_sections(raw)
    if sections:
        if sections.get("key_takeaways"):
            sections["key_takeaways"] = _clean_bullets(sections["key_takeaways"])
        print("[LLM Enrichment] Generated editorial sections successfully.")
    return sections


# Backward-compatible wrapper: returns just the "why this matters" paragraph
def generate_editorial_context(title, snippet, source_name):
    """Return a single grounded context paragraph, or None. Kept for backward
    compatibility with code that calls the old function name."""
    sections = generate_editorial_sections(title, snippet, source_name)
    if sections:
        return sections.get("why_this_matters")
    return None
