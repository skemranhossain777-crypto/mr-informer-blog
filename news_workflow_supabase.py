import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

# Import base news workflow generator
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import news_workflow

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

def fetch_supabase_articles():
    """Retrieve existing article IDs from Supabase to prevent duplicates."""
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
        "title": article["title"],
        "category": article["category"],
        "read_time": article["readTime"],
        "date": article["date"],
        "author": article["author"],
        "featured": article.get("featured", False),
        "image": article["image"],
        "tags": article.get("tags", []),
        "summary": article["summary"],
        "claps": article.get("claps", 100),
        "views": article.get("views", "1.2K"),
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
    """Run automated news sweep and sync directly to Supabase Cloud Database."""
    print("=" * 70)
    print("🚀 MR. INFORMER CLOUD SUPABASE INGESTION WORKFLOW")
    print(f"📡 Querying {len(news_workflow.RSS_FEEDS)} global RSS sources...")
    print("=" * 70)

    existing_articles = fetch_supabase_articles()
    
    # Also load local articles for title normalization check
    local_articles = news_workflow.load_existing_articles()
    all_articles = existing_articles + local_articles

    news_items = news_workflow.fetch_all_rss_feeds()
    if not news_items:
        print("⚠️ No news items retrieved during this sweep.")
        return None

    for item in news_items:
        raw_title = item["raw_title"]
        if news_workflow.is_duplicate_article(raw_title, all_articles):
            continue

        # Synthesize fresh article
        article = news_workflow.generate_mr_informer_article(item, all_articles)
        
        # 1. Insert into Supabase
        cloud_success = insert_supabase_article(article)
        
        # 2. Also save to local database files as fallback
        local_articles.insert(0, article)
        news_workflow.save_articles(local_articles)
        
        print(f"✅ Auto-Published Scoop: '{article['title']}' [{article['category']}]")
        return article

    # Fallback: Guarantee continuous fresh posts even during quiet news periods
    import random
    fallback_topics = [
        "Autonomous AI Swarms Achieve Zero-Latency Edge Processing Milestones",
        "Post-Quantum Lattice Cryptography Breaches Sealed Across Edge Relays",
        "Next-Generation 100K Qubit Supercomputing Arrays Pass Stability Benchmarks",
        "Spatial Neural Wearables Set Thermal Micro-Architectural Output Records",
        "Zero-Trust Micro-Kernel Architecture Patched Against Perimeter Exploits"
    ]
    base_topic = random.choice(fallback_topics)
    raw_title = f"{base_topic} ({datetime.now().strftime('%b %d')})"
    
    if not news_workflow.is_duplicate_article(raw_title, all_articles):
        fallback_item = {
            "raw_title": raw_title,
            "link": "https://mrinformer.tech/scoop",
            "pubDate": "",
            "snippet": "Latest investigative telemetry confirms significant performance breakthroughs and zero-latency stability across enterprise infrastructure."
        }
        article = news_workflow.generate_mr_informer_article(fallback_item, all_articles)
        insert_supabase_article(article)
        local_articles.insert(0, article)
        news_workflow.save_articles(local_articles)
        print(f"✅ Auto-Published Fallback Scoop: '{article['title']}' [{article['category']}]")
        return article

    print("ℹ️ Sweep complete. All current RSS items already ingested.")
    return None

if __name__ == "__main__":
    run_cloud_ingestion()
