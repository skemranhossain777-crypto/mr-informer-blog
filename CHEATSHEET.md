# Mr. Informer Blog — Operator Cheat Sheet

Quick reference for running this site day-to-day. For how the code actually works, see `CLAUDE.md`. For the content-pipeline deep dive, see `PIPELINE_REPORT.md`.

## Where things live

| Thing | Where |
|---|---|
| Live site | https://mr-informer.top |
| Source of truth for articles | Supabase `articles` table (not the files in this repo) |
| RSS feed list + publish schedule | `news_workflow.py` (`RSS_FEEDS`) + `.github/workflows/rss_ingestion.yml` (cron) |
| Admin panel | `https://mr-informer.top/#admin` |
| Database dashboard | https://app.supabase.com → your project |
| Ad code / publisher ID | `ads.txt` + the `ca-pub-...` script tag in `index.html` |
| Hosting / DNS | GitHub Pages (repo Settings → Pages), DNS at your domain registrar |

## Checking if new articles are publishing

1. Go to the repo on GitHub → **Actions** tab.
2. Look for "Automated RSS Cloud Ingestion Workflow" runs — should fire every 3 hours automatically, plus once whenever code is pushed.
3. Green check = ran fine (note: a successful run doesn't always mean a new article was published — if there was no genuinely new story that cycle, it correctly publishes nothing).
4. To force one right now: Actions tab → select the workflow → "Run workflow" button.

## Logging into the admin panel

1. Go to `https://mr-informer.top/#admin`.
2. Log in with the email/password you created in Supabase (Authentication → Users). If you ever need to add a second admin, create their user in Supabase Authentication, then run this in the Supabase SQL Editor with their User UID:
   ```sql
   INSERT INTO public.admins (id, email) VALUES ('their-uid-here', 'their-email@example.com');
   ```
3. Forgot who's an admin? Check the `admins` table in Supabase's Table Editor.

## Checking AdSense status

Google AdSense dashboard → **Sites** (left sidebar). Two independent statuses:
- **Approval status**: "Requires review" → still being reviewed, no revenue yet. "Ready" → approved.
- **ads.txt status**: should read "Authorized"/found once Google re-crawls it (can lag up to ~24h behind an actual fix — check `https://mr-informer.top/ads.txt` directly if in doubt).

## Publishing an article manually (not via RSS)

Admin panel → CMS dashboard → **Articles** tab → **Publish Brief**. This writes straight to Supabase and shows up on the live site within the next scheduled ingestion cycle (which is also when it gets a proper indexable `/articles/<slug>/` page — there can be up to a ~3 hour lag between a manual CMS publish and it having its own crawlable page).

## If you (or an AI agent) need to push code changes

The automated workflow commits directly to `main` on its own schedule, so a local branch can go stale. Before pushing:
```bash
git fetch origin main
git log HEAD..origin/main --oneline   # anything listed? merge it first
```
If there are automated commits to merge, do **not** trust a plain `git merge` on `articles.json` blindly — after merging, re-pull fresh from Supabase and re-run `python generate_seo_pages.py` before committing, so the files match the live database exactly. Details in `CLAUDE.md`.

## Changing the domain

`SITE_DOMAIN` is templated from one place for generated content (`.env` locally, plus a `SITE_DOMAIN` repo variable in GitHub Actions settings), but the four legal pages (`about/`, `contact/`, `privacy/`, `terms/`), `robots.txt`, and `index.html` hardcode it directly since they're hand-written, not generated — all need updating together, then `python generate_seo_pages.py` to rebuild everything else.

## Red flags to never do

- Never click your own AdSense ads, even to "test" them — instant, usually permanent, ban risk.
- Never put `SUPABASE_SERVICE_ROLE_KEY` in any file that ships to the browser (only Python scripts should ever use it).
- Don't re-enable a "publish something even if nothing new was found" fallback in the content pipeline — that's the exact fabrication pattern that got removed for AdSense policy compliance.
