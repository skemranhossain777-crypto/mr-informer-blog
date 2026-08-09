"""
One-time migration: rewrite every article currently stored in articles.json
through the new honest content template (news_workflow.build_article_content),
replacing the old fabricated-stats/fake-infographic bodies and the misleading
"Exclusive Intel:" title prefix.

These older posts were never stored with a source URL, so they can't get a
real outbound attribution link retroactively — the migration says so openly
instead of inventing one. Also resets the old random "claps"/"views" numbers
(fake social proof) to honest zero/"New", and best-effort repairs the mojibake
character seen in a few old titles.

Safe to run more than once; it's idempotent given the same input.
"""
import os
import re
import json

import news_workflow as nw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, "articles.json")
js_path = os.path.join(BASE_DIR, "articles.js")

QUOTE_RE = re.compile(r'<div class="article-quote-box">\s*<p>"(.*?)"</p>', re.DOTALL)
TITLE_PREFIX_RE = re.compile(r'^(exclusive intel|mr\. informer briefing):\s*', re.IGNORECASE)


def repair_mojibake_text(text):
    """Best-effort cleanup for the stray U+FFFD replacement character seen in
    a few old titles (irreversible data loss at the source — this just makes
    it readable instead of showing a broken glyph)."""
    if not text:
        return text
    return text.replace("�", "'")


def rewrite_legacy_article(art):
    """Rewrite one article dict (in place) from the old fabricated-stats
    template to the honest one. Shared by the local articles.json migration
    below and migrate_supabase_articles.py for the live database."""
    raw_title = TITLE_PREFIX_RE.sub("", art.get("title", ""))
    raw_title = repair_mojibake_text(raw_title)
    art["title"] = f"Mr. Informer Briefing: {raw_title}"

    # Recover the real quoted snippet from the old content body if present,
    # otherwise fall back to the stored summary.
    match = QUOTE_RE.search(art.get("content", ""))
    snippet = match.group(1) if match else art.get("summary", "").split(". ")[0]
    snippet = repair_mojibake_text(snippet)

    source_name = art.get("sourceName") or "the original publisher (not recorded for this earlier post)"
    source_url = art.get("sourceUrl") or None

    art["content"] = nw.build_article_content(raw_title, snippet, source_name, source_url)
    art["summary"] = f"Mr. Informer briefing on {raw_title}. {snippet[:120]}"
    art.setdefault("slug", art["id"])
    art["sourceName"] = art.get("sourceName") or ""
    art["sourceUrl"] = art.get("sourceUrl") or ""

    # The old fake engagement numbers were randomly generated, not real.
    art["claps"] = 0
    art["views"] = "New"

    art["tags"] = [t for t in art.get("tags", []) if t != "Live Scoop"]
    return art


def migrate():
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        rewrite_legacy_article(art)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    with open(js_path, "w", encoding="utf-8") as f:
        f.write("const ARTICLES_DATA = " + json.dumps(articles, indent=2, ensure_ascii=False) + ";\n")

    print(f"Migrated {len(articles)} articles to the honest content template.")
    print("If these were already synced to Supabase, re-run sync_to_supabase.py to push the corrected content.")


if __name__ == "__main__":
    migrate()
