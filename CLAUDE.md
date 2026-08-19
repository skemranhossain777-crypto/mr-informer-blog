# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static tech/AI/cybersecurity blog (Mr. Informer, deployed at mr-informer.top via GitHub Pages) with no build step and no test suite: plain HTML/CSS/JS on the frontend, a Python content pipeline that pulls real RSS stories and republishes them as short attributed summaries, and Supabase (Postgres + Auth) as the backend. There is no `package.json`, no bundler, no framework — `index.html` loads `styles.css`, `articles.js`, `app.js`, `supabase_client.js` directly as `<script>` tags.

## Commands

No build/lint/test tooling exists. What you actually run:

```bash
# Validate a changed Python file before trusting it
python -m py_compile <file>.py

# Validate changed JS
node --check app.js

# Validate HTML after editing index.html or a generated page (no HTML linter installed —
# this is how validity gets checked throughout this repo's history)
python -c "
import html.parser
class C(html.parser.HTMLParser):
    def error(self, m): print('ERR:', m)
C().feed(open('index.html', encoding='utf-8').read())
"

# Run one ingestion cycle locally (reads .env, hits real RSS feeds + Supabase)
python news_workflow_supabase.py

# Rebuild all static article pages + sitemap.xml from Supabase (the real source of truth —
# see Architecture below). Do this after any articles.json/Supabase content change.
python generate_seo_pages.py
```

There's no local dev server requirement — `index.html` can be opened directly or served with any static file server.

## Architecture

**Supabase is the source of truth for articles, not `articles.json`.** `articles.json`/`articles.js` are a local fallback cache that the Python scripts write for when Supabase is unreachable, and that `app.js` reads on first paint before `supabase_client.js`'s `initCloudSupabaseSync()` overwrites `window.ARTICLES_DATA` with live Supabase data. When regenerating local state, pull from Supabase and overwrite the local files — don't hand-edit `articles.json` and expect it to matter to the live site.

**Content pipeline**: `news_workflow.py` holds the RSS feed list, the honest-template article generator (`generate_mr_informer_article`, `build_article_content`), and `pick_next_story()`/`run_sync()`. `news_workflow_supabase.py` wraps that for cloud publishing (writes to Supabase via `SUPABASE_SERVICE_ROLE_KEY`, then falls back to local files). **There is deliberately no fake-content fallback** — if no new, non-duplicate RSS item is found in a cycle, nothing gets published. Don't reintroduce a "guarantee a post every cycle" fallback; an earlier version of this pipeline did that by inventing headlines and fabricated stats, which is exactly what got removed (see `run_regen.py` / `migrate_supabase_articles.py`, which exist specifically to retroactively rewrite that old fabricated content into the honest template — reuse `rewrite_legacy_article()` from `run_regen.py` rather than duplicating that logic again).

**`llm_enrichment.py` optionally generates three editorial sections** for each new article via the Gemini API (Google AI Studio's free tier, plain REST via `urllib` — no extra pip dependency), called from `generate_mr_informer_article()`. The three sections are: (1) "Why this matters" — 2-4 sentence industry/trend framing, (2) "Technical context" — 2-4 sentence explanation of the underlying technology, (3) "Key takeaways" — 4-5 bullet points summarizing the most important points. It requires `GEMINI_API_KEY` (local `.env` + GitHub Actions secret); if unset, or the call errors/is blocked, it silently returns `None` and the article publishes with a template-generated fallback paragraph — this must never block or fail the pipeline. The model is instructed to ground everything strictly in the given headline/excerpt and never invent new facts, consistent with the no-fabrication rule above. `build_article_content()` in `news_workflow.py` renders all three sections as HTML when available, or falls back to a richer template when the LLM is unavailable. Existing articles are not retroactively enriched — only new ones going forward.

**`generate_seo_pages.py` is what makes articles indexable.** The homepage (`index.html` + `app.js`) is a client-rendered SPA — Google can't index anything inside its reader modal. This script builds one real static HTML page per article at `articles/<slug>/index.html` (full content, canonical URL, OG/Twitter tags, `NewsArticle` JSON-LD) plus `sitemap.xml`, by merging `articles.json` with a live pull from Supabase (so admin-CMS-published articles that never touch the local JSON still get indexed). Run it after any content change; it's idempotent.

**GitHub Actions (`.github/workflows/rss_ingestion.yml`) runs on a 3-hour cron and on every push to `main`**, executing `news_workflow_supabase.py` then `generate_seo_pages.py`, and auto-committing the result (`[skip ci]`). This means **the remote `main` branch can drift out from under a local branch between when you start working and when you push** — the bot commits directly to `main` on its own schedule. Before pushing, `git fetch` and check `git log HEAD..origin/main`; if there are bot commits touching `articles.json`/`articles.js`/`articles/`/`sitemap.xml`, merge them (`-X ours` is safe for those specific files since the next step regenerates them anyway) and then re-pull from Supabase + re-run `generate_seo_pages.py` before committing, rather than trusting a raw git text-merge of `articles.json`.

**Admin auth is real Supabase Auth, not a password in the code.** `supabase_client.js` implements `supabaseAdminSignIn`/`supabaseAdminSignOut` against Supabase's GoTrue REST endpoint; access is gated by RLS policies checking `auth.uid()` against the `admins` table (see `supabase_schema.sql`), not by anything the browser can fake. `supabase_schema.sql` is the single source of truth for schema/RLS — it's written to be safely re-run (`IF NOT EXISTS` / `DROP POLICY IF EXISTS` + recreate) and must be run manually in the Supabase SQL Editor; there's no migration runner.

**`SITE_DOMAIN`** (env var, read by `news_workflow.py` and used throughout `generate_seo_pages.py`) is the one place the production domain is templated from for canonical URLs/sitemap/OG tags. The static legal pages (`about/`, `contact/`, `privacy/`, `terms/`) and `robots.txt`/`index.html` hardcode the domain directly since they're hand-authored, not generated — update all of them together if the domain changes.

**AdSense**: the Auto ads loader script and `ads.txt` publisher ID are wired into `index.html`, the `generate_seo_pages.py` article template, and all four legal pages. There's no per-slot manual ad configuration (Auto ads places ads automatically); the commented `<ins class="adsbygoogle">` blocks left in place would need real ad-unit slot IDs from the AdSense dashboard to activate.

### Environment / credentials

Local `.env` (gitignored) holds `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SITE_DOMAIN`, and optionally `GEMINI_API_KEY` (for `llm_enrichment.py` — see above; the pipeline works fine without it). The **service role key bypasses RLS entirely** and is only ever used by the Python scripts — never reference it from `supabase_client.js` or any browser-shipped file. GitHub Actions needs its own copies as repo secrets (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, optionally `GEMINI_API_KEY`) and a repo variable (`SITE_DOMAIN`).

### Pushing to GitHub from a sandboxed/non-interactive shell

`git push`/`gh auth git-credential` can hang waiting on `/dev/tty` in non-interactive environments. Working fallback: `GH_TOKEN=$(gh auth token) && git -c credential.helper= push "https://<username>:${GH_TOKEN}@github.com/<owner>/<repo>.git" main`. The `gh` token needs the `workflow` OAuth scope to push changes to `.github/workflows/*` — if pushes get rejected with an auth error specifically on a workflow-file change, that's the likely cause (`gh auth login --web` refreshes scopes).
