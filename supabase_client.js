// ==========================================================================
// MR. INFORMER BLOG - SUPABASE REAL-TIME CLOUD ADAPTER
// ==========================================================================

const SUPABASE_CONFIG = {
  url: window.ENV_SUPABASE_URL || "https://vtzquvzpyqzyhpjitjnl.supabase.co",
  anonKey: window.ENV_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0enF1dnpweXF6eWhwaml0am5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU1MDYzNDgsImV4cCI6MjEwMTA4MjM0OH0.WCaWp7Mccjm1ooXnz10fYTCLvFXJoD5Rp5sEF7Wj0Tg"
};

// ==========================================================================
// REAL ADMIN AUTHENTICATION (Supabase Auth / GoTrue)
//
// Replaces the old hardcoded username/password that used to live in app.js.
// The admin panel is only as secure as the RLS policies in supabase_schema.sql
// (see the `admins` table + `is_admin()` policies) — this just gets a real,
// server-verified session token to send along with those requests.
// ==========================================================================

const ADMIN_SESSION_KEY = "mi_admin_session";

function getAdminSession() {
  try {
    const raw = localStorage.getItem(ADMIN_SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    if (!session.access_token || !session.expires_at) return null;
    if (Date.now() >= session.expires_at) {
      localStorage.removeItem(ADMIN_SESSION_KEY);
      return null;
    }
    return session;
  } catch (e) {
    return null;
  }
}

function storeAdminSession(authResponse) {
  const session = {
    access_token: authResponse.access_token,
    refresh_token: authResponse.refresh_token,
    expires_at: Date.now() + (authResponse.expires_in || 3600) * 1000,
    user: authResponse.user ? { id: authResponse.user.id, email: authResponse.user.email } : null
  };
  localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(session));
  return session;
}

window.supabaseAdminSignIn = async function(email, password) {
  const response = await fetch(`${SUPABASE_CONFIG.url}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: {
      "apikey": SUPABASE_CONFIG.anonKey,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error_description || data.msg || "Invalid email or password.");
  }
  return storeAdminSession(data);
};

window.supabaseAdminSignOut = async function() {
  const session = getAdminSession();
  localStorage.removeItem(ADMIN_SESSION_KEY);
  if (!session) return;
  try {
    await fetch(`${SUPABASE_CONFIG.url}/auth/v1/logout`, {
      method: "POST",
      headers: {
        "apikey": SUPABASE_CONFIG.anonKey,
        "Authorization": `Bearer ${session.access_token}`
      }
    });
  } catch (e) {
    // Best-effort server-side revoke; local session is already cleared.
  }
};

window.getAdminSession = getAdminSession;

function adminAuthHeaders() {
  const session = getAdminSession();
  return {
    "apikey": SUPABASE_CONFIG.anonKey,
    "Authorization": `Bearer ${session ? session.access_token : SUPABASE_CONFIG.anonKey}`
  };
}

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
    if (!Array.isArray(dbArticles)) return null;
    
    // Map Supabase column names back to frontend article structure safely
    return dbArticles.map(a => {
      let authorObj = { name: "Mr. Informer", title: "Chief Investigative Tech Analyst", avatar: "assets/author_avatar.jpg" };
      if (a.author) {
        if (typeof a.author === "string") {
          try { authorObj = JSON.parse(a.author); } catch(e) { authorObj = { name: a.author, title: "Investigative Tech Analyst", avatar: "assets/author_avatar.jpg" }; }
        } else if (typeof a.author === "object" && a.author !== null) {
          authorObj = { ...authorObj, ...a.author };
        }
      }
      return {
        id: a.id || `art-${Math.random()}`,
        slug: a.slug || a.id || `art-${Math.random()}`,
        title: a.title || "Untitled Intel Brief",
        category: a.category || "Tech Pulse",
        readTime: a.read_time || "4 min read",
        date: a.date || "Just now",
        author: authorObj,
        featured: Boolean(a.featured),
        image: a.image || "assets/hero_tech_cyber.jpg",
        tags: Array.isArray(a.tags) ? a.tags : ["Tech Pulse", "Live Scoop"],
        summary: a.summary || "",
        sourceName: a.source_name || "",
        sourceUrl: a.source_url || "",
        claps: a.claps || 100,
        views: a.views || "1.2K",
        content: a.content || "",
        comments: Array.isArray(a.comments) ? a.comments : []
      };
    });
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
  // Requires an admin session — the subscribers table denies anonymous
  // reads at the RLS level (see supabase_schema.sql), so this will come
  // back empty/403 for anyone who isn't signed in as an admin.
  if (!getAdminSession()) return [];
  try {
    const response = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/subscribers?select=*&order=created_at.desc`, {
      headers: adminAuthHeaders()
    });
    if (!response.ok) return [];
    return await response.json();
  } catch (err) {
    console.warn("⚠️ Failed to fetch subscribers from Supabase:", err);
    return [];
  }
};

// Global Article Cloud Publisher
window.addArticleToSupabase = async function(article) {
  if (!SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey) {
    return false;
  }
  try {
    const payload = {
      id: article.id,
      slug: article.slug || article.id,
      title: article.title,
      category: article.category || "Tech Pulse",
      read_time: article.readTime || "4 min read",
      date: article.date,
      author: article.author || { name: "Mr. Informer", title: "Chief Investigative Tech Analyst", avatar: "assets/author_avatar.jpg" },
      featured: Boolean(article.featured),
      image: article.image || "assets/hero_tech_cyber.jpg",
      tags: article.tags || ["Live Scoop"],
      summary: article.summary,
      source_name: article.sourceName || null,
      source_url: article.sourceUrl || null,
      claps: article.claps || 100,
      views: article.views || "1.2K",
      content: article.content,
      comments: article.comments || []
    };

    const response = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/articles`, {
      method: "POST",
      headers: {
        ...adminAuthHeaders(),
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
      },
      body: JSON.stringify(payload)
    });

    return response.ok || response.status === 201;
  } catch (err) {
    console.warn("⚠️ Failed to publish article to Supabase Cloud:", err);
    return false;
  }
};
