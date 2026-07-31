-- ==========================================================================
-- MR. INFORMER BLOG - SUPABASE POSTGRESQL SCHEMA & FULL CRM DATABASE
-- Execute this SQL in your Supabase SQL Editor (https://app.supabase.com)
-- ==========================================================================

-- 1. Create Articles Table
CREATE TABLE IF NOT EXISTS public.articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Tech Pulse',
    read_time TEXT DEFAULT '4 min read',
    date TEXT NOT NULL,
    author JSONB DEFAULT '{"name": "Mr. Informer", "title": "Chief Investigative Tech Analyst", "avatar": "assets/author_avatar.jpg"}'::jsonb,
    featured BOOLEAN DEFAULT false,
    image TEXT NOT NULL,
    tags TEXT[] DEFAULT ARRAY['Tech Pulse', 'Live Scoop'],
    summary TEXT NOT NULL,
    claps INTEGER DEFAULT 100,
    views TEXT DEFAULT '1.2K',
    content TEXT NOT NULL,
    comments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

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

-- ==========================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================================================

ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whistleblower_tips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;

-- Allow Public Read Access for Articles
CREATE POLICY "Allow public read access to articles" 
ON public.articles FOR SELECT USING (true);

-- Allow Service Role Write Access for Ingestion Daemon & Admin CMS
CREATE POLICY "Allow service role write access to articles" 
ON public.articles FOR ALL USING (auth.role() = 'service_role');

-- Allow Anonymous Visitors to Subscribe to Newsletter
CREATE POLICY "Allow anonymous newsletter subscription" 
ON public.subscribers FOR INSERT WITH CHECK (true);

-- Allow Public/Service Role Read Access for Subscribers in CRM
CREATE POLICY "Allow read access to subscribers" 
ON public.subscribers FOR SELECT USING (true);

-- Allow Anonymous Whistleblowers to Insert Tips
CREATE POLICY "Allow anonymous tip submissions" 
ON public.whistleblower_tips FOR INSERT WITH CHECK (true);

-- Allow Public Read Access to Site Config
CREATE POLICY "Allow public read access to site_config" 
ON public.site_config FOR SELECT USING (true);
