import os
import sys
import json
import urllib.request

# Load environment variables from .env if python-dotenv installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_JSON_PATH = os.path.join(BASE_DIR, "articles.json")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

def sync_all_articles():
    print("=" * 70)
    print("🚀 MR. INFORMER - BULK SUPABASE CLOUD SYNC SCRIPT")
    print("=" * 70)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in your .env file!")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to your .env file.")
        return

    if not os.path.exists(ARTICLES_JSON_PATH):
        print("❌ ERROR: articles.json not found.")
        return

    with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"📦 Found {len(articles)} local articles in articles.json. Preparing cloud upload...")

    url = f"{SUPABASE_URL}/rest/v1/articles"

    success_count = 0
    for article in articles:
        payload = {
            "id": article["id"],
            "title": article["title"],
            "category": article.get("category", "Tech Pulse"),
            "read_time": article.get("readTime", "4 min read"),
            "date": article.get("date", ""),
            "author": article.get("author", {}),
            "featured": article.get("featured", False),
            "image": article.get("image", ""),
            "tags": article.get("tags", []),
            "summary": article.get("summary", ""),
            "claps": article.get("claps", 100),
            "views": article.get("views", "1.2K"),
            "content": article.get("content", ""),
            "comments": article.get("comments", [])
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    print(f"  ✅ Uploaded: '{article['title'][:50]}...'")
                    success_count += 1
        except Exception as e:
            print(f"  ❌ Failed for '{article['title'][:30]}': {e}")

    print("=" * 70)
    print(f"🎉 SYNC COMPLETE: {success_count}/{len(articles)} articles successfully inserted/updated in Supabase!")
    print("=" * 70)

if __name__ == "__main__":
    sync_all_articles()
