# Content Pipeline Report — Mr. Informer Blog

Audit date: 2026-08-09

## How it works, end to end

```
GitHub Actions cron (every 3 hours) or a push to main
        │
        ▼
news_workflow_supabase.py
        │  fetch ~30 RSS feeds in parallel (news_workflow.RSS_FEEDS)
        │  drop items already published (title-match against Supabase + local)
        │  first genuinely new item → generate_mr_informer_article()
        │      (honest summary + real attribution + link to source;
        │       no fabricated stats, no invented headlines)
        │  no new item found → publish nothing, log and exit
        ▼
Supabase `articles` table (source of truth)  +  local articles.json/articles.js (fallback cache)
        │
        ▼
generate_seo_pages.py
        │  pull full article set from Supabase (+ merge local)
        │  write articles/<slug>/index.html  (static, crawlable, per-article page)
        │  write sitemap.xml
        ▼
git auto-commit [skip ci] → GitHub Pages rebuilds → live at mr-informer.top
```

The homepage (`index.html` + `app.js`) is a separate client-rendered SPA that reads Supabase directly at runtime (`supabase_client.js`) for the interactive browsing experience; the generated `articles/*` pages exist specifically so Google has real HTML to index, since the SPA's reader modal has nothing at a crawlable URL.

## Pros

- **No fabrication.** The generator only ever publishes a real RSS item with attribution + outbound link, or nothing. There's no "guarantee a post every cycle" fallback anymore — a quiet news cycle correctly results in zero posts.
- **Supabase as source of truth + local fallback** means the site still has content to show even if Supabase is briefly unreachable at page-load time.
- **Idempotent regeneration.** `generate_seo_pages.py` can be re-run any time with no side effects other than rewriting its own output — safe to run after any manual content change.
- **Real security boundary.** Writes to Supabase go through `SUPABASE_SERVICE_ROLE_KEY` (Python-only, never shipped to the browser); the admin CMS in the browser goes through real Supabase Auth + an `admins`-table RLS check, not a password baked into client JS.
- **Duplicate detection** works off normalized title matching against both Supabase and local state before generating anything, so the same story doesn't get re-published on the next cycle.

## Cons / risks found

1. **Local `articles.json` and live Supabase can silently diverge.** The GitHub Actions bot commits directly to `main` on its own 3-hour schedule. Anyone pushing from a separate local clone can end up with a stale base and a non-fast-forward push, and a naive `git merge` on `articles.json` (a large JSON array) can textually "succeed" while producing logically wrong results (this happened during setup — see below). **Mitigation in place**: `generate_seo_pages.py` and the resync procedure documented in `CLAUDE.md` always treat Supabase as authoritative and rebuild local files from it rather than trusting a git merge of the JSON — but this requires a human/agent to remember to do it. There's no automated guard against it.
2. **The "RSS Automation" tab in the admin CMS was fully decorative.** It let an admin edit RSS feed URLs / publish interval / poll interval and "save" them — but nothing in the codebase ever reads `config.automation` back out. The real feed list and schedule live only in `news_workflow.py` and the GitHub Actions YAML. **Fixed**: added an explicit warning in that tab (not removed, since the fields are harmless to keep as a planning/reference surface) so this doesn't read as a working control.
3. **No automated test coverage.** Nothing verifies `generate_mr_informer_article()`'s output shape, RSS parsing resilience, or that a schema change doesn't silently break the Supabase writes. Everything in this pipeline is currently validated by hand (`python -m py_compile`, ad hoc smoke tests, live curl checks against the deployed site).
4. **Mojibake repair is best-effort, not guaranteed.** `fix_mojibake()` in `news_workflow.py` fixes the specific "UTF-8 bytes misdecoded as Windows-1252" failure mode going forward; it can't recover already-corrupted historical text (a small number of old titles/summaries may still read slightly oddly where a lost byte hit U+FFFD before this fix existed).
5. **Single point of duplicate-detection failure**: matching is purely on normalized title text. A source that changes its headline slightly between an RSS update and a later re-crawl, or two outlets covering the same story with different headlines, would both be treated as new and published separately. Low-severity (not fabrication, just occasional near-duplicate real coverage) but worth knowing.

## Dummy / generic content found and removed

| Item | What it was | Fix |
|---|---|---|
| 4 seed articles (`ai-quantum-leap-2026`, `neural-glass-wearables`, `quantum-processor-milestone`, `zero-day-mesh-breach`) | Fully invented demo content bundled with the original site template — fake titles, no real source URL, dated before the real RSS pipeline ever ran. `ai-quantum-leap-2026` was the **featured hero article** on the homepage. | Deleted from Supabase (the live source of truth). Hero now falls back to the most recent real article, as designed. |
| "LIVE SCOOP" ticker bar | Static hardcoded marketing copy ("Autonomous AI swarms refactor code in under 90 seconds," etc.) — never reflected real articles, presented under a "LIVE" label. | Now dynamically built from the titles of the most recently published real articles (`renderTicker()` in `app.js`), refreshed on every article-data reload. |
| "Trending Tags" sidebar | Static list of 7 hardcoded tag buttons, including `#LiveScoop` — a tag no article carries anymore, so that filter button was dead. | Now computed live from actual tag frequency across loaded articles (`renderTrendingTags()`), including active-state highlighting. |
| CMS "Live Breaking Ticker Items" field | An editable textarea whose default value was the same fabricated ticker copy above, and which — now that the ticker is dynamic — would have fought with real data if ever used. | Removed (ticker is no longer admin-editable text; it's always real). |
| CMS "Logo Badge Text" field | Editable 2-letter text for a badge that's now a real logo image. | Removed, along with its dead JS wiring. |
| Announcement banner default copy | Disabled by default (`showAnnouncement: false`), but its default text was a fabricated claim ("Q3 Special Telemetry Report... unredacted logs"), which would have shown verbatim if ever toggled on without editing. | Replaced with an honest, obviously-a-placeholder default. |
| Branding tagline default | Unused dead default, but read "Uncensored Tech Intelligence & Deep Investigations" — inconsistent with the site's actual honest-summary positioning. | Updated text (still not rendered anywhere currently, but no longer contradicts the real branding if ever wired up). |

## Workflow health check

- Confirmed via GitHub's API that `.github/workflows/rss_ingestion.yml` on `main` has the corrected `cron: '0 */3 * * *'` schedule (previously every 5 minutes).
- Reviewed the last 20 Action runs: all `Automated RSS Cloud Ingestion Workflow` runs completed successfully (no failures), both `schedule`- and `push`-triggered.
- The handful of 5-minute-interval `schedule` runs seen were leftover triggers queued before the cron fix landed — expected, not a bug. Not enough time has elapsed since the fix to empirically observe a full 3-hour gap between runs yet; worth spot-checking again in a day.
- Live-verified the actual deployed site (not just the repo) reflects pipeline output: fetched `https://mr-informer.top/` and confirmed served HTML matches the latest generated content.

## Recommendations (not yet done)

- Consider a lightweight smoke test (even a plain Python script asserting `generate_mr_informer_article()`'s output has the required keys and no fabrication markers) that CI runs before the auto-commit, so a future bad edit fails loudly instead of silently shipping.
- If duplicate near-misses become a visible problem, loosen/adjust the duplicate check (e.g. fuzzy match or compare source URLs, which are now tracked, instead of only titles).
