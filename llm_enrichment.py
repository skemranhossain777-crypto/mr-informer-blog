"""Optional LLM-generated editorial context for Mr. Informer briefings.

Adds a short, grounded "Why this matters" paragraph on top of the honest
RSS-snippet summary built in news_workflow.build_article_content. This is
strictly additive: it requires ANTHROPIC_API_KEY and the `anthropic`
package, and silently no-ops (falls back to the template-only article, same
as before this file existed) if either is missing or the call fails for any
reason — the RSS pipeline must never fail or block publishing on this.

The model is instructed to ground everything in the provided headline/
excerpt only and never invent facts, stats, quotes, or names — consistent
with this codebase's non-negotiable "no fabricated content" rule (see
CLAUDE.md).
"""
import os

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

MODEL = "claude-opus-5"

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
    "- Do not include internal or system XML tags in your response.\n"
    "- If the excerpt is too thin to say anything useful without inventing "
    "facts, respond with exactly: SKIP"
)


def generate_editorial_context(title, snippet, source_name):
    """Return a short grounded context paragraph, or None if the LLM is
    unavailable, declines, or the call fails for any reason."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not _ANTHROPIC_AVAILABLE or not api_key:
        return None

    user_prompt = f"Headline: {title}\nSource: {source_name}\nExcerpt: {snippet}"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        print(f"[LLM Enrichment] Skipped (API error): {e}")
        return None

    if response.stop_reason == "refusal":
        print("[LLM Enrichment] Skipped (safety refusal).")
        return None

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text or text.upper() == "SKIP":
        return None
    return text
