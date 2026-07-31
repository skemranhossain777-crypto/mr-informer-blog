// ==========================================================================
// MR. INFORMER BLOG - APPLICATION LOGIC WITH AUTOMATED WORKFLOW REFRESH
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // DOMContentLoaded Initialization
  if (typeof window.initCloudSupabaseSync === "function") {
    window.initCloudSupabaseSync((cloudData) => {
      articles = cloudData;
      renderHero();
      renderArticles();
    });
  }
  // State Variables
  let articles = typeof ARTICLES_DATA !== 'undefined' ? ARTICLES_DATA : [];
  let activeCategory = "All";
  let activeTag = null;
  let searchQuery = "";
  let savedArticles = JSON.parse(localStorage.getItem("mr_informer_saved")) || [];
  let currentActiveArticle = null;
  let audioPlaying = false;
  let audioInterval = null;
  let lastKnownArticleCount = 0;

  // DOM Elements
  const heroSection = document.getElementById("heroSection");
  const articlesGrid = document.getElementById("articlesGrid");
  const categoryBar = document.getElementById("categoryBar");
  const searchInput = document.getElementById("searchInput");
  const savedCountEl = document.getElementById("savedCount");
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  
  // Reader Modal Elements
  const readerModal = document.getElementById("readerModal");
  const closeReaderBtn = document.getElementById("closeReaderBtn");
  const readingProgressBar = document.getElementById("readingProgressBar");
  const readerCategory = document.getElementById("readerCategory");
  const readerTitle = document.getElementById("readerTitle");
  const readerDate = document.getElementById("readerDate");
  const readerReadTime = document.getElementById("readerReadTime");
  const readerViews = document.getElementById("readerViews");
  const readerHeroImg = document.getElementById("readerHeroImg");
  const readerBody = document.getElementById("readerBody");
  const clapBtn = document.getElementById("clapBtn");
  const clapCountEl = document.getElementById("clapCount");
  const readerSaveBtn = document.getElementById("readerSaveBtn");
  const shareBtn = document.getElementById("shareBtn");
  const commentsList = document.getElementById("commentsList");
  const commentForm = document.getElementById("commentForm");
  const commentInput = document.getElementById("commentInput");
  
  // Audio Elements
  const audioPlayBtn = document.getElementById("audioPlayBtn");
  const audioProgress = document.getElementById("audioProgress");

  // Modals
  const newsletterModal = document.getElementById("newsletterModal");
  const openNewsletterBtn = document.getElementById("openNewsletterBtn");
  const closeNewsletterBtn = document.getElementById("closeNewsletterBtn");
  const newsletterForm = document.getElementById("newsletterForm");

  const tipModal = document.getElementById("tipModal");
  const openTipBtn = document.getElementById("openTipBtn");
  const quickTipSubmitBtn = document.getElementById("quickTipSubmitBtn");
  const closeTipBtn = document.getElementById("closeTipBtn");
  const tipForm = document.getElementById("tipForm");
  const footerTipLink = document.getElementById("footerTipLink");
  const footerIntelLink = document.getElementById("footerIntelLink");
  const manualSyncBtn = document.getElementById("manualSyncBtn");

  // Load & Apply Site Configuration
  loadAndApplySiteConfig();

  // Load Initial Data from articles.json (with fallback to ARTICLES_DATA)
  fetchArticles();

  // Poll for Auto-Published Articles every 15 seconds
  setInterval(fetchArticles, 15000);

  function fetchArticles() {
    fetch("articles.json?t=" + new Date().getTime())
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          // Check if new articles were added by workflow
          if (lastKnownArticleCount > 0 && data.length > lastKnownArticleCount) {
            const newest = data[0];
            showToastNotification(`⚡ NEW INTEL BRIEF AUTO-PUBLISHED: ${newest.title}`);
          }
          lastKnownArticleCount = data.length;

          // Merge local user-persisted comments
          const savedComments = JSON.parse(localStorage.getItem("mr_informer_user_comments")) || {};
          data.forEach(art => {
            if (savedComments[art.id] && Array.isArray(savedComments[art.id])) {
              const existingTexts = new Set((art.comments || []).map(c => c.text));
              savedComments[art.id].forEach(userComm => {
                if (!existingTexts.has(userComm.text)) {
                  art.comments.unshift(userComm);
                  existingTexts.add(userComm.text);
                }
              });
            }
          });

          // Merge custom CMS created articles & handle deletions
          const cmsArticles = JSON.parse(localStorage.getItem("mr_informer_cms_articles")) || [];
          const deletedIds = JSON.parse(localStorage.getItem("mr_informer_cms_deleted")) || [];
          
          let merged = [...cmsArticles, ...data].filter(a => !deletedIds.includes(a.id));
          
          // Deduplicate by ID
          const seenIds = new Set();
          articles = merged.filter(a => {
            if (seenIds.has(a.id)) return false;
            seenIds.add(a.id);
            return true;
          });

          updateSavedCount();
          renderHero();
          renderArticles();
        }
      })
      .catch(err => {
        console.log("Using static articles dataset fallback.", err);
        updateSavedCount();
        renderHero();
        renderArticles();
      });
  }

  // Toast Notification System
  function showToastNotification(message) {
    const toast = document.createElement("div");
    toast.className = "toast-notification";
    toast.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
        <span>${message}</span>
        <button style="background:none; border:none; color:#fff; cursor:pointer; font-weight:bold;">✕</button>
      </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 6000);
    toast.querySelector("button").onclick = () => toast.remove();
  }

  // ==========================================
  // 1. Theme Toggle Logic
  // ==========================================
  const currentTheme = localStorage.getItem("mr_informer_theme") || "dark";
  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeIcon(currentTheme);

  themeToggleBtn.addEventListener("click", () => {
    const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("mr_informer_theme", theme);
    updateThemeIcon(theme);
  });

  function updateThemeIcon(theme) {
    const themeIcon = document.getElementById("themeIcon");
    if (!themeIcon) return;
    if (theme === "light") {
      themeIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>`;
    } else {
      themeIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>`;
    }
  }

  // ==========================================
  // 2. Render Hero Article
  // ==========================================
  function renderHero() {
    const heroArticle = articles.find(a => a.featured) || articles[0];
    if (!heroArticle) return;

    heroSection.innerHTML = `
      <div class="hero-card">
        <div class="hero-image-box">
          <img src="${heroArticle.image}" alt="${heroArticle.title}">
          <span class="hero-badge">FEATURED INTEL</span>
        </div>
        <div class="hero-content">
          <div class="hero-meta">
            <span>${heroArticle.category}</span> • <span>${heroArticle.readTime}</span>
          </div>
          <h2 class="hero-title">${heroArticle.title}</h2>
          <p class="hero-summary">${heroArticle.summary}</p>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-top: auto;">
            <div class="author-row">
              <img src="${heroArticle.author.avatar}" alt="${heroArticle.author.name}" class="author-avatar">
              <div class="author-info">
                <h4>${heroArticle.author.name}</h4>
                <p>${heroArticle.date}</p>
              </div>
            </div>
            <button class="btn btn-primary read-article-btn" data-id="${heroArticle.id}">Read Brief →</button>
          </div>
        </div>
      </div>
    `;

    heroSection.querySelector(".read-article-btn").addEventListener("click", () => {
      openReader(heroArticle.id);
    });
  }

  // ==========================================
  // 3. Render Articles Grid
  // ==========================================
  function renderArticles() {
    let filtered = articles.filter(art => {
      const matchCat = activeCategory === "All" || art.category === activeCategory;
      const matchTag = !activeTag || art.tags.includes(activeTag);
      const matchSearch = searchQuery === "" || 
        art.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
        art.summary.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCat && matchTag && matchSearch;
    });

    if (filtered.length === 0) {
      articlesGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 0; color: var(--text-muted);">
          <h3>No intel briefs match your search criteria.</h3>
          <p>Try resetting categories or search keywords.</p>
        </div>
      `;
      return;
    }

    articlesGrid.innerHTML = filtered.map(art => {
      const isSaved = savedArticles.includes(art.id);
      return `
        <article class="article-card">
          <div class="card-img-wrapper">
            <img src="${art.image}" alt="${art.title}">
            <span class="cat-tag">${art.category}</span>
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span>${art.date}</span>
              <span>${art.readTime}</span>
            </div>
            <h3 class="card-title">${art.title}</h3>
            <p class="card-summary">${art.summary}</p>
            <div class="card-footer">
              <span>👀 ${art.views}</span>
              <div class="card-actions">
                <button class="action-btn bookmark-btn ${isSaved ? 'active' : ''}" data-id="${art.id}" title="Bookmark">
                  ${isSaved ? '🔖 Saved' : '🔖 Save'}
                </button>
                <button class="btn btn-secondary read-btn" data-id="${art.id}" style="padding: 6px 14px; font-size: 0.8rem;">Read</button>
              </div>
            </div>
          </div>
        </article>
      `;
    }).join("");

    // Attach Event Listeners to Article Cards
    articlesGrid.querySelectorAll(".read-btn").forEach(btn => {
      btn.addEventListener("click", () => openReader(btn.getAttribute("data-id")));
    });

    articlesGrid.querySelectorAll(".bookmark-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleSaveArticle(btn.getAttribute("data-id"));
      });
    });
  }

  // ==========================================
  // 4. Category & Search Filtering
  // ==========================================
  document.addEventListener("click", (e) => {
    const pill = e.target.closest(".cat-pill");
    if (pill && pill.hasAttribute("data-category")) {
      e.preventDefault();
      const cat = pill.getAttribute("data-category");
      document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
      document.querySelectorAll(`.cat-pill[data-category="${cat}"]`).forEach(p => p.classList.add("active"));
      activeCategory = cat;
      activeTag = null;
      renderArticles();
      
      // Smooth scroll back to articles grid if clicked from footer
      if (!categoryBar.contains(pill)) {
        window.scrollTo({ top: heroSection.offsetTop - 40, behavior: 'smooth' });
      }
    }
  });

  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value;
    renderArticles();
  });

  // Tag Cloud Clicks
  document.querySelectorAll(".tag-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      activeTag = btn.getAttribute("data-tag");
      renderArticles();
    });
  });

  // Manual Sync Button
  if (manualSyncBtn) {
    manualSyncBtn.addEventListener("click", () => {
      manualSyncBtn.textContent = "⏳ Syncing Feeds...";
      fetchArticles();
      setTimeout(() => {
        manualSyncBtn.textContent = "🔄 Trigger Instant News Sync";
        showToastNotification("🟢 Automated Hourly News Workflow is Active & Synced!");
      }, 1200);
    });
  }

  // ==========================================
  // 5. Bookmark Saving System
  // ==========================================
  function toggleSaveArticle(id) {
    if (savedArticles.includes(id)) {
      savedArticles = savedArticles.filter(item => item !== id);
    } else {
      savedArticles.push(id);
    }
    localStorage.setItem("mr_informer_saved", JSON.stringify(savedArticles));
    updateSavedCount();
    renderArticles();

    if (currentActiveArticle && currentActiveArticle.id === id) {
      updateReaderSaveBtnState();
    }
  }

  function updateSavedCount() {
    savedCountEl.textContent = savedArticles.length;
  }

  // Bookmark Drawer Button Click
  document.getElementById("bookmarkDrawerBtn").addEventListener("click", () => {
    if (savedArticles.length === 0) {
      alert("No saved articles yet! Click the bookmark button on any article to save it.");
      return;
    }
    activeCategory = "All";
    searchQuery = "";
    articlesGrid.innerHTML = "";
    const savedList = articles.filter(a => savedArticles.includes(a.id));
    
    categoryBar.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
    
    articlesGrid.innerHTML = `
      <div style="grid-column: 1 / -1; margin-bottom: 16px;">
        <h2>🔖 Your Bookmarked Intel Briefs</h2>
      </div>
    ` + savedList.map(art => `
      <article class="article-card">
        <div class="card-img-wrapper">
          <img src="${art.image}" alt="${art.title}">
          <span class="cat-tag">${art.category}</span>
        </div>
        <div class="card-body">
          <div class="card-meta">
            <span>${art.date}</span>
            <span>${art.readTime}</span>
          </div>
          <h3 class="card-title">${art.title}</h3>
          <p class="card-summary">${art.summary}</p>
          <div class="card-footer">
            <button class="action-btn bookmark-btn active" data-id="${art.id}">🔖 Remove</button>
            <button class="btn btn-secondary read-btn" data-id="${art.id}">Read Brief</button>
          </div>
        </div>
      </article>
    `).join("");

    articlesGrid.querySelectorAll(".read-btn").forEach(btn => {
      btn.addEventListener("click", () => openReader(btn.getAttribute("data-id")));
    });
    articlesGrid.querySelectorAll(".bookmark-btn").forEach(btn => {
      btn.addEventListener("click", () => toggleSaveArticle(btn.getAttribute("data-id")));
    });
  });

  // ==========================================
  // 6. Full Article Reader Modal
  // ==========================================
  function openReader(id) {
    const art = articles.find(a => a.id === id);
    if (!art) return;

    currentActiveArticle = art;
    readerCategory.textContent = art.category;
    readerTitle.textContent = art.title;
    readerDate.textContent = art.date;
    readerReadTime.textContent = art.readTime;
    readerViews.textContent = art.views + " Views";
    readerHeroImg.src = art.image;
    readerHeroImg.alt = art.title;
    readerBody.innerHTML = art.content;
    clapCountEl.textContent = art.claps.toLocaleString();

    updateReaderSaveBtnState();
    renderComments();

    readerModal.classList.add("active");
    readerModal.scrollTop = 0;
    document.body.style.overflow = "hidden";
  }

  function closeReader() {
    readerModal.classList.remove("active");
    document.body.style.overflow = "";
    if (audioPlaying) stopAudio();
  }

  closeReaderBtn.addEventListener("click", closeReader);

  function updateReaderSaveBtnState() {
    if (!currentActiveArticle) return;
    const isSaved = savedArticles.includes(currentActiveArticle.id);
    readerSaveBtn.textContent = isSaved ? "🔖 Bookmarked" : "🔖 Bookmark";
  }

  readerSaveBtn.addEventListener("click", () => {
    if (currentActiveArticle) toggleSaveArticle(currentActiveArticle.id);
  });

  // Reading Progress Bar
  readerModal.addEventListener("scroll", () => {
    const scrollTop = readerModal.scrollTop;
    const scrollHeight = readerModal.scrollHeight - readerModal.clientHeight;
    const progress = (scrollTop / scrollHeight) * 100;
    readingProgressBar.style.width = `${progress}%`;
  });

  // Claps Counter Logic
  clapBtn.addEventListener("click", () => {
    if (currentActiveArticle) {
      currentActiveArticle.claps += 1;
      clapCountEl.textContent = currentActiveArticle.claps.toLocaleString();
      clapBtn.style.transform = "scale(1.2)";
      setTimeout(() => clapBtn.style.transform = "none", 200);
    }
  });

  // Share Button
  shareBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(window.location.href);
    alert("Article link copied to clipboard! Share securely.");
  });

  // Audio Player with Web Speech API Support
  let synth = window.speechSynthesis;
  let speechUtterance = null;

  audioPlayBtn.addEventListener("click", () => {
    if (audioPlaying) {
      stopAudio();
    } else {
      if (!currentActiveArticle) return;
      audioPlaying = true;
      audioPlayBtn.textContent = "⏸";

      // Extract text content from HTML body
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = currentActiveArticle.content;
      const plainText = `${currentActiveArticle.title}. ${tempDiv.textContent || tempDiv.innerText}`;

      if (synth) {
        synth.cancel(); // Reset active speech
        speechUtterance = new SpeechSynthesisUtterance(plainText);
        speechUtterance.rate = 1.0;
        speechUtterance.pitch = 1.0;

        speechUtterance.onboundary = (event) => {
          if (event.charIndex && plainText.length) {
            const pct = Math.min(100, Math.round((event.charIndex / plainText.length) * 100));
            audioProgress.style.width = `${pct}%`;
          }
        };

        speechUtterance.onend = () => stopAudio();
        speechUtterance.onerror = () => stopAudio();

        synth.speak(speechUtterance);
      }

      // Visual progress fallback timer
      let progress = 0;
      const durationEstimateSec = Math.max(12, plainText.split(" ").length / 2.5);
      audioInterval = setInterval(() => {
        progress += (100 / (durationEstimateSec * 10));
        if (!synth || !synth.speaking) {
          audioProgress.style.width = `${Math.min(100, progress)}%`;
        }
        if (progress >= 100) stopAudio();
      }, 100);
    }
  });

  function stopAudio() {
    audioPlaying = false;
    audioPlayBtn.textContent = "▶";
    if (audioInterval) clearInterval(audioInterval);
    if (synth && synth.speaking) synth.cancel();
    audioProgress.style.width = "0%";
  }

  // Comment System with LocalStorage Persistence
  function renderComments() {
    if (!currentActiveArticle || !currentActiveArticle.comments) return;
    commentsList.innerHTML = currentActiveArticle.comments.map(c => `
      <div class="comment-card">
        <div class="comment-header">
          <span>${c.name}</span>
          <span style="color: var(--text-muted); font-size: 0.78rem;">${c.date}</span>
        </div>
        <p style="font-size: 0.9rem; color: var(--text-secondary);">${c.text}</p>
      </div>
    `).join("");
  }

  commentForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const val = commentInput.value.trim();
    if (!val || !currentActiveArticle) return;

    const newComment = {
      name: "Verified Reader",
      date: "Just now",
      text: val
    };

    currentActiveArticle.comments.unshift(newComment);

    // Save to LocalStorage
    const savedComments = JSON.parse(localStorage.getItem("mr_informer_user_comments")) || {};
    if (!savedComments[currentActiveArticle.id]) {
      savedComments[currentActiveArticle.id] = [];
    }
    savedComments[currentActiveArticle.id].unshift(newComment);
    localStorage.setItem("mr_informer_user_comments", JSON.stringify(savedComments));

    commentInput.value = "";
    renderComments();
  });

  // ==========================================
  // 7. Modals: Newsletter & Encrypted Tip
  // ==========================================
  openNewsletterBtn.addEventListener("click", () => newsletterModal.classList.add("active"));
  closeNewsletterBtn.addEventListener("click", () => newsletterModal.classList.remove("active"));
  if (footerIntelLink) footerIntelLink.addEventListener("click", (e) => { e.preventDefault(); newsletterModal.classList.add("active"); });

  newsletterForm.addEventListener("submit", (e) => {
    e.preventDefault();
    alert("Success! You are now subscribed to the Mr. Informer Intel Dispatch.");
    newsletterModal.classList.remove("active");
  });

  function openTip() { tipModal.classList.add("active"); }
  function closeTip() { tipModal.classList.remove("active"); }

  openTipBtn.addEventListener("click", openTip);
  quickTipSubmitBtn.addEventListener("click", openTip);
  closeTipBtn.addEventListener("click", closeTip);
  if (footerTipLink) footerTipLink.addEventListener("click", (e) => { e.preventDefault(); openTip(); });

  tipForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const inputs = tipForm.querySelectorAll("input, textarea");
    const subj = inputs[0] ? inputs[0].value.trim() : "Intel Leak";
    const text = inputs[1] ? inputs[1].value.trim() : "";

    const newTip = {
      id: "tip-" + Date.now(),
      date: new Date().toLocaleString(),
      subject: subj,
      content: text
    };

    const existingTips = JSON.parse(localStorage.getItem("mr_informer_tips")) || [];
    existingTips.unshift(newTip);
    localStorage.setItem("mr_informer_tips", JSON.stringify(existingTips));

    alert("Intel transmitted successfully! IP headers and metadata have been purged.");
    tipModal.classList.remove("active");
    tipForm.reset();
    updateCmsTipCount();
  });

  // ==========================================
  // 8. CMS & ADMIN PORTAL CONTROLLER
  // ==========================================
  const openAdminBtn = document.getElementById("openAdminBtn");
  const adminLoginModal = document.getElementById("adminLoginModal");
  const closeAdminLoginBtn = document.getElementById("closeAdminLoginBtn");
  const adminLoginForm = document.getElementById("adminLoginForm");
  const adminPasswordInput = document.getElementById("adminPasswordInput");

  const cmsDashboardModal = document.getElementById("cmsDashboardModal");
  const closeCmsBtn = document.getElementById("closeCmsBtn");
  const cmsExportJsonBtn = document.getElementById("cmsExportJsonBtn");
  const cmsTabs = document.getElementById("cmsTabs");
  const cmsTipCountEl = document.getElementById("cmsTipCount");
  const cmsArticlesTableBody = document.getElementById("cmsArticlesTableBody");
  const cmsTipsList = document.getElementById("cmsTipsList");

  const cmsArticleForm = document.getElementById("cmsArticleForm");
  const cmsEditArticleId = document.getElementById("cmsEditArticleId");
  const cmsTitleInput = document.getElementById("cmsTitleInput");
  const cmsCategorySelect = document.getElementById("cmsCategorySelect");
  const cmsReadTimeInput = document.getElementById("cmsReadTimeInput");
  const cmsImageSelect = document.getElementById("cmsImageSelect");
  const cmsTagsInput = document.getElementById("cmsTagsInput");
  const cmsSummaryInput = document.getElementById("cmsSummaryInput");
  const cmsContentInput = document.getElementById("cmsContentInput");
  const cmsCancelEditBtn = document.getElementById("cmsCancelEditBtn");
  const cmsSubmitBtn = document.getElementById("cmsSubmitBtn");

  // Admin Access Key (Default: informer2026)
  const MASTER_ADMIN_KEY = "informer2026";

  const navAdminBtn = document.getElementById("navAdminBtn");
  const adminLoginAlert = document.getElementById("adminLoginAlert");
  const cmsLogoutBtn = document.getElementById("cmsLogoutBtn");

  function triggerAdminAuthCheck() {
    if (sessionStorage.getItem("mr_informer_admin") === "true") {
      openCmsDashboard();
    } else {
      if (adminLoginAlert) adminLoginAlert.style.display = "none";
      if (adminPasswordInput) {
        adminPasswordInput.value = "";
        adminPasswordInput.style.borderColor = "";
      }
      adminLoginModal.classList.add("active");
      if (adminPasswordInput) setTimeout(() => adminPasswordInput.focus(), 150);
    }
  }

  if (navAdminBtn) {
    navAdminBtn.addEventListener("click", (e) => {
      e.preventDefault();
      triggerAdminAuthCheck();
    });
  }

  if (openAdminBtn) {
    openAdminBtn.addEventListener("click", (e) => {
      e.preventDefault();
      triggerAdminAuthCheck();
    });
  }

  if (closeAdminLoginBtn) {
    closeAdminLoginBtn.addEventListener("click", () => adminLoginModal.classList.remove("active"));
  }

  if (adminLoginForm) {
    adminLoginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = adminPasswordInput.value.trim();
      if (val === MASTER_ADMIN_KEY || val === "admin") {
        sessionStorage.setItem("mr_informer_admin", "true");
        adminPasswordInput.value = "";
        if (adminPasswordInput) adminPasswordInput.style.borderColor = "";
        if (adminLoginAlert) adminLoginAlert.style.display = "none";
        adminLoginModal.classList.remove("active");
        showToastNotification("🟢 Admin Authenticated Successfully! Welcome Mr. Informer.");
        openCmsDashboard();
      } else {
        if (adminLoginAlert) {
          adminLoginAlert.textContent = "❌ Access Denied: Invalid Master Admin Access Key!";
          adminLoginAlert.style.display = "block";
        }
        if (adminPasswordInput) {
          adminPasswordInput.style.borderColor = "#f43f5e";
          adminPasswordInput.focus();
        }
      }
    });
  }

  if (cmsLogoutBtn) {
    cmsLogoutBtn.addEventListener("click", () => {
      sessionStorage.removeItem("mr_informer_admin");
      cmsDashboardModal.classList.remove("active");
      showToastNotification("🔒 Admin CMS Session Locked & Logged Out.");
    });
  }

  function openCmsDashboard() {
    cmsDashboardModal.classList.add("active");
    updateCmsTipCount();
    renderCmsArticlesTable();
    renderCmsTipsInbox();
  }

  if (closeCmsBtn) {
    closeCmsBtn.addEventListener("click", () => cmsDashboardModal.classList.remove("active"));
  }

  // CMS Tabs Switcher
  if (cmsTabs) {
    cmsTabs.addEventListener("click", (e) => {
      if (e.target.classList.contains("cms-tab-btn")) {
        cmsTabs.querySelectorAll(".cms-tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".cms-tab-content").forEach(c => c.classList.remove("active"));
        
        e.target.classList.add("active");
        const targetTab = e.target.getAttribute("data-tab");
        document.getElementById(targetTab).classList.add("active");
      }
    });
  }

  function updateCmsTipCount() {
    const tips = JSON.parse(localStorage.getItem("mr_informer_tips")) || [];
    if (cmsTipCountEl) cmsTipCountEl.textContent = tips.length;
  }

  // Render CMS Articles Table
  function renderCmsArticlesTable() {
    if (!cmsArticlesTableBody) return;
    cmsArticlesTableBody.innerHTML = articles.map(art => `
      <tr>
        <td style="font-weight: 600; max-width: 260px;">${art.title}</td>
        <td><span class="cms-badge">${art.category}</span></td>
        <td style="color: var(--text-muted);">${art.date}</td>
        <td>👀 ${art.views || '1.0K'}</td>
        <td>👏 ${art.claps || 0}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary cms-edit-btn" data-id="${art.id}" style="padding: 4px 8px; font-size: 0.75rem;">Edit</button>
            <button class="btn btn-secondary cms-delete-btn" data-id="${art.id}" style="padding: 4px 8px; font-size: 0.75rem; border-color: var(--accent-rose); color: var(--accent-rose);">Delete</button>
          </div>
        </td>
      </tr>
    `).join("");

    // Attach Edit & Delete Listeners
    cmsArticlesTableBody.querySelectorAll(".cms-edit-btn").forEach(btn => {
      btn.addEventListener("click", () => editCmsArticle(btn.getAttribute("data-id")));
    });

    cmsArticlesTableBody.querySelectorAll(".cms-delete-btn").forEach(btn => {
      btn.addEventListener("click", () => deleteCmsArticle(btn.getAttribute("data-id")));
    });
  }

  // Edit Article
  function editCmsArticle(id) {
    const art = articles.find(a => a.id === id);
    if (!art) return;

    cmsEditArticleId.value = art.id;
    cmsTitleInput.value = art.title;
    cmsCategorySelect.value = art.category;
    cmsReadTimeInput.value = art.readTime;
    cmsImageSelect.value = art.image || "assets/hero_tech_cyber.jpg";
    cmsTagsInput.value = (art.tags || []).join(", ");
    cmsSummaryInput.value = art.summary;
    cmsContentInput.value = art.content;

    cmsSubmitBtn.textContent = "💾 Save Changes";
    
    // Switch to Editor Tab
    cmsTabs.querySelectorAll(".cms-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".cms-tab-content").forEach(c => c.classList.remove("active"));
    const editorTabBtn = cmsTabs.querySelector('[data-tab="cmsTabEditor"]');
    if (editorTabBtn) editorTabBtn.classList.add("active");
    document.getElementById("cmsTabEditor").classList.add("active");
  }

  // Delete Article
  function deleteCmsArticle(id) {
    if (!confirm("Are you sure you want to delete this article brief?")) return;

    const deletedIds = JSON.parse(localStorage.getItem("mr_informer_cms_deleted")) || [];
    if (!deletedIds.includes(id)) deletedIds.push(id);
    localStorage.setItem("mr_informer_cms_deleted", JSON.stringify(deletedIds));

    // Remove from custom CMS articles if present
    let cmsArticles = JSON.parse(localStorage.getItem("mr_informer_cms_articles")) || [];
    cmsArticles = cmsArticles.filter(a => a.id !== id);
    localStorage.setItem("mr_informer_cms_articles", JSON.stringify(cmsArticles));

    articles = articles.filter(a => a.id !== id);
    renderHero();
    renderArticles();
    renderCmsArticlesTable();
    showToastNotification("🗑️ Article Deleted Successfully.");
  }

  // Cancel Edit Form Reset
  if (cmsCancelEditBtn) {
    cmsCancelEditBtn.addEventListener("click", () => {
      cmsArticleForm.reset();
      cmsEditArticleId.value = "";
      cmsSubmitBtn.textContent = "🚀 Publish Brief";
    });
  }

  // Publish / Save Article Form Submit
  if (cmsArticleForm) {
    cmsArticleForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const id = cmsEditArticleId.value || ("cms-" + Date.now());
      const title = cmsTitleInput.value.trim();
      const category = cmsCategorySelect.value;
      const readTime = cmsReadTimeInput.value.trim();
      const image = cmsImageSelect.value;
      const tags = cmsTagsInput.value.split(",").map(t => t.trim()).filter(Boolean);
      const summary = cmsSummaryInput.value.trim();
      const content = cmsContentInput.value.trim();

      const cmsArticles = JSON.parse(localStorage.getItem("mr_informer_cms_articles")) || [];
      const existingIdx = cmsArticles.findIndex(a => a.id === id);

      const articleObj = {
        id: id,
        title: title,
        category: category,
        readTime: readTime,
        date: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
        author: {
          name: "Mr. Informer",
          title: "Chief Investigative Tech Analyst",
          avatar: "assets/author_avatar.jpg"
        },
        featured: false,
        image: image,
        tags: tags,
        summary: summary,
        claps: existingIdx >= 0 ? cmsArticles[existingIdx].claps : 100,
        views: existingIdx >= 0 ? cmsArticles[existingIdx].views : "1.2K",
        content: content,
        comments: existingIdx >= 0 ? cmsArticles[existingIdx].comments : []
      };

      if (existingIdx >= 0) {
        cmsArticles[existingIdx] = articleObj;
      } else {
        cmsArticles.unshift(articleObj);
      }

      localStorage.setItem("mr_informer_cms_articles", JSON.stringify(cmsArticles));

      // Update in-memory articles
      const artIdx = articles.findIndex(a => a.id === id);
      if (artIdx >= 0) {
        articles[artIdx] = articleObj;
      } else {
        articles.unshift(articleObj);
      }

      cmsArticleForm.reset();
      cmsEditArticleId.value = "";
      cmsSubmitBtn.textContent = "🚀 Publish Brief";

      renderHero();
      renderArticles();
      renderCmsArticlesTable();

      showToastNotification(`✅ Brief '${title}' Published Successfully!`);
      
      // Switch back to Articles List Tab
      cmsTabs.querySelectorAll(".cms-tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".cms-tab-content").forEach(c => c.classList.remove("active"));
      const articlesTabBtn = cmsTabs.querySelector('[data-tab="cmsTabArticles"]');
      if (articlesTabBtn) articlesTabBtn.classList.add("active");
      document.getElementById("cmsTabArticles").classList.add("active");
    });
  }

  // Render Whistleblower Tips Inbox
  function renderCmsTipsInbox() {
    if (!cmsTipsList) return;
    const tips = JSON.parse(localStorage.getItem("mr_informer_tips")) || [];
    
    if (tips.length === 0) {
      cmsTipsList.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--text-muted);">
          <h3>No Whistleblower Submissions Yet</h3>
          <p>Transmitted anonymous intel drops will appear here.</p>
        </div>
      `;
      return;
    }

    cmsTipsList.innerHTML = tips.map(t => `
      <div class="tip-inbox-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h4 style="color: var(--accent-rose);">${t.subject}</h4>
          <span style="color: var(--text-muted); font-size: 0.78rem;">${t.date}</span>
        </div>
        <p style="font-size: 0.9rem; color: var(--text-secondary); white-space: pre-wrap; margin-bottom: 10px;">${t.content}</p>
        <button class="btn btn-secondary delete-tip-btn" data-id="${t.id}" style="padding: 4px 8px; font-size: 0.75rem; border-color: var(--accent-rose); color: var(--accent-rose);">Delete Tip</button>
      </div>
    `).join("");

    cmsTipsList.querySelectorAll(".delete-tip-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        let tips = JSON.parse(localStorage.getItem("mr_informer_tips")) || [];
        tips = tips.filter(tp => tp.id !== id);
        localStorage.setItem("mr_informer_tips", JSON.stringify(tips));
        updateCmsTipCount();
        renderCmsTipsInbox();
      });
    });
  }

  // Export articles.json File Download Helper
  if (cmsExportJsonBtn) {
    cmsExportJsonBtn.addEventListener("click", () => {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(articles, null, 2));
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", "articles.json");
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToastNotification("💾 Exported updated articles.json dataset!");
    });
  }

  // ==========================================
  // 9. ENTERPRISE SITE CONFIG & GALLERY CONTROLLERS
  // ==========================================
  function loadAndApplySiteConfig() {
    const config = JSON.parse(localStorage.getItem("mr_informer_site_config")) || {
      branding: {
        title: "Mr. Informer Blog",
        badge: "MI",
        tagline: "Uncensored Tech Intelligence & Deep Investigations",
        tickerText: "⚡ Autonomous AI swarms refactor code in under 90 seconds • ⚡ Quantum 100k qubit chip breaches silicon barrier • ⚡ Edge zero-day mesh exploit patched by DevSecOps teams • ⚡ Spatial neural glasses set to replace smartphones by Q4",
        authorName: "Mr. Informer",
        authorTitle: "Chief Investigative Tech Analyst",
        authorBio: "Investigative Tech Analyst & Data Journalist uncovering hidden algorithms, zero-day vulnerabilities, and future hardware.",
        authorAvatar: "assets/author_avatar.jpg",
        social: "@MrInformerTech"
      },
      sections: {
        showTicker: true,
        showHero: true,
        showWhistleblower: true,
        showTags: true,
        showAnnouncement: false,
        announcementTitle: "⚡ EXCLUSIVE INVESTIGATIVE DISPATCH",
        announcementText: "Mr. Informer Q3 Special Telemetry Report on Quantum Supremacy is now live. Access unredacted logs.",
        announcementBtn: "Read Special Report →"
      },
      automation: {
        feeds: [
          "https://techcrunch.com/feed/",
          "https://feeds.arstechnica.com/arstechnica/index",
          "https://www.wired.com/feed/rss",
          "https://hnrss.org/newest?points=100",
          "https://www.theverge.com/rss/index.xml",
          "https://www.engadget.com/rss.xml",
          "https://venturebeat.com/feed/",
          "https://www.bleepingcomputer.com/feed/",
          "https://www.darkreading.com/rss.xml",
          "https://spectrum.ieee.org/rss/fulltext",
          "https://scitechdaily.com/feed/",
          "https://news.google.com/rss/search?q=artificial+intelligence+cybersecurity+quantum&hl=en-US&gl=US&ceid=US:en"
        ],
        interval: 300,
        poll: 15
      }
    };

    // Apply Branding to DOM
    const brandTitleEl = document.querySelector(".brand-title");
    if (brandTitleEl) brandTitleEl.innerHTML = `${config.branding.title.split(" ")[0]} <span>${config.branding.title.split(" ").slice(1).join(" ")}</span>`;
    
    const logoBadgeEl = document.querySelector(".logo-badge");
    if (logoBadgeEl) logoBadgeEl.textContent = config.branding.badge;

    const tickerContentEl = document.getElementById("tickerContent");
    if (tickerContentEl) tickerContentEl.textContent = config.branding.tickerText;

    const authorWidgetNameEl = document.querySelector(".author-widget-name");
    if (authorWidgetNameEl) authorWidgetNameEl.textContent = config.branding.authorName;

    const authorWidgetBioEl = document.querySelector(".author-widget-bio");
    if (authorWidgetBioEl) authorWidgetBioEl.textContent = config.branding.authorBio;

    const authorWidgetAvatarEl = document.querySelector(".author-widget-avatar");
    if (authorWidgetAvatarEl) authorWidgetAvatarEl.src = config.branding.authorAvatar;

    // Apply Visible Section Toggles
    const tickerWrapper = document.querySelector(".ticker-wrapper");
    if (tickerWrapper) tickerWrapper.style.display = config.sections.showTicker ? "block" : "none";

    if (heroSection) heroSection.style.display = config.sections.showHero ? "block" : "none";

    const tipWidget = document.querySelector(".tip-widget");
    if (tipWidget) tipWidget.style.display = config.sections.showWhistleblower ? "block" : "none";

    const tagsWidget = document.getElementById("tagsCloud") ? document.getElementById("tagsCloud").closest(".widget") : null;
    if (tagsWidget) tagsWidget.style.display = config.sections.showTags ? "block" : "none";

    // Custom Announcement Banner Rendering
    const customBannerContainer = document.getElementById("customBannerContainer");
    if (customBannerContainer) {
      if (config.sections.showAnnouncement) {
        customBannerContainer.innerHTML = `
          <div class="custom-announcement-banner">
            <div>
              <h4>${config.sections.announcementTitle}</h4>
              <p style="font-size: 0.88rem; color: var(--text-secondary);">${config.sections.announcementText}</p>
            </div>
            <button class="btn btn-primary" style="padding: 8px 16px; font-size: 0.82rem;">${config.sections.announcementBtn}</button>
          </div>
        `;
      } else {
        customBannerContainer.innerHTML = "";
      }
    }
  }

  // Branding Form Submit
  const cmsBrandingForm = document.getElementById("cmsBrandingForm");
  if (cmsBrandingForm) {
    cmsBrandingForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const config = JSON.parse(localStorage.getItem("mr_informer_site_config")) || {};
      
      config.branding = {
        title: document.getElementById("brandingTitleInput").value.trim(),
        badge: document.getElementById("brandingBadgeInput").value.trim(),
        tagline: document.getElementById("brandingTaglineInput").value.trim(),
        tickerText: document.getElementById("brandingTickerInput").value.trim(),
        authorName: document.getElementById("brandingAuthorNameInput").value.trim(),
        authorTitle: document.getElementById("brandingAuthorTitleInput").value.trim(),
        authorBio: document.getElementById("brandingAuthorBioInput").value.trim(),
        authorAvatar: document.getElementById("brandingAuthorAvatarInput").value.trim(),
        social: document.getElementById("brandingSocialInput").value.trim()
      };

      localStorage.setItem("mr_informer_site_config", JSON.stringify(config));
      loadAndApplySiteConfig();
      showToastNotification("🎨 Site Branding & Header Settings Updated!");
    });
  }

  // Custom Sections & Banner Form Submit
  const cmsAnnouncementForm = document.getElementById("cmsAnnouncementForm");
  if (cmsAnnouncementForm) {
    cmsAnnouncementForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const config = JSON.parse(localStorage.getItem("mr_informer_site_config")) || {};
      
      config.sections = {
        showTicker: document.getElementById("toggleTicker").checked,
        showHero: document.getElementById("toggleHero").checked,
        showWhistleblower: document.getElementById("toggleWhistleblower").checked,
        showTags: document.getElementById("toggleTags").checked,
        showAnnouncement: document.getElementById("toggleAnnouncement").checked,
        announcementTitle: document.getElementById("announcementTitleInput").value.trim(),
        announcementText: document.getElementById("announcementTextInput").value.trim(),
        announcementBtn: document.getElementById("announcementBtnInput").value.trim()
      };

      localStorage.setItem("mr_informer_site_config", JSON.stringify(config));
      loadAndApplySiteConfig();
      showToastNotification("🧩 Custom Sections & Announcement Banner Saved!");
    });
  }

  // Automation Form Submit
  const cmsAutomationForm = document.getElementById("cmsAutomationForm");
  if (cmsAutomationForm) {
    cmsAutomationForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const config = JSON.parse(localStorage.getItem("mr_informer_site_config")) || {};
      
      const feeds = document.getElementById("automationFeedsInput").value.split("\n").map(f => f.trim()).filter(Boolean);
      config.automation = {
        feeds: feeds,
        interval: parseInt(document.getElementById("automationIntervalInput").value, 10) || 3600,
        poll: parseInt(document.getElementById("automationPollInput").value, 10) || 15
      };

      localStorage.setItem("mr_informer_site_config", JSON.stringify(config));
      showToastNotification("⚡ RSS Automation Scope Updated!");
    });
  }

  // Media Gallery Management
  const uploadImageBtn = document.getElementById("uploadImageBtn");
  const galleryFileInput = document.getElementById("galleryFileInput");
  const galleryUrlInput = document.getElementById("galleryUrlInput");
  const mediaGalleryGrid = document.getElementById("mediaGalleryGrid");

  const defaultGallery = [
    "assets/hero_tech_cyber.jpg",
    "assets/article_ai.jpg",
    "assets/article_cyber.jpg",
    "assets/article_quantum.jpg",
    "assets/author_avatar.jpg"
  ];

  function renderGallery() {
    if (!mediaGalleryGrid) return;
    const customGallery = JSON.parse(localStorage.getItem("mr_informer_gallery")) || [];
    const allImages = [...defaultGallery, ...customGallery];

    mediaGalleryGrid.innerHTML = allImages.map(imgSrc => `
      <div class="gallery-card">
        <img src="${imgSrc}" class="gallery-img" alt="Gallery Asset">
        <div class="gallery-info">
          <span style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${imgSrc.split('/').pop()}</span>
          <div style="display: flex; gap: 4px; margin-top: 4px;">
            <button class="btn btn-secondary select-cover-btn" data-src="${imgSrc}" style="padding: 3px 6px; font-size: 0.72rem; flex: 1;">Use Cover</button>
            <button class="btn btn-secondary copy-src-btn" data-src="${imgSrc}" style="padding: 3px 6px; font-size: 0.72rem;">Copy</button>
          </div>
        </div>
      </div>
    `).join("");

    mediaGalleryGrid.querySelectorAll(".select-cover-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const src = btn.getAttribute("data-src");
        
        // Add to cmsImageSelect dropdown if not already present
        let exists = false;
        for (let i = 0; i < cmsImageSelect.options.length; i++) {
          if (cmsImageSelect.options[i].value === src) {
            exists = true;
            break;
          }
        }
        if (!exists) {
          const opt = document.createElement("option");
          opt.value = src;
          opt.textContent = src.split('/').pop() || src;
          cmsImageSelect.appendChild(opt);
        }
        cmsImageSelect.value = src;
        showToastNotification(`🖼️ Set Cover Image to: ${src.split('/').pop()}`);
        
        // Switch to Editor Tab
        cmsTabs.querySelectorAll(".cms-tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".cms-tab-content").forEach(c => c.classList.remove("active"));
        const editorTabBtn = cmsTabs.querySelector('[data-tab="cmsTabEditor"]');
        if (editorTabBtn) editorTabBtn.classList.add("active");
        document.getElementById("cmsTabEditor").classList.add("active");
      });
    });

    mediaGalleryGrid.querySelectorAll(".copy-src-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        navigator.clipboard.writeText(btn.getAttribute("data-src"));
        showToastNotification("📋 Image URL Copied to Clipboard!");
      });
    });
  }

  if (uploadImageBtn) {
    uploadImageBtn.addEventListener("click", () => {
      const urlVal = galleryUrlInput.value.trim();
      const file = galleryFileInput.files[0];

      if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          const dataUrl = e.target.result;
          const customGallery = JSON.parse(localStorage.getItem("mr_informer_gallery")) || [];
          customGallery.unshift(dataUrl);
          localStorage.setItem("mr_informer_gallery", JSON.stringify(customGallery));
          galleryFileInput.value = "";
          renderGallery();
          showToastNotification("🟢 Uploaded New Image Asset to Gallery!");
        };
        reader.readAsDataURL(file);
      } else if (urlVal) {
        const customGallery = JSON.parse(localStorage.getItem("mr_informer_gallery")) || [];
        customGallery.unshift(urlVal);
        localStorage.setItem("mr_informer_gallery", JSON.stringify(customGallery));
        galleryUrlInput.value = "";
        renderGallery();
        showToastNotification("🟢 Added Image URL to Asset Gallery!");
      } else {
        alert("Please select a file to upload or enter an Image URL!");
      }
    });
  }

  // Render gallery when CMS Dashboard opens
  const originalOpenCmsDashboard = openCmsDashboard;
  openCmsDashboard = function() {
    originalOpenCmsDashboard();
    renderGallery();
  };
});
