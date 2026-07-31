// ==========================================================================
// MR. INFORMER BLOG - SUPABASE REAL-TIME CLOUD ADAPTER
// ==========================================================================

const SUPABASE_CONFIG = {
  url: window.ENV_SUPABASE_URL || "https://vtzquvzpyqzyhpjitjnl.supabase.co",
  anonKey: window.ENV_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0enF1dnpweXF6eWhwaml0am5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU1MDYzNDgsImV4cCI6MjEwMTA4MjM0OH0.WCaWp7Mccjm1ooXnz10fYTCLvFXJoD5Rp5sEF7Wj0Tg"
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

// Newsletter Subscriber CRM Cloud Sync
window.addSubscriberToSupabase = async function(email, source = "Website Popup") {
  if (!SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey) {
    return true;
  }
  try {
    const response = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/subscribers`, {
      method: "POST",
      headers: {
        "apikey": SUPABASE_CONFIG.anonKey,
        "Authorization": `Bearer ${SUPABASE_CONFIG.anonKey}`,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
      },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        source: source
      })
    });
    return response.ok || response.status === 409;
  } catch (err) {
    console.warn("⚠️ Failed to save subscriber to Supabase:", err);
    return false;
  }
};

window.fetchSubscribersFromSupabase = async function() {
  if (!SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey) {
    return [];
  }
  try {
    const response = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/subscribers?select=*&order=created_at.desc`, {
      headers: {
        "apikey": SUPABASE_CONFIG.anonKey,
        "Authorization": `Bearer ${SUPABASE_CONFIG.anonKey}`
      }
    });
    if (!response.ok) return [];
    return await response.json();
  } catch (err) {
    console.warn("⚠️ Failed to fetch subscribers from Supabase:", err);
    return [];
  }
};
