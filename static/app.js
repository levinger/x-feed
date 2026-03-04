const state = {
  keyword: null,
  offset: 0,
  hasMore: false,
  loading: false,
  keywordIds: {},   // keyword string → id
};

// ── Feed ──────────────────────────────────────────────────────────────

async function loadFeed(reset = true) {
  if (state.loading) return;
  state.loading = true;

  const btn = document.getElementById("refresh-btn");
  btn.classList.add("spinning");

  try {
    if (reset) state.offset = 0;

    const params = new URLSearchParams({ limit: 50, offset: state.offset });
    if (state.keyword) params.set("keyword", state.keyword);

    const res  = await fetch(`/api/feed?${params}`);
    const data = await res.json();

    renderTweets(data.tweets, reset);
    syncKeywordPills(data.keywords);

    state.hasMore = data.has_more;
    state.offset += data.tweets.length;
    document.getElementById("load-more").classList.toggle("hidden", !state.hasMore);
  } catch (e) {
    console.error("loadFeed error:", e);
  } finally {
    state.loading = false;
    btn.classList.remove("spinning");
  }
}

function renderTweets(tweets, reset) {
  const list = document.getElementById("tweet-list");
  if (reset) list.innerHTML = "";

  if (tweets.length === 0 && reset) {
    list.innerHTML = `
      <div class="empty-state">
        <p>No posts yet.</p>
        <p>Add a keyword above, then wait for the next fetch.</p>
      </div>`;
    return;
  }

  const frag = document.createDocumentFragment();
  for (const t of tweets) {
    const card = document.createElement("article");
    card.className = "tweet-card";
    card.innerHTML = `
      <div class="tweet-header">
        <img class="tweet-avatar"
             src="${esc(t.author_avatar || '')}"
             alt=""
             onerror="this.style.visibility='hidden'">
        <div class="tweet-meta">
          <div class="tweet-name">${esc(t.author_name)}</div>
          <div class="tweet-handle">@${esc(t.author_username)}</div>
        </div>
        <span class="keyword-badge">${esc(t.keyword)}</span>
      </div>
      <div class="tweet-content">${esc(t.content)}</div>
      <div class="tweet-footer">
        <span>♡ ${t.like_count}</span>
        <span>↺ ${t.retweet_count}</span>
        <span>↩ ${t.reply_count}</span>
        <span>${relTime(t.tweeted_at)}</span>
        <a href="${esc(t.tweet_url)}" target="_blank" rel="noopener noreferrer">Open ↗</a>
      </div>`;
    frag.appendChild(card);
  }
  list.appendChild(frag);
}

// ── Keyword pills ─────────────────────────────────────────────────────

function syncKeywordPills(keywords) {
  const nav = document.getElementById("keyword-nav");

  // Build current set from server response
  const serverKws = new Set(keywords.map(k => k.keyword));

  // Remove pills for deleted keywords
  nav.querySelectorAll(".pill[data-keyword]").forEach(pill => {
    const kw = pill.dataset.keyword;
    if (kw && !serverKws.has(kw)) {
      if (state.keyword === kw) setKeyword("");
      pill.remove();
      delete state.keywordIds[kw];
    }
  });

  // Add pills for new keywords
  for (const { id, keyword: kw } of keywords) {
    state.keywordIds[kw] = id;
    if (nav.querySelector(`.pill[data-keyword="${CSS.escape(kw)}"]`)) continue;

    const pill = document.createElement("button");
    pill.className = "pill";
    pill.dataset.keyword = kw;

    const label = document.createElement("span");
    label.className = "pill-label";
    label.textContent = kw;
    label.addEventListener("click", e => { e.stopPropagation(); setKeyword(kw); });

    const del = document.createElement("span");
    del.className = "pill-delete";
    del.textContent = "×";
    del.setAttribute("role", "button");
    del.setAttribute("aria-label", `Remove ${kw}`);
    del.addEventListener("click", e => { e.stopPropagation(); deleteKeyword(id, kw, pill); });

    pill.addEventListener("click", () => setKeyword(kw));
    pill.appendChild(label);
    pill.appendChild(del);
    nav.appendChild(pill);
  }
}

