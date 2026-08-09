import os
import sys
import json
import urllib.request

# Import base news workflow generator
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import news_workflow

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

def fetch_supabase_articles():
    """Retrieve existing articles from Supabase to prevent duplicates."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase credentials missing. Operating in local mode.")
        return []

    url = f"{SUPABASE_URL}/rest/v1/articles?select=id,title,image"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"⚠️ Could not fetch existing Supabase articles: {e}")
        return []

def insert_supabase_article(article):
    """Insert a new article directly into Supabase via REST API."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase credentials missing. Skipping cloud insert.")
        return False

    url = f"{SUPABASE_URL}/rest/v1/articles"

    # Map fields to Supabase column names
    payload = {
        "id": article["id"],
        "slug": article.get("slug", article["id"]),
        "title": article["title"],
        "category": article["category"],
        "read_time": article["readTime"],
        "date": article["date"],
        "author": article["author"],
        "featured": article.get("featured", False),
        "image": article["image"],
        "tags": article.get("tags", []),
        "summary": article["summary"],
        "source_name": article.get("sourceName"),
        "source_url": article.get("sourceUrl"),
        "claps": article.get("claps", 0),
        "views": article.get("views", "New"),
        "content": article["content"],
        "comments": article.get("comments", [])
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status in (200, 201):
                print(f"☁️ [SUPABASE SUCCESS] Post '{article['title']}' inserted into Cloud PostgreSQL!")
                return True
    except Exception as e:
        print(f"❌ Failed to insert article to Supabase: {e}")
        return False

def run_cloud_ingestion():
    """Run one automated news sweep and, if a genuinely new story is found,
    publish it to both Supabase and the local articles.json/articles.js
    fallback. Returns None (publishing nothing) on a quiet cycle — there is
    no fabricated-headline fallback here anymore."""
    print("=" * 70)
    print("🚀 MR. INFORMER CLOUD SUPABASE INGESTION WORKFLOW")
    print(f"📡 Querying {len(news_workflow.RSS_FEEDS)} global RSS sources...")
    print("=" * 70)

    cloud_articles = fetch_supabase_articles()
    local_articles = news_workflow.load_existing_articles()
    all_articles = cloud_articles + local_articles

    selected_item = news_workflow.pick_next_story(all_articles)
    if not selected_item:
        print("⚠️ No new story to publish this cycle.")
        return None

    article = news_workflow.generate_mr_informer_article(selected_item, all_articles)

    insert_supabase_article(article)

    local_articles.insert(0, article)
    news_workflow.save_articles(local_articles)

    print(f"✅ Auto-Published Briefing: '{article['title']}' [{article['category']}]")
    return article

if __name__ == "__main__":
    run_cloud_ingestion()
