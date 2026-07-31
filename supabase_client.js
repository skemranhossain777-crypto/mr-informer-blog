// ==========================================================================
// MR. INFORMER BLOG - SUPABASE REAL-TIME CLOUD ADAPTER
// ==========================================================================

const SUPABASE_CONFIG = {
  url: window.ENV_SUPABASE_URL || "",
  anonKey: window.ENV_SUPABASE_ANON_KEY || ""
};

async function fetchArticlesFromSupabase() {
  if (!SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey) {
    console.log("ℹ️ Supabase credentials not set in window.ENV. Using local articles dataset.");
    return null;
  }

  try {
    const response = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/articles?select=*&order=created_at.desc`, {
      headers: {
        "apikey": SUPABASE_CONFIG.anonKey,
        "Authorization": `Bearer ${SUPABASE_CONFIG.anonKey}`
      }
    });

    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    
    const dbArticles = await response.json();
    
    // Map Supabase column names back to frontend article structure
    return dbArticles.map(a => ({
      id: a.id,
      title: a.title,
      category: a.category,
      readTime: a.read_time,
      date: a.date,
      author: a.author,
      featured: a.featured,
      image: a.image,
      tags: a.tags || [],
      summary: a.summary,
      claps: a.claps || 100,
      views: a.views || "1.2K",
      content: a.content,
      comments: a.comments || []
    }));
  } catch (err) {
    console.warn("⚠️ Failed to load articles from Supabase:", err);
    return null;
  }
}

// Global Cloud Sync Initializer
window.initCloudSupabaseSync = async function(onArticlesLoaded) {
  const cloudArticles = await fetchArticlesFromSupabase();
  if (cloudArticles && cloudArticles.length > 0) {
    window.ARTICLES_DATA = cloudArticles;
    if (typeof onArticlesLoaded === "function") {
      onArticlesLoaded(cloudArticles);
    }
  }
};
