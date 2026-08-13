"""Optional LLM-generated editorial context for Mr. Informer briefings.

Adds a short, grounded "Why this matters" paragraph on top of the honest
RSS-snippet summary built in news_workflow.build_article_content, using the
Gemini API (Google AI Studio's free tier) via plain REST — no extra pip
dependency, consistent with the rest of this stdlib-only pipeline.

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

# gemini-3.5-flash-lite: Google's cost/speed-optimized tier for "simple
# data processing" tasks like this one. Verified accessible with this
# project's API key (gemini-2.5-flash / gemini-2.5-flash-lite are not —
# both 404 as "no longer available to new users").
MODEL = "gemini-3.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# Some models echo a "**Why this matters:**"-style heading back at the start
# of their answer despite the "no headers, no markdown" instruction — the
# template already renders its own <h3>Why this matters</h3> above this
# text, so a leading duplicate (with literal, unescaped-looking asterisks)
# would show up on the live page. Strip it, plus any stray markdown bold.
_LEADING_HEADING_RE = re.compile(
    r'^\**\s*why this matters\s*:?\s*\**\s*', re.IGNORECASE
)


def _clean_output(text):
    text = _LEADING_HEADING_RE.sub('', text).strip()
    text = text.replace('**', '')
    return text.strip()


SYSTEM_PROMPT = (
    "You write a short \"Why this matters\" paragraph for Mr. Informer, a "
    "tech news briefing site. You are given only a headline, a short excerpt "
    "from the original report, and the source outlet's name — that is the "
    "entire set of facts available to you. Ground everything strictly in "
    "that material.\n\n"
    "Rules:\n"
    "- Do not invent facts, statistics, quotes, names, or details that are "
    "not present in the provided headline/excerpt.\n"
    "- You may add genuine context: why this kind of development matters, "
    "how it fits into a broader trend, what a reader should take away — "
    "phrase it as general framing, not as new factual claims about this "
    "specific story.\n"
    "- 2-4 sentences. Plain prose, no headers, no bullet points, no markdown.\n"
    "- If the excerpt is too thin to say anything useful without inventing "
    "facts, respond with exactly: SKIP"
)


def generate_editorial_context(title, snippet, source_name):
    """Return a short grounded context paragraph, or None if the LLM is
    unavailable, declines, or the call fails for any reason."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    user_prompt = f"Headline: {title}\nSource: {source_name}\nExcerpt: {snippet}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        # maxOutputTokens has to cover this model's internal "thinking" tokens
        # too, not just the visible answer — a tight budget here truncates
        # the response mid-sentence before any text is returned.
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
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
        # Cut off mid-thought (thinking tokens + answer exceeded the budget)
        # — never publish a truncated paragraph.
        print("[LLM Enrichment] Skipped (truncated at max_tokens).")
        return None

    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text or text.upper() == "SKIP":
        return None
    text = _clean_output(text)
    if not text or text.upper() == "SKIP":
        return None
    return text
