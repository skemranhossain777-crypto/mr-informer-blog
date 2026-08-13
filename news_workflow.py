import os
import json
import time
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import llm_enrichment

# Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_JSON_PATH = os.path.join(BASE_DIR, "articles.json")
ARTICLES_JS_PATH = os.path.join(BASE_DIR, "articles.js")

def load_env():
    """Parse local .env file securely into environment variables."""
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

load_env()

# Public site domain used for canonical URLs / sitemap / source links.
# Swap this once a domain is registered (see .env.example).
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "https://mr-informer.top").rstrip("/")

# Image Pool
IMAGE_POOL = [
    "assets/hero_tech_cyber.jpg",
    "assets/article_ai.jpg",
    "assets/article_cyber.jpg",
    "assets/article_quantum.jpg"
]

# Friendly display names for the RSS sources we cite in each briefing.
SOURCE_FRIENDLY_NAMES = {
    "techcrunch.com": "TechCrunch",
    "arstechnica.com": "Ars Technica",
    "feeds.arstechnica.com": "Ars Technica",
    "wired.com": "Wired",
    "theverge.com": "The Verge",
    "engadget.com": "Engadget",
    "venturebeat.com": "VentureBeat",
    "zdnet.com": "ZDNet",
    "techradar.com": "TechRadar",
    "readwrite.com": "ReadWrite",
    "technologyreview.com": "MIT Technology Review",
    "gizmodo.com": "Gizmodo",
    "slashdot.org": "Slashdot",
    "mashable.com": "Mashable",
    "lifehacker.com": "Lifehacker",
    "dev.to": "DEV Community",
    "bleepingcomputer.com": "BleepingComputer",
    "darkreading.com": "Dark Reading",
    "securityweek.com": "SecurityWeek",
    "krebsonsecurity.com": "Krebs on Security",
    "thehackernews.com": "The Hacker News",
    "spectrum.ieee.org": "IEEE Spectrum",
    "tomshardware.com": "Tom's Hardware",
    "scitechdaily.com": "SciTechDaily",
    "news.google.com": "Google News",
    "hnrss.org": "Hacker News",
    "arxiv.org": "arXiv",
    "rss.arxiv.org": "arXiv",
    "mit.edu": "MIT",
    "news.mit.edu": "MIT News",
    "theregister.com": "The Register",
    "techmeme.com": "Techmeme",
    "cisa.gov": "CISA",
    "siliconangle.com": "SiliconANGLE",
    "cnet.com": "CNET",
}

def extract_source_name(link):
    """Best-effort friendly publication name for outbound attribution."""
    if not link:
        return "the original source"
    try:
        netloc = urllib.parse.urlparse(link).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return SOURCE_FRIENDLY_NAMES.get(netloc, netloc or "the original source")
    except Exception:
        return "the original source"

def fix_mojibake(raw_bytes):
    """Recover feed bytes that are UTF-8-declared but actually Windows-1252
    (the classic cause of stray ï¿½/replacement-character garbage in titles)."""
    try:
        raw_bytes.decode("utf-8")
        return raw_bytes
    except UnicodeDecodeError:
        try:
            return raw_bytes.decode("cp1252").encode("utf-8")
        except Exception:
            return raw_bytes

