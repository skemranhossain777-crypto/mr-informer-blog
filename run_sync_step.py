import sys
import os
import json

workspace_dir = r"d:\Apersonontherun\Google-Programmed\mr-informer-blog"
sys.path.insert(0, workspace_dir)

import news_workflow

if __name__ == "__main__":
    article = news_workflow.run_sync()
    if article:
        print("RESULT_JSON_START")
        print(json.dumps({
            "status": "published",
            "id": article["id"],
            "title": article["title"],
            "category": article["category"],
            "image": article["image"],
            "date": article["date"]
        }))
        print("RESULT_JSON_END")
    else:
        print("RESULT_JSON_START")
        print(json.dumps({"status": "no_new_story"}))
        print("RESULT_JSON_END")
