"""
Builds the crawlable, static half of the site that the SPA (index.html +
app.js) can't provide on its own:

  - articles/<slug>/index.html  — one real, indexable page per article, with
    full server-rendered content, unique meta tags, canonical URL, Open
    Graph/Twitter Card tags, and NewsArticle JSON-LD.
  - sitemap.xml                 — every article + the static pages.

Google (and AdSense reviewers) need actual HTML to read; a click-only JS
modal has nothing to index. The homepage SPA still works exactly as before —
these pages are an addition, not a replacement — and clicking an article
card on the homepage opens the fast in-page reader instead of navigating
here, unless the visitor arrives directly (e.g. from a Google search result)
or opens it in a new tab.

Run standalone: `python generate_seo_pages.py`
Also called automatically at the end of news_workflow.run_sync() and
news_workflow_supabase.run_cloud_ingestion() after a new article is saved.
"""
import os
import re
import json
import html
import urllib.request
from datetime import datetime

import news_workflow as nw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")

SITE_DOMAIN = nw.SITE_DOMAIN
SITE_NAME = "Mr. Informer"

STATIC_PAGES = ["/", "/about/", "/contact/", "/privacy/", "/terms/"]


def slugify(text, fallback="post"):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:80] or fallback


def article_slug(article):
    return article.get("slug") or article.get("id") or slugify(article.get("title"))


def absolute_url(path):
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{SITE_DOMAIN}/{path.lstrip('/')}"


def parse_article_date(date_str):
    """Article dates are stored as 'August 09, 2026 - 14:38'; fall back to
    now() for anything that doesn't parse (e.g. hand-entered CMS dates)."""
    try:
        return datetime.strptime(date_str, "%B %d, %Y - %H:%M")
    except (ValueError, TypeError):
        return datetime.now()


def fetch_supabase_articles():
    """Pull in articles published through the admin CMS (Supabase-only,
    never written to local articles.json) so they get static pages too.
    Public anon key is fine here — RLS allows public SELECT on articles."""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return []
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/articles?select=*&order=created_at.desc",
            headers={"apikey": key, "Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[SEO Pages] Could not fetch Supabase articles (continuing with local only): {e}")
        return []

    articles = []
    for r in rows:
        articles.append({
            "id": r.get("id"),
            "slug": r.get("slug") or r.get("id"),
            "title": r.get("title", "Untitled Brief"),
            "category": r.get("category", "Tech Pulse"),
            "readTime": r.get("read_time", "3 min read"),
            "date": r.get("date", ""),
            "author": r.get("author") or {"name": "Mr. Informer", "title": "Chief Investigative Tech Analyst", "avatar": "assets/author_avatar.jpg"},
            "featured": bool(r.get("featured", False)),
            "image": r.get("image", "assets/hero_tech_cyber.jpg"),
            "tags": r.get("tags") or [],
            "summary": r.get("summary", ""),
            "sourceName": r.get("source_name") or "",
            "sourceUrl": r.get("source_url") or "",
            "claps": r.get("claps", 0),
            "views": r.get("views", "New"),
            "content": r.get("content", ""),
            "comments": r.get("comments") or [],
        })
    return articles


def load_all_articles():
    local = nw.load_existing_articles()
    cloud = fetch_supabase_articles()

    merged = {}
    for art in local + cloud:
        merged[article_slug(art)] = art
    return list(merged.values())


def render_head(title, description, canonical_url, image_url, extra_meta=""):
    return f"""<title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:image" content="{image_url}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:type" content="{'article' if extra_meta else 'website'}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)}">
  <meta name="twitter:description" content="{html.escape(description)}">
  <meta name="twitter:image" content="{image_url}">
  {extra_meta}
  <link rel="stylesheet" href="/styles.css">"""


def render_chrome_header():
    return """<header class="site-header">
    <div class="container nav-wrapper">
      <a href="/" class="brand-logo">
        <div class="logo-badge">MI</div>
        <div class="brand-title">Mr. Informer <span>Blog</span></div>
      </a>
    </div>
  </header>"""


def render_chrome_footer():
    return f"""<footer class="site-footer">
    <div class="container footer-grid">
      <div class="footer-col">
        <a href="/" class="brand-logo" style="margin-bottom: 16px;">
          <div class="logo-badge">MI</div>
          <div class="brand-title">Mr. Informer <span>Blog</span></div>
        </a>
        <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
          Independent tech coverage: AI, cybersecurity, and hardware briefings, curated with disclosed AI assistance and linked back to original reporting.
        </p>
      </div>
      <div class="footer-col">
        <h4>Legal</h4>
        <ul class="footer-links">
          <li><a href="/about/">About</a></li>
          <li><a href="/contact/">Contact</a></li>
          <li><a href="/privacy/">Privacy Policy</a></li>
          <li><a href="/terms/">Terms</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      &copy; {datetime.now().year} Mr. Informer Blog. All rights reserved.
    </div>
  </footer>"""


