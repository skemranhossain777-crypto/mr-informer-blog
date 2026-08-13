"""
One-time migration: rewrite every article currently stored in the LIVE
Supabase database through the honest content template, same treatment as
run_regen.py applied to the local articles.json copy.

The old 5-minute cron published straight to Supabase for weeks, so the cloud
table has far more rows than the local articles.json snapshot — this script
is what actually cleans up production data, not just the local files.

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (service role, not anon —
writes go through the REST data API bypassing RLS, same as the ingestion
scripts already do). Safe to re-run; each article is rewritten from its
current stored state, and rewriting twice is a no-op after the first pass.
"""
import os
import re
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

import news_workflow as nw  # noqa: F401 (imported for its .env loading side effect)
from run_regen import rewrite_legacy_article

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def fetch_all(url, key):
    req = urllib.request.Request(
        f"{url}/rest/v1/articles?select=*&order=created_at.desc",
        headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_local_shape(row):
    """Supabase column names -> the shape rewrite_legacy_article() expects."""
    return {
        "id": row.get("id"),
        "slug": row.get("slug") or row.get("id"),
        "title": row.get("title", ""),
        "summary": row.get("summary", ""),
        "content": row.get("content", ""),
        "readTime": row.get("read_time", ""),
        "tags": row.get("tags") or [],
        "sourceName": row.get("source_name") or "",
        "sourceUrl": row.get("source_url") or "",
    }


def _patch_request(url, key, row_id, fields):
    payload = json.dumps(fields).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/rest/v1/articles?id=eq.{urllib.parse.quote(row_id)}",
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        method="PATCH"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status in (200, 204)


def patch_article(url, key, row_id, fields):
    """PATCH one row. If Supabase rejects a column because
    supabase_schema.sql hasn't been run there yet (PGRST204 'column not
    found'), drop that column from the payload and retry — so content/title
    still get fixed now, and slug/source_name/source_url backfill next run
    once the schema migration has been applied."""
    remaining = dict(fields)
    for _ in range(len(fields) + 1):
        try:
            return _patch_request(url, key, row_id, remaining)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            match = re.search(r"Could not find the '(\w+)' column", body)
            if match and match.group(1) in remaining:
                del remaining[match.group(1)]
                continue
            raise
    return False


def migrate():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set (check .env).")
        sys.exit(1)

    rows = fetch_all(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print(f"Fetched {len(rows)} articles from Supabase. Rewriting...")

    success, failed = 0, 0
    for row in rows:
        local_shaped = to_local_shape(row)
        rewrite_legacy_article(local_shaped)

        fields = {
            "title": local_shaped["title"],
            "slug": local_shaped["slug"],
            "summary": local_shaped["summary"],
            "content": local_shaped["content"],
            "read_time": local_shaped["readTime"],
            "tags": local_shaped["tags"],
            "source_name": local_shaped["sourceName"] or None,
            "source_url": local_shaped["sourceUrl"] or None,
            "claps": 0,
            "views": "New",
        }

        try:
            patch_article(SUPABASE_URL, SUPABASE_SERVICE_KEY, row["id"], fields)
            success += 1
        except urllib.error.HTTPError as e:
            print(f"  FAILED '{row.get('title', row.get('id'))[:60]}': HTTP {e.code} {e.read()[:200]}")
            failed += 1
        except Exception as e:
            print(f"  FAILED '{row.get('title', row.get('id'))[:60]}': {e}")
            failed += 1

    print(f"Done. {success} rewritten, {failed} failed out of {len(rows)}.")


if __name__ == "__main__":
    migrate()
