import time
import os
import sys
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import news_workflow

DEFAULT_INTERVAL_SECONDS = int(os.getenv("RSS_SWEEP_INTERVAL", "300"))  # Default 5 minutes

def run_schedule(interval_seconds=DEFAULT_INTERVAL_SECONDS):
    """Automated scheduling daemon that triggers news checks and posts breaking articles."""
    print("=" * 70)
    print("🚀 MR. INFORMER AUTOMATED SCHEDULER WORKFLOW DAEMON STARTED")
    print(f"⏰ Execution Interval: Every {interval_seconds} seconds ({interval_seconds // 60} minutes)")
    print(f"📡 Registered Sources: {len(news_workflow.RSS_FEEDS)} global open RSS feeds")
    print("=" * 70)

    iteration = 1
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] 🔄 Triggering Scheduled News Check Cycle #{iteration}...")
        
        try:
            import importlib
            import news_workflow_supabase
            importlib.reload(news_workflow)
            importlib.reload(news_workflow_supabase)
            article = news_workflow_supabase.run_cloud_ingestion()
            if not article:
                article = news_workflow.run_sync()
            if article:
                print(f"✅ [{timestamp}] Auto-Posted Dispatch: '{article['title']}' [{article['category']}]")
        except Exception as e:
            print(f"❌ [{timestamp}] Scheduler Execution Error: {e}")

        iteration += 1
        print(f"⏰ Next automated sweep in {interval_seconds} seconds...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    interval = DEFAULT_INTERVAL_SECONDS
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        interval = int(sys.argv[1])
    run_schedule(interval)
