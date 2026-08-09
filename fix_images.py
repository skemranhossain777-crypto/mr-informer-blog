import json
import re

# Comprehensive pools of 100% DISTINCT Unsplash photos (NO REPEATING PHOTO IDs)
CATEGORY_LIBRARIES = {
    "AI & Future": [
        "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1555255707-c07966088b7b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1614741118887-7a4ee193a5fa?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1676299081847-824916de030a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1507146426996-ef05306b995a?auto=format&fit=crop&w=1200&q=80",
        "assets/article_ai.jpg"
    ],
    "Cyber Security": [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1510511459019-5dda7724fd87?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1526374870839-e155464bb9b2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1200&q=80",
        "assets/article_cyber.jpg"
    ],
    "Deep Dives": [
        "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1200&q=80",
        "assets/article_quantum.jpg"
    ],
    "Tech Pulse": [
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1592478411213-6153e4ebc07d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?auto=format&fit=crop&w=1200&q=80",
        "assets/hero_tech_cyber.jpg"
    ]
}

def extract_photo_id(url):
    """Extract unique photo identifier from Unsplash URL or asset path."""
    if 'photo-' in url:
        match = re.search(r'photo-[a-zA-Z0-9-]+', url)
        if match:
            return match.group(0)
    return url.split('?')[0]

def fix_all_article_images():
    with open('articles.json', 'r', encoding='utf-8') as f:
        articles = json.load(f)

    used_photo_ids = set()
    updated_count = 0

    for article in articles:
        category = article.get('category', 'Tech Pulse')
        current_img = article.get('image', '')
        curr_id = extract_photo_id(current_img)

        # If current image photo ID is already used or is blank, find a new distinct image
        if not curr_id or curr_id in used_photo_ids:
            candidates = CATEGORY_LIBRARIES.get(category, CATEGORY_LIBRARIES["Tech Pulse"])
            assigned = False
            for cand in candidates:
                cand_id = extract_photo_id(cand)
                if cand_id not in used_photo_ids:
                    article['image'] = cand
                    used_photo_ids.add(cand_id)
                    assigned = True
                    updated_count += 1
                    break
            
            if not assigned:
                # Check all pools
                for cat, cand_list in CATEGORY_LIBRARIES.items():
                    for cand in cand_list:
                        cand_id = extract_photo_id(cand)
                        if cand_id not in used_photo_ids:
                            article['image'] = cand
                            used_photo_ids.add(cand_id)
                            assigned = True
                            updated_count += 1
                            break
                    if assigned:
                        break
        else:
            used_photo_ids.add(curr_id)

    print(f"✅ Processed {len(articles)} articles. Re-assigned {updated_count} duplicate image URLs.")
    print(f"🌟 Total unique photo IDs active across all articles: {len(used_photo_ids)}")

    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    # Sync articles.js (must match the ARTICLES_DATA global app.js reads)
    with open('articles.js', 'w', encoding='utf-8') as f:
        f.write("const ARTICLES_DATA = " + json.dumps(articles, indent=2, ensure_ascii=False) + ";\n")
    print("✅ Successfully updated articles.json and synced articles.js!")

if __name__ == "__main__":
    fix_all_article_images()