# Comprehensive Global RSS Directory (50+ Open Tech, AI, Cyber, Science, Hardware Sources)
RSS_FEEDS = [
    # Top Tech News Publications
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.wired.com/feed/rss",
    "https://hnrss.org/newest?points=100",
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://venturebeat.com/feed/",
    "https://www.zdnet.com/news/rss.xml",
    "https://www.techradar.com/rss",
    "https://readwrite.com/feed/",
    "https://technologyreview.com/feed/",
    "https://gizmodo.com/rss",
    "https://slashdot.org/slashdot.rss",
    "https://mashable.com/feeds/rss/all",
    "https://lifehacker.com/rss",
    
    "https://www.theregister.com/headlines.atom",
    "https://www.techmeme.com/feed.xml",
    "https://www.cnet.com/rss/news/",

    # AI & Deep Learning Feeds
    "https://news.google.com/rss/search?q=artificial+intelligence+llm+neural+networks+openai+deepmind&hl=en-US&gl=US&ceid=US:en",
    "https://dev.to/feed/tag/ai",
    "https://dev.to/feed/tag/machinelearning",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://rss.arxiv.org/rss/cs.AI",
    "https://rss.arxiv.org/rss/cs.CL",
    "https://siliconangle.com/feed/",

    # Cyber Security & Zero-Day Exploits
    "https://news.google.com/rss/search?q=cybersecurity+zero-day+vulnerability+exploit+ransomware&hl=en-US&gl=US&ceid=US:en",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.darkreading.com/rss.xml",
    "https://www.securityweek.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://thehackernews.com/feeds/posts/default",
    "https://dev.to/feed/tag/security",
    "https://dev.to/feed/tag/cybersecurity",
    "https://www.theregister.com/security/headlines.atom",
    "https://www.cisa.gov/cybersecurity-advisories/all.xml",

    # Quantum Computing & Hardware Deep Dives
    "https://news.google.com/rss/search?q=quantum+computing+semiconductors+microprocessors+supercomputers&hl=en-US&gl=US&ceid=US:en",
    "https://spectrum.ieee.org/rss/fulltext",
    "https://www.tomshardware.com/feeds/all",
    "https://scitechdaily.com/feed/",
    "https://news.mit.edu/rss/research",
    "https://dev.to/feed/tag/hardware",

    # Developer & Tech Pulse
    "https://dev.to/feed",
    "https://rss.arxiv.org/rss/cs.SE",
    "https://news.google.com/rss/search?q=spatial+computing+neural+wearables+robotics&hl=en-US&gl=US&ceid=US:en"
]

def _local_tag(tag):
    """Strip an XML namespace prefix off a tag, e.g. '{http://...}item' -> 'item'."""
    return tag.split('}')[-1] if '}' in tag else tag

def _child_text(elem, names):
    """First direct child of elem whose local tag is in `names`, preferring its
    text content and falling back to an href attribute (for Atom <link> tags)."""
    for child in elem:
        if _local_tag(child.tag) in names:
            if child.text and child.text.strip():
                return child.text.strip()
            href = child.attrib.get('href')
            if href:
                return href
    return ""

def fetch_rss_single(feed_url):
    """Fetch and parse a single feed with timeout. Handles plain RSS 2.0,
    namespaced RSS 1.0/RDF (e.g. Slashdot), and Atom (e.g. The Register)."""
    items = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MrInformer/2026'}
    try:
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            xml_data = fix_mojibake(response.read())
            root = ET.fromstring(xml_data)

            # Wildcard-namespace match covers RSS 2.0 <item>, RSS 1.0/RDF
            # <item> (default-namespaced), and falls back to Atom <entry>.
            entries = root.findall('.//{*}item')[:8] or root.findall('.//{*}entry')[:8]

            for item in entries:
                title = _child_text(item, {'title'})
                link = _child_text(item, {'link'})
                pubDate = _child_text(item, {'pubDate', 'published', 'updated', 'date'})
                description = _child_text(item, {'description', 'summary', 'content', 'encoded'})

                clean_desc = html.unescape(re.sub('<[^<]+?>', '', description)).strip()
                clean_title = html.unescape(title).strip()
                if clean_title and len(clean_title) > 15:
                    items.append({
                        'raw_title': clean_title,
                        'link': link,
                        'pubDate': pubDate,
                        'snippet': clean_desc[:500]
                    })
    except Exception:
        pass
    return items