def render_related_links(article, all_articles):
    slug = article_slug(article)
    same_category = [a for a in all_articles if a.get("category") == article.get("category") and article_slug(a) != slug]
    others = [a for a in all_articles if article_slug(a) != slug and a not in same_category]
    picks = (same_category + others)[:3]
    if not picks:
        return ""
    items = "\n".join(
        f'<li><a href="/articles/{article_slug(a)}/">{html.escape(a.get("title", "Untitled Brief"))}</a></li>'
        for a in picks
    )
    return f"""<section style="margin-top: 48px;">
      <h3 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 12px;">More from Mr. Informer</h3>
      <ul style="line-height: 2;">{items}</ul>
    </section>"""


def render_article_page(article, all_articles):
    slug = article_slug(article)
    title = article.get("title", "Untitled Brief")
    summary = (article.get("summary") or "").strip()
    description = (summary[:157] + "...") if len(summary) > 160 else summary
    canonical_url = f"{SITE_DOMAIN}/articles/{slug}/"
    image_url = absolute_url(article.get("image", "assets/hero_tech_cyber.jpg"))
    published_iso = parse_article_date(article.get("date", "")).isoformat()
    author_name = (article.get("author") or {}).get("name", "Mr. Informer") if isinstance(article.get("author"), dict) else "Mr. Informer"

    json_ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": description,
        "image": [image_url] if image_url else [],
        "datePublished": published_iso,
        "dateModified": published_iso,
        "author": {"@type": "Person", "name": author_name},
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "logo": {"@type": "ImageObject", "url": absolute_url("assets/author_avatar.jpg")}
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url}
    }
    extra_meta = f'<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>\n  <meta property="article:published_time" content="{published_iso}">'

    head = render_head(f"{title} | {SITE_NAME}", description, canonical_url, image_url, extra_meta)

    page = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {head}
  <!-- Google AdSense (Auto ads) -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5604509489162955" crossorigin="anonymous"></script>
</head>
<body>
  <div class="bg-ambient-glow"></div>
  {render_chrome_header()}
  <main class="container" style="max-width: 780px; padding-top: 32px; padding-bottom: 64px;">
    <p style="font-size: 0.85rem;"><a href="/">← Back to Mr. Informer</a></p>
    <img src="{html.escape(article.get('image', 'assets/hero_tech_cyber.jpg'))}" alt="{html.escape(title)}" style="width: 100%; border-radius: var(--radius-md); margin: 16px 0;">
    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px;">
      {html.escape(article.get('category', 'Tech Pulse'))} • {html.escape(article.get('readTime', '3 min read'))} • {html.escape(article.get('date', ''))}
    </div>
    <h1 style="font-family: var(--font-heading); font-size: 2rem; margin-bottom: 20px;">{html.escape(title)}</h1>
    <article class="article-body-content">
      {article.get('content', '')}
    </article>

    <!-- AdSense in-article slot: uncomment after approval and set your
         ad-slot ID (also requires the loader script in <head>). -->
    <!--
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-5604509489162955" data-ad-slot="0000000000" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    -->

    {render_related_links(article, all_articles)}
  </main>
  {render_chrome_footer()}
</body>
</html>
"""
    return page


def render_sitemap(all_articles):
    urls = []
    for path in STATIC_PAGES:
        urls.append(f"  <url><loc>{SITE_DOMAIN}{path}</loc></url>")
    for art in all_articles:
        slug = article_slug(art)
        lastmod = parse_article_date(art.get("date", "")).strftime("%Y-%m-%d")
        urls.append(f'  <url><loc>{SITE_DOMAIN}/articles/{slug}/</loc><lastmod>{lastmod}</lastmod></url>')

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls) + "\n</urlset>\n")


def generate_all():
    all_articles = load_all_articles()
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    written = 0
    for art in all_articles:
        slug = article_slug(art)
        if not slug:
            continue
        page_dir = os.path.join(ARTICLES_DIR, slug)
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_article_page(art, all_articles))
        written += 1

    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(render_sitemap(all_articles))

    print(f"[SEO Pages] Wrote {written} article page(s) to /articles/ and sitemap.xml ({len(all_articles)} URLs).")
    return written


if __name__ == "__main__":
    generate_all()