async function deleteKeyword(id, kw, pillEl) {
  pillEl.style.opacity = "0.4";
  await fetch(`/api/keywords/${id}`, { method: "DELETE" });
  if (state.keyword === kw) setKeyword("");
  pillEl.remove();
  delete state.keywordIds[kw];
  loadFeed(true);
}

function setKeyword(kw) {
  state.keyword = kw || null;
  document.querySelectorAll(".pill").forEach(p => {
    p.classList.toggle("active", p.dataset.keyword === (kw || ""));
  });
  loadFeed(true);
}

document.querySelector(".pill[data-keyword='']")
  .addEventListener("click", () => setKeyword(""));

// ── Add keyword ───────────────────────────────────────────────────────

document.getElementById("add-keyword-form").addEventListener("submit", async e => {
  e.preventDefault();
  const input = document.getElementById("keyword-input");
  const kw = input.value.trim();
  if (!kw) return;
  input.value = "";
  input.disabled = true;
  try {
    await fetch("/api/keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword: kw }),
    });
    setTimeout(() => loadFeed(true), 800);
  } finally {
    input.disabled = false;
  }
});

// ── Refresh / load more ───────────────────────────────────────────────

document.getElementById("refresh-btn").addEventListener("click", () => loadFeed(true));
document.getElementById("load-more").addEventListener("click", () => loadFeed(false));

// ── Pull-to-refresh ───────────────────────────────────────────────────

let touchStartY = 0;
document.addEventListener("touchstart", e => {
  touchStartY = e.touches[0].clientY;
}, { passive: true });
document.addEventListener("touchend", e => {
  const dy = e.changedTouches[0].clientY - touchStartY;
  const ptr = document.getElementById("ptr-indicator");
  ptr.style.display = "none";
  if (dy > 80 && window.scrollY === 0) loadFeed(true);
}, { passive: true });
document.addEventListener("touchmove", e => {
  const dy = e.touches[0].clientY - touchStartY;
  const ptr = document.getElementById("ptr-indicator");
  ptr.style.display = (dy > 40 && window.scrollY === 0) ? "block" : "none";
}, { passive: true });

// ── Auto-poll every 2 minutes ─────────────────────────────────────────

setInterval(() => {
  if (window.scrollY < 100) loadFeed(true);
}, 120_000);

// ── Account management ────────────────────────────────────────────────

async function loadAccounts() {
  const res  = await fetch("/api/accounts");
  const list = await res.json();
  const el   = document.getElementById("account-list");

  if (list.length === 0) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:8px 0">No accounts added yet.</p>';
    return;
  }

  el.innerHTML = list.map(a => `
    <div class="account-item">
      <span class="acc-name">@${esc(a.username)}</span>
      <span class="account-status ${a.active ? 'ok' : 'err'}">${a.active ? "active" : "error"}</span>
      <button class="account-delete" data-username="${esc(a.username)}" title="Remove">✕</button>
    </div>`).join("");

  el.querySelectorAll(".account-delete").forEach(btn => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/accounts/${encodeURIComponent(btn.dataset.username)}`, { method: "DELETE" });
      loadAccounts();
    });
  });
}

document.getElementById("account-panel").addEventListener("toggle", e => {
  if (e.target.open) loadAccounts();
});

document.getElementById("add-account-form").addEventListener("submit", async e => {
  e.preventDefault();
  const form   = e.target;
  const submit = form.querySelector("button[type=submit]");
  submit.disabled = true;
  submit.textContent = "Adding…";
  try {
    const body = {
      username:       form.username.value.replace(/^@/, ""),
      password:       form.password.value,
      email:          form.email.value,
      email_password: form.email_password.value,
      cookies:        form.cookies.value || null,
    };
    const res = await fetch("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      form.reset();
      loadAccounts();
    } else {
      const err = await res.json();
      alert("Error: " + (err.detail || JSON.stringify(err)));
    }
  } finally {
    submit.disabled = false;
    submit.textContent = "Add Account";
  }
});

// ── Utilities ─────────────────────────────────────────────────────────

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function relTime(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return `${Math.floor(diff)}s`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return new Date(iso).toLocaleDateString();
}

// ── Init ──────────────────────────────────────────────────────────────

loadFeed();