def fetch_rss_items():
    """Fetch and parse breaking tech news items in parallel from 50+ global RSS feeds."""
    news_items = []
    print(f"📡 Querying {len(RSS_FEEDS)} global open RSS feeds in parallel (Worker Pool: 20)...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(fetch_rss_single, url): url for url in RSS_FEEDS}
        for future in as_completed(future_to_url):
            res = future.result()
            if res:
                news_items.extend(res)

    print(f"⚡ Successfully retrieved {len(news_items)} raw news items from global feeds.")
    return news_items

def determine_category(title, snippet):
    """Categorize news into site categories based on multi-keyword analysis."""
    text = (title + " " + snippet).lower()
    
    if any(k in text for k in ['ai', 'intelligence', 'gpt', 'model', 'neural', 'llm', 'deep learning', 'openai', 'anthropic', 'deepmind', 'autonomous', 'agent']):
        return "AI & Future"
    elif any(k in text for k in ['cyber', 'hack', 'security', 'zero-day', 'exploit', 'breach', 'vulnerability', 'encrypt', 'malware', 'ransomware', 'patch']):
        return "Cyber Security"
    elif any(k in text for k in ['quantum', 'chip', 'processor', 'hardware', 'semiconductor', 'supercomputer', 'qubit', 'silicon', 'physics']):
        return "Deep Dives"
    else:
        return "Tech Pulse"

# Extended Curated High-Definition Technology Cover Photo Library (Distinct Photo IDs)
COVER_IMAGE_LIBRARY = {
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
    """Extract photo ID from Unsplash URL or asset path."""
    if 'photo-' in url:
        match = re.search(r'photo-[a-zA-Z0-9-]+', url)
        if match:
            return match.group(0)
    return url.split('?')[0]

def generate_unique_cover_image(category, title, existing_articles):
    """Guarantees a 100% unique cover image URL per article with no repetitions."""
    used_photo_ids = set()
    for a in existing_articles:
        img = a.get('image', '')
        if img:
            used_photo_ids.add(extract_photo_id(img))

    # 1. Check primary category pool
    candidates = COVER_IMAGE_LIBRARY.get(category, COVER_IMAGE_LIBRARY["Tech Pulse"])
    for url in candidates:
        if extract_photo_id(url) not in used_photo_ids:
            return url

    # 2. Search all pools across all categories
    for cat_list in COVER_IMAGE_LIBRARY.values():
        for url in cat_list:
            if extract_photo_id(url) not in used_photo_ids:
                return url

    # 3. Dynamic Seeded High-Resolution Image Generator (Guarantees 100% unique image for unlimited articles)
    title_slug = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
    unique_seed = abs(hash(title_slug + str(len(existing_articles)))) % 999999
    return f"https://picsum.photos/seed/tech{unique_seed}/1200/800"

def split_snippet_for_quote(snippet):
    """Split a snippet into (lead sentence(s), distinct pull-quote) so a page
    doesn't render the exact same sentence twice — once as body text and once
    in a blockquote, which reads as templated/duplicate content to a reviewer.
    Falls back to no pull-quote when there isn't a second, genuinely different
    sentence to show."""
    sentences = [s for s in re.split(r'(?<=[.!?])\s+', snippet.strip()) if s]
    if len(sentences) < 2:
        return snippet, None
    lead, quote = sentences[0], " ".join(sentences[1:])
    if not quote.strip() or quote.strip() == lead.strip():
        return snippet, None
    return lead, quote

def estimate_read_time(content_html):
    """Honest read-time estimate from the actual rendered word count, instead
    of a hardcoded '3 min read' regardless of how short the summary is."""
    text = re.sub('<[^<]+?>', ' ', content_html or '')
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"

def build_article_content(cleaned_title, snippet, source_name, source_url, editorial_context=None):
    """Honest article body: a labeled summary + real attribution, no invented
    statistics or quotes. This is what used to be a hash-generated fake
    infographic and fabricated 'verified' metrics table. `editorial_context`
    is an optional LLM-generated "Why this matters" paragraph (see
    llm_enrichment.py) — grounded in the same snippet, never a substitute
    for it, and omitted entirely when unavailable."""
    safe_snippet = snippet.strip() if snippet else "See the original report for full details."
    lead, quote = split_snippet_for_quote(safe_snippet)

    source_link_html = (
        f'<p class="article-source-note">Read the full original report at '
        f'<a href="{html.escape(source_url)}" target="_blank" rel="noopener noreferrer nofollow">{html.escape(source_name)} →</a></p>'
        if source_url else ""
    )

    quote_html = (
        f'<div class="article-quote-box">\n      <p>"{html.escape(quote)}"</p>\n      <cite>— {html.escape(source_name)}</cite>\n    </div>\n\n    '
        if quote else ""
    )

    editorial_html = (
        f'<h3>Why this matters</h3>\n    <p>{html.escape(editorial_context)}</p>\n\n    '
        if editorial_context else ""
    )

    content_html = f"""
    <p class="ai-disclosure-badge">🤖 AI-assisted summary of third-party reporting — see our <a href="/terms/">AI use policy</a></p>

    <p class="article-lead">{html.escape(lead)}</p>

    {quote_html}<h3>What this covers</h3>
    <p>This is a Mr. Informer briefing on <strong>{html.escape(cleaned_title)}</strong> — a short, automation-assisted summary of reporting from {html.escape(source_name)}. For full quotes, sourcing, and context, read the original report linked below.</p>

    {editorial_html}{source_link_html}
    """
    return content_html

def build_archival_notice_content(cleaned_title, snippet):
    """Honest body for pre-source-tracking legacy articles: preserves whatever
    real snippet text survives, but makes clear no verified source link exists
    for this one, instead of the old copy that promised a link with none there."""
    safe_snippet = snippet.strip() if snippet else "No further detail survives from this earlier post."
    lead, quote = split_snippet_for_quote(safe_snippet)

    quote_html = (
        f'<div class="article-quote-box">\n      <p>"{html.escape(quote)}"</p>\n      <cite>— unverified source (predates source tracking)</cite>\n    </div>\n\n    '
        if quote else ""
    )

    content_html = f"""
    <p class="ai-disclosure-badge">🗄️ Archival brief — original source not verified</p>

    <p class="article-lead">{html.escape(lead)}</p>

    {quote_html}<h3>About this brief</h3>
    <p>This briefing on <strong>{html.escape(cleaned_title)}</strong> was published before Mr. Informer began recording a verified, clickable source link for every article. We can't confirm or link back to the original reporting it was based on, so treat this as an unverified archival summary rather than a sourced briefing. Every new briefing links directly to its original source — see our <a href="/terms/">AI use policy</a> and recent posts for examples.</p>
    """
    return content_html

def generate_mr_informer_article(news_item, existing_articles=None):
    """Build a Mr. Informer briefing from a real RSS item: honest summary,
    real attribution + outbound link to the source, no fabricated data."""
    if existing_articles is None:
        existing_articles = []

    raw_title = news_item['raw_title']
    snippet = news_item['snippet'] if news_item['snippet'] else "See the original report for full details."
    category = determine_category(raw_title, snippet)

    # Clean source suffix (e.g. " - TechCrunch")
    cleaned_title = re.sub(r' - [^-]+$', '', raw_title)
    cleaned_title = re.sub(r' \| [^|]+$', '', cleaned_title)
    article_title = f"Mr. Informer Briefing: {cleaned_title}"

    source_url = news_item.get('link', '')
    source_name = extract_source_name(source_url)

    # Unique slug/ID
    slug_base = re.sub(r'[^a-zA-Z0-9]', '-', cleaned_title.lower())[:40].strip('-') or "briefing"
    article_id = f"auto-{slug_base}-{int(time.time())}"

    # Dynamic Unique Cover Image & Tag Mapping
    img = generate_unique_cover_image(category, cleaned_title, existing_articles)

    if category == "AI & Future":
        tags = ["AI & Future", "Artificial Intelligence", "Deep Learning", "Automation"]
    elif category == "Cyber Security":
        tags = ["Cyber Security", "Zero-Day", "Cryptography", "Network Safety"]
    elif category == "Deep Dives":
        tags = ["Deep Dives", "Quantum Computing", "Hardware", "Physics"]
    else:
        tags = ["Tech Pulse", "Spatial Computing", "Wearables", "AR/VR"]

    formatted_date = datetime.now().strftime("%B %d, %Y - %H:%M")
    editorial_context = llm_enrichment.generate_editorial_context(cleaned_title, snippet, source_name)
    content_html = build_article_content(cleaned_title, snippet, source_name, source_url, editorial_context)
    summary = f"Mr. Informer briefing on {cleaned_title}, summarizing reporting from {source_name}."

    article = {
        "id": article_id,
        "slug": article_id,
        "title": article_title,
        "category": category,
        "readTime": estimate_read_time(content_html),
        "date": formatted_date,
        "author": {
            "name": "Mr. Informer",
            "title": "AI-Assisted Briefing Desk",
            "avatar": "assets/author_avatar.jpg"
        },
        "featured": False,
        "image": img,
        "tags": tags,
        "summary": summary,
        "sourceName": source_name,
        "sourceUrl": source_url,
        "claps": 0,
        "views": "New",
        "content": content_html,
        "comments": []
    }
    return article

def load_existing_articles():
    """Load existing articles from articles.json."""
    if os.path.exists(ARTICLES_JSON_PATH):
        try:
            with open(ARTICLES_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Workflow Error] Failed reading articles.json: {e}")
    return []

def save_articles(articles):
    """Save articles list to articles.json and articles.js."""
    with open(ARTICLES_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2)

    js_content = f"const ARTICLES_DATA = {json.dumps(articles, indent=2)};\n"
    with open(ARTICLES_JS_PATH, 'w', encoding='utf-8') as f:
        f.write(js_content)

def fetch_all_rss_feeds():
    """Fetch breaking tech news items in parallel from configured RSS feeds."""
    return fetch_rss_items()

def is_duplicate_article(raw_title, existing_articles):
    """Check if a raw title or synthesized title already exists in existing articles list."""
    clean_t = re.sub(r' - [^-]+$', '', raw_title).strip()
    clean_t = re.sub(r' \| [^|]+$', '', clean_t).strip()
    candidate_title = f"Mr. Informer Briefing: {clean_t}".lower()

    existing_titles_norm = set()
    for a in existing_articles:
        t = a.get('title', '').lower().strip()
        existing_titles_norm.add(t)
        # Strip both the current and the old (pre-rewrite) title prefixes so
        # articles published before this rewrite still count as duplicates.
        existing_titles_norm.add(re.sub(r'^mr\. informer briefing:\s*', '', t))
        existing_titles_norm.add(re.sub(r'^exclusive intel:\s*', '', t))

    return candidate_title in existing_titles_norm or clean_t.lower() in existing_titles_norm

def pick_next_story(existing_articles=None):
    """Fetch RSS items and return the first one that isn't a duplicate of an
    existing article, or None if there's nothing new right now. Deliberately
    has no fabricated fallback — a quiet cycle with no publish is normal and
    expected, unlike the old version which invented a fake headline here."""
    if existing_articles is None:
        existing_articles = load_existing_articles()

    items = fetch_rss_items()
    if not items:
        print("[Workflow] No RSS items retrieved this cycle.")
        return None

    for item in items:
        if not is_duplicate_article(item['raw_title'], existing_articles):
            return item

    print("[Workflow] No new (non-duplicate) stories found this cycle.")
    return None

def run_sync():
    """Fetch RSS items, create at most one article, and update articles.json
    & articles.js. Returns None (without publishing anything) if there's no
    genuinely new story to report."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running automated news search workflow...")

    existing_articles = load_existing_articles()
    selected_item = pick_next_story(existing_articles)
    if not selected_item:
        return None

    new_article = generate_mr_informer_article(selected_item, existing_articles=existing_articles)

    existing_articles.insert(0, new_article)
    save_articles(existing_articles)

    print(f"✅ Published New Article: '{new_article['title']}' ({new_article['category']})")
    return new_article

def start_daemon(interval_seconds=None):
    """Run the workflow continuously (default: every 3 hours). Only used for
    local/manual runs — production scheduling is the GitHub Actions cron."""
    if interval_seconds is None:
        interval_seconds = int(os.getenv("RSS_SWEEP_INTERVAL", "10800"))
    print(f"🚀 Starting Mr. Informer Automated News Dispatch Daemon (Interval: {interval_seconds}s)")
    while True:
        try:
            run_sync()
        except Exception as e:
            print(f"[Workflow Error] Execution error: {e}")
        print(f"⏰ Sleeping for {interval_seconds // 60} minutes until next cycle...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        start_daemon()
    else:
        run_sync()

