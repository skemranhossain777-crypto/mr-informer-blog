-- ==========================================================================
-- MR. INFORMER BLOG - SUPABASE POSTGRESQL SCHEMA & FULL CRM DATABASE
-- Execute this SQL in your Supabase SQL Editor (https://app.supabase.com)
--
-- Safe to re-run: every statement is guarded with IF EXISTS / IF NOT EXISTS,
-- and policies are dropped and recreated so this file stays the single
-- source of truth for your schema.
-- ==========================================================================

-- 1. Create Articles Table
CREATE TABLE IF NOT EXISTS public.articles (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Tech Pulse',
    read_time TEXT DEFAULT '4 min read',
    date TEXT NOT NULL,
    author JSONB DEFAULT '{"name": "Mr. Informer", "title": "Chief Investigative Tech Analyst", "avatar": "assets/author_avatar.jpg"}'::jsonb,
    featured BOOLEAN DEFAULT false,
    image TEXT NOT NULL,
    tags TEXT[] DEFAULT ARRAY['Tech Pulse', 'Live Scoop'],
    summary TEXT NOT NULL,
    source_name TEXT,
    source_url TEXT,
    claps INTEGER DEFAULT 100,
    views TEXT DEFAULT '1.2K',
    content TEXT NOT NULL,
    comments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backfill columns for tables created by an older version of this schema
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS source_name TEXT;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS source_url TEXT;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'articles_slug_key'
    ) THEN
        ALTER TABLE public.articles ADD CONSTRAINT articles_slug_key UNIQUE (slug);
    END IF;
END $$;

-- Index for fast category & recency sorting
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON public.articles (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category ON public.articles (category);

-- 2. Create Newsletter Subscribers CRM Table
CREATE TABLE IF NOT EXISTS public.subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    source TEXT DEFAULT 'Website Popup',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscribers_created_at ON public.subscribers (created_at DESC);

-- 3. Create Whistleblower Submissions Table
CREATE TABLE IF NOT EXISTS public.whistleblower_tips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    date TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Site Configuration & Branding Table
CREATE TABLE IF NOT EXISTS public.site_config (
    id TEXT PRIMARY KEY DEFAULT 'global',
    branding JSONB NOT NULL,
    sections JSONB NOT NULL,
    automation JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Admin Allowlist
-- Rows here are the ONLY Supabase Auth users allowed to use the in-browser
-- admin CMS. This table is deliberately locked to service_role only — you
-- add yourself to it from the Supabase SQL Editor, never from the app.
--
-- One-time setup after running this file:
--   1. Supabase Dashboard -> Authentication -> Users -> Add User
--      (create yourself an email + password login)
--   2. Copy that user's UID, then run:
--      INSERT INTO public.admins (id, email) VALUES ('paste-uid-here', 'you@example.com');
CREATE TABLE IF NOT EXISTS public.admins (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================================================

ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whistleblower_tips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admins ENABLE ROW LEVEL SECURITY;

-- Helper: is the current request from a signed-in admin?
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.admins WHERE id = auth.uid()
    );
$$;

-- ---- articles ----
DROP POLICY IF EXISTS "Allow public read access to articles" ON public.articles;
CREATE POLICY "Allow public read access to articles"
ON public.articles FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow service role write access to articles" ON public.articles;
DROP POLICY IF EXISTS "Allow admin write access to articles" ON public.articles;
CREATE POLICY "Allow admin write access to articles"
ON public.articles FOR ALL USING (public.is_admin()) WITH CHECK (public.is_admin());
-- Note: the service_role key (used only by the Python ingestion scripts,
-- never shipped to the browser) bypasses RLS entirely and does not need
-- its own policy here.

-- ---- subscribers ----
-- SECURITY FIX: subscribers used to be world-readable via the public anon
-- key (USING (true)), which let anyone dump every subscriber's email from
-- the browser console. Reads are now admin-only; anonymous visitors can
-- still subscribe (insert), just never list the table.
DROP POLICY IF EXISTS "Allow anonymous newsletter subscription" ON public.subscribers;
CREATE POLICY "Allow anonymous newsletter subscription"
ON public.subscribers FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow read access to subscribers" ON public.subscribers;
DROP POLICY IF EXISTS "Allow admin read access to subscribers" ON public.subscribers;
CREATE POLICY "Allow admin read access to subscribers"
ON public.subscribers FOR SELECT USING (public.is_admin());

-- ---- whistleblower_tips ----
DROP POLICY IF EXISTS "Allow anonymous tip submissions" ON public.whistleblower_tips;
CREATE POLICY "Allow anonymous tip submissions"
ON public.whistleblower_tips FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow admin read access to tips" ON public.whistleblower_tips;
CREATE POLICY "Allow admin read access to tips"
ON public.whistleblower_tips FOR SELECT USING (public.is_admin());

-- ---- site_config ----
DROP POLICY IF EXISTS "Allow public read access to site_config" ON public.site_config;
CREATE POLICY "Allow public read access to site_config"
ON public.site_config FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow admin write access to site_config" ON public.site_config;
CREATE POLICY "Allow admin write access to site_config"
ON public.site_config FOR ALL USING (public.is_admin()) WITH CHECK (public.is_admin());

-- ---- admins ----
-- No policies for anon/authenticated roles at all: this table is only ever
-- touched by you via the SQL Editor (which runs as a superuser and bypasses
-- RLS), so it stays fully locked down from both the browser and the app.
