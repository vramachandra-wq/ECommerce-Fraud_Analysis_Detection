import {
  t,
  curSym,
  languageToggleHtml,
  bindLanguageToggle,
} from "./i18n.js";

const PAGE_LABEL_KEYS = {
  ADMIN_PANEL: "nav_admin_panel",
  FRAUD_DASHBOARD: "nav_fraud_dashboard",
  POWER_BI_DASHBOARD: "nav_power_bi",
  AI_CHATBOT: "nav_analytics_ai",
};

function pageLabel(page) {
  return t(PAGE_LABEL_KEYS[page] || page);
}

const PAGE_ROUTES = {
  ADMIN_PANEL: "admin",
  FRAUD_DASHBOARD: "dashboard",
  POWER_BI_DASHBOARD: "analytics",
  AI_CHATBOT: "chatbot",
};

// Official sidebar order
const PAGE_ORDER = ["ADMIN_PANEL", "FRAUD_DASHBOARD", "POWER_BI_DASHBOARD", "AI_CHATBOT"];

const ROUTE_PAGES = Object.fromEntries(
  Object.entries(PAGE_ROUTES).map(([k, v]) => [v, k]),
);

let session = loadSession();
let chatMessages = [];

function loadSession() {
  try {
    return JSON.parse(localStorage.getItem("metro_cart_session") || "null");
  } catch {
    return null;
  }
}

function saveSession(data) {
  session = data;
  localStorage.setItem("metro_cart_session", JSON.stringify(data));
  localStorage.setItem("metro_cart_token", data.token);
}

function clearSession() {
  session = null;
  localStorage.removeItem("metro_cart_session");
  localStorage.removeItem("metro_cart_token");
}

async function api(path, options = {}, auth = true) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (auth && session?.token) headers.Authorization = `Bearer ${session.token}`;
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * Show a confirmation modal. Resolves true if confirmed, false if cancelled.
 * @param {{ title?: string, message: string, confirmLabel?: string, cancelLabel?: string, danger?: boolean, alertOnly?: boolean }} opts
 */
function confirmAction(opts) {
  const {
    title = t("confirm_action"),
    message,
    confirmLabel = t("confirm"),
    cancelLabel = t("cancel"),
    danger = false,
    alertOnly = false,
  } = opts || {};

  return new Promise((resolve) => {
    const existing = document.getElementById("confirm-modal");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "confirm-modal";
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h3 id="confirm-title">${esc(title)}</h3>
        <p>${esc(message)}</p>
        <div class="confirm-actions">
          ${alertOnly ? "" : `<button type="button" class="btn btn-secondary" data-confirm="no">${esc(cancelLabel)}</button>`}
          <button type="button" class="btn ${danger ? "btn-danger" : "btn-primary"}" data-confirm="yes">${esc(confirmLabel)}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const finish = (value) => {
      overlay.remove();
      document.removeEventListener("keydown", onKey);
      resolve(value);
    };
    const onKey = (e) => {
      if (e.key === "Escape") finish(alertOnly ? true : false);
      if (e.key === "Enter" && alertOnly) finish(true);
    };
    document.addEventListener("keydown", onKey);

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) finish(alertOnly ? true : false);
    });
    const noBtn = overlay.querySelector('[data-confirm="no"]');
    if (noBtn) noBtn.onclick = () => finish(false);
    overlay.querySelector('[data-confirm="yes"]').onclick = () => finish(true);
    overlay.querySelector('[data-confirm="yes"]').focus();
  });
}

function alertDialog({ title = t("success"), message, confirmLabel = t("ok") } = {}) {
  return confirmAction({ title, message, confirmLabel, alertOnly: true });
}

function badge(status) {
  return `<span class="badge badge-${esc(status)}">${esc(status.replaceAll("_", " "))}</span>`;
}

function money(n) {
  return `${curSym()} ${Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function formatMinutes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const mins = Math.abs(Number(value));
  if (mins < 60) return t("minutes_short", { n: Math.round(mins) });
  const hours = Math.floor(mins / 60);
  const rem = Math.round(mins % 60);
  return rem
    ? t("hours_mins_short", { h: hours, m: rem })
    : t("hours_short", { h: hours });
}

function remainingCell(o) {
  if (o.is_overdue) {
    return `<span class="timing timing-overdue">${t("overdue_with_time", { mins: formatMinutes(o.minutes_overdue) })}</span>`;
  }
  return `<span class="timing timing-ok">${formatMinutes(o.minutes_remaining_display ?? o.minutes_remaining)}</span>`;
}

function queueHeadersHtml() {
  return `<tr>
    <th style="width:42px"><input type="checkbox" class="q-select-all" title="${esc(t("select_all_page"))}" /></th>
    <th>${esc(t("col_order_short"))}</th><th>${esc(t("col_customer"))}</th><th>${esc(t("col_product"))}</th><th>${esc(t("col_amount"))}</th><th>${esc(t("col_status"))}</th>
    <th>${esc(t("col_delay_short"))}</th><th>${esc(t("col_remaining"))}</th><th>${esc(t("col_rule_short"))}</th><th>${esc(t("col_placed_short"))}</th>
  </tr>`;
}

const QUEUE_PAGE_SIZE = 10;

function queuePageCount(total) {
  return Math.max(1, Math.ceil((total || 0) / QUEUE_PAGE_SIZE));
}

function queuePageSlice(items, page) {
  const safePage = Math.min(Math.max(1, page), queuePageCount(items.length));
  const start = (safePage - 1) * QUEUE_PAGE_SIZE;
  return {
    page: safePage,
    rows: items.slice(start, start + QUEUE_PAGE_SIZE),
    start: items.length ? start + 1 : 0,
    end: Math.min(start + QUEUE_PAGE_SIZE, items.length),
    totalPages: queuePageCount(items.length),
  };
}

function pagerHtml({ page, total, totalPages, start, end, prefix }) {
  if (!total) return "";
  const buttons = [];
  const windowStart = Math.max(1, page - 2);
  const windowEnd = Math.min(totalPages, windowStart + 4);
  for (let p = windowStart; p <= windowEnd; p += 1) {
    buttons.push(
      `<button type="button" class="pager-btn ${p === page ? "active" : ""}" data-page="${p}" data-pager="${prefix}">${p}</button>`,
    );
  }
  return `
    <div class="pager" id="${prefix}-pager">
      <div class="pager-info">${esc(t("pager_showing", { start, end, total, page, total_pages: totalPages, size: QUEUE_PAGE_SIZE }))}</div>
      <div class="pager-controls">
        <button type="button" class="pager-btn" data-page="${page - 1}" data-pager="${prefix}" ${page <= 1 ? "disabled" : ""}>${esc(t("pager_prev"))}</button>
        ${buttons.join("")}
        <button type="button" class="pager-btn" data-page="${page + 1}" data-pager="${prefix}" ${page >= totalPages ? "disabled" : ""}>${esc(t("pager_next"))}</button>
      </div>
    </div>`;
}

function queueRowHtml(o, { selected, pickable }) {
  const pickCell = pickable
    ? `<td><button type="button" class="btn btn-ghost aq-pick" data-id="${esc(o.order_id)}" style="padding:0;color:var(--accent)">${esc(o.order_id)}</button></td>`
    : `<td>${esc(o.order_id)}</td>`;
  const placed = o.tagged_timestamp || o.order_timestamp || "";
  return `
    <tr data-id="${esc(o.order_id)}" class="${o.is_overdue ? "row-overdue" : ""}">
      <td><input type="checkbox" class="q-check" data-id="${esc(o.order_id)}" ${selected.has(o.order_id) ? "checked" : ""} /></td>
      ${pickCell}
      <td>${esc(o.customer_name)}</td>
      <td>${esc(o.product_name)}</td>
      <td>${money(o.amount)}</td>
      <td>${badge(o.order_status)}</td>
      <td>${esc(o.delay_minutes ?? "—")}m</td>
      <td>${remainingCell(o)}</td>
      <td title="${esc(o.flagged_reason || "")}">${esc(o.rule_name || "—")}</td>
      <td>${esc(placed)}</td>
    </tr>`;
}

function backlogCardHtml(orders, metrics) {
  const overdue = (orders || []).filter((o) => o.is_overdue);
  const backlogCount = metrics?.backlog ?? overdue.length;
  if (!backlogCount) {
    return `<div class="card"><h3>${esc(t("backlog_section"))}</h3><div class="alert alert-success">${esc(t("backlog_none_open"))}</div></div>`;
  }
  const preview = overdue.slice(0, 5);
  const subtitle = [
    t("backlog_past_delay", { n: backlogCount }),
    metrics?.max_minutes_overdue
      ? t("backlog_max_overdue", { mins: formatMinutes(metrics.max_minutes_overdue) })
      : "",
  ].filter(Boolean).join(" · ");
  return `
    <div class="card">
      <div class="section-head" style="margin-bottom:0.75rem">
        <h3 style="margin:0">${esc(t("backlog_title_overdue"))}</h3>
        <p class="subtitle" style="margin:0">${esc(subtitle)}</p>
      </div>
      <table>
        <thead>
          <tr><th>${esc(t("col_order_short"))}</th><th>${esc(t("col_status"))}</th><th>${esc(t("col_rule_short"))}</th><th>${esc(t("col_overdue"))}</th><th>${esc(t("col_delay_short"))}</th></tr>
        </thead>
        <tbody>
          ${preview.map((o) => `
            <tr class="row-overdue">
              <td>${esc(o.order_id)}</td>
              <td>${badge(o.order_status)}</td>
              <td>${esc(o.rule_name || "—")}</td>
              <td class="timing timing-overdue">${formatMinutes(o.minutes_overdue)}</td>
              <td>${esc(o.delay_minutes ?? "—")}m</td>
            </tr>`).join("")}
        </tbody>
      </table>
      ${overdue.length > preview.length ? `<p class="subtitle">${esc(t("backlog_showing_preview", { shown: preview.length, total: overdue.length }))}</p>` : ""}
    </div>`;
}

function investigationTimingHtml(timing, order) {
  const tm = timing || {};
  const delay = tm.delay_minutes ?? order?.delay_minutes;
  const remaining = tm.is_overdue
    ? `<span class="timing timing-overdue">${t("overdue_with_time", { mins: formatMinutes(tm.minutes_overdue) })}</span>`
    : `<span class="timing timing-ok">${formatMinutes(tm.minutes_remaining_display ?? tm.minutes_remaining)}</span>`;
  return `
    <div class="overview-grid" style="margin:1rem 0;grid-template-columns:repeat(3,minmax(0,1fr))">
      <div class="stat-card"><div><div class="stat-value" style="font-size:1.25rem">${esc(delay ?? "—")}m</div><div class="stat-label">${esc(t("review_delay"))}</div></div></div>
      <div class="stat-card"><div><div class="stat-value" style="font-size:1.25rem">${remaining}</div><div class="stat-label">${esc(t("time_left"))}</div></div></div>
      <div class="stat-card"><div><div class="stat-value" style="font-size:1.1rem">${esc(tm.rule_name || order?.flagged_reason || "—")}</div><div class="stat-label">${esc(t("triggered_rule"))}</div></div></div>
    </div>`;
}

function currentRoute() {
  const hash = location.hash.replace(/^#\/?/, "") || "dashboard";
  return hash.split("/")[0];
}

function navigate(route) {
  location.hash = `#/${route}`;
  render();
}

function hasPage(page) {
  return session?.granted_pages?.includes(page);
}

const NAV_ICONS = {
  dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>`,
  admin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 4v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7l8-4z"/><path d="M9 12l2 2 4-4"/></svg>`,
  analytics: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 17V10"/><path d="M12 17V7"/><path d="M16 17v-4"/></svg>`,
  chatbot: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a8 8 0 01-8 8H7l-4 3V12a8 8 0 018-8h2a8 8 0 018 8z"/></svg>`,
};

function initials(name) {
  return String(name || "MC")
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function shell(content, route) {
  const granted = new Set(session.granted_pages || []);
  const pages = PAGE_ORDER.filter((page) => granted.has(page));
  const nav = pages
    .map((page) => {
      const r = PAGE_ROUTES[page];
      return `<a href="#/${r}" class="nav-link ${route === r ? "active" : ""}">
        ${NAV_ICONS[r] || NAV_ICONS.dashboard}
        <span>${esc(pageLabel(page))}</span>
        <span class="chev">›</span>
      </a>`;
    })
    .join("");

  return `
    <div class="app-frame">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-logo">M</div>
          <div class="sidebar-brand-name">${esc(t("internal_brand"))}</div>
        </div>
        <div class="sidebar-section">${esc(t("workspace"))}</div>
        ${nav}
        <div class="sidebar-footer">
          <button class="btn btn-ghost" style="width:100%" id="logout-btn">${esc(t("log_out"))}</button>
        </div>
      </aside>
      <div class="main-wrap">
        <header class="topbar">
          <div class="topbar-left">
            <span class="subtitle" style="margin:0">${esc(t("fraud_analyst_workspace"))}</span>
          </div>
          <div class="topbar-right">
            ${languageToggleHtml({ id: "lang-select" })}
            <div class="user-chip" style="border-left:none;padding-left:0">
              <span class="user-chip-text">${esc(t("hi_user", { name: session.analyst.employee_name }))}</span>
              <div class="user-avatar">${esc(initials(session.analyst.employee_name))}</div>
            </div>
          </div>
        </header>
        <main class="content ${route === "chatbot" ? "content--chat" : ""}">${content}</main>
      </div>
    </div>
  `;
}

async function renderLogin() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="login-wrap">
      <div class="login-lang">${languageToggleHtml({ id: "lang-select-login" })}</div>
      <form class="login-card" id="login-form">
        <div class="login-logo-row">
          <div class="sidebar-logo">M</div>
          <h1>${esc(t("internal_brand"))}</h1>
        </div>
        <p class="subtitle" style="margin-top:0">${esc(t("analyst_login_subtitle"))}</p>
        <div id="login-error"></div>
        <div class="field"><label>${esc(t("username"))}</label><input name="username" required autocomplete="username" /></div>
        <div class="field"><label>${esc(t("password"))}</label><input name="password" type="password" required autocomplete="current-password" /></div>
        <button class="btn btn-primary" style="width:100%" type="submit">${esc(t("sign_in"))}</button>
      </form>
    </div>
  `;
  bindLanguageToggle("lang-select-login", () => renderLogin());
  document.getElementById("login-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = document.getElementById("login-error");
    err.innerHTML = "";
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: fd.get("username"),
          password: fd.get("password"),
        }),
      }, false);
      saveSession(data);
      const first = PAGE_ROUTES[data.granted_pages[0]] || "dashboard";
      navigate(first);
    } catch (ex) {
      err.innerHTML = `<div class="alert alert-error">${esc(ex.message || t("invalid_login_analyst"))}</div>`;
    }
  };
}

function overviewIcon(kind) {
  const icons = {
    people: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
    pin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
    mic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><path d="M12 19v4"/><path d="M8 23h8"/></svg>`,
    bag: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 7h12l1 14H5L6 7z"/><path d="M9 7V5a3 3 0 016 0v2"/></svg>`,
    orders: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6"/><path d="M9 16h4"/></svg>`,
    fraud: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
    rate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 15l3-4 3 2 4-6"/></svg>`,
  };
  return icons[kind] || icons.people;
}

function buildBarChart(m) {
  const series = [
    { label: "Queue", value: m.total || 0, color: "#1a237e" },
    { label: "Pending", value: m.pending_review || 0, color: "#1976d2" },
    { label: "On Hold", value: m.on_hold || 0, color: "#fb8c00" },
    { label: "Cleared*", value: Math.max((m.total || 0) - (m.pending_review || 0) - (m.on_hold || 0), 0), color: "#ec407a" },
  ];
  // Fake multi-group bars like Matx (4 groups × 4 series) using scaled queue metrics
  const groups = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const max = Math.max(...series.map((s) => s.value), 1);
  const bars = groups.map((g, gi) => {
    const factor = 0.55 + ((gi % 5) * 0.12);
    return `<div class="bar-group" title="${g}">
      ${series.map((s) => {
        const h = Math.max(8, Math.round(((s.value * factor) / max) * 180));
        return `<div class="bar" style="height:${h}px;background:${s.color}"></div>`;
      }).join("")}
    </div>`;
  }).join("");
  return `
    <div class="chart-legend">
      ${series.map((s) => `<div class="legend-item"><span class="legend-dot" style="background:${s.color}"></span>${esc(s.label)}</div>`).join("")}
    </div>
    <div class="bar-chart">${bars}</div>
    <div class="bar-labels">${groups.map((g) => `<span>${g}</span>`).join("")}</div>
    <p class="subtitle" style="margin:0.75rem 0 0;font-size:0.75rem">* Cleared = total minus pending and on-hold in current queue snapshot</p>
  `;
}

async function renderDashboard() {
  document.getElementById("app").innerHTML = shell(`
    <div class="section-head">
      <h1 class="page-title">${esc(t("overview"))}</h1>
      <select class="select-pill" id="dash-period"><option>${esc(t("period_this_month"))}</option><option>${esc(t("period_this_week"))}</option><option>${esc(t("period_today"))}</option></select>
    </div>
    <p class="subtitle">${esc(t("loading_dashboard"))}</p>
  `, "dashboard");
  bindShell();

  try {
    const sync = await api("/portal/sync-holds", { method: "POST" });
    const data = await api("/portal/queue");
    let orders = data.orders || [];
    const m = data.metrics || { total: 0, pending_review: 0, on_hold: 0 };
    let selectedIds = new Set();
    let activeId = orders[0]?.order_id || "";
    let detail = activeId ? await api(`/portal/orders/${encodeURIComponent(activeId)}`) : null;
    let queuePage = 1;

    function paint() {
      const order = detail?.order;
      const bl = detail?.blacklists || {};
      const timing = detail?.timing || orders.find((o) => o.order_id === activeId) || {};
      const pageInfo = queuePageSlice(orders, queuePage);
      queuePage = pageInfo.page;
      const pageRows = pageInfo.rows;
      const pageIds = pageRows.map((o) => o.order_id);
      const pageSelectedCount = pageIds.filter((id) => selectedIds.has(id)).length;

      const content = `
        <div class="section-head">
          <h1 class="page-title">${esc(t("overview"))}</h1>
          <select class="select-pill" id="dash-period"><option>${esc(t("period_this_month"))}</option><option>${esc(t("period_this_week"))}</option><option>${esc(t("period_today"))}</option></select>
        </div>
        ${sync.auto_approved ? `<div class="alert alert-info">${esc(t("auto_approved_hold", { n: sync.auto_approved }))}</div>` : ""}

        <div class="overview-grid">
          <div class="stat-card">
            <div class="stat-icon blue">${overviewIcon("people")}</div>
            <div>
              <div class="stat-value">${Number(m.total || 0).toLocaleString()}</div>
              <div class="stat-label">${esc(t("orders_in_queue"))}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon orange">${overviewIcon("pin")}</div>
            <div>
              <div class="stat-value">${Number(m.pending_review || 0).toLocaleString()}</div>
              <div class="stat-label">${esc(t("pending_review"))}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon navy">${overviewIcon("mic")}</div>
            <div>
              <div class="stat-value">${Number(m.on_hold || 0).toLocaleString()}</div>
              <div class="stat-label">${esc(t("on_hold"))}</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon pink">${overviewIcon("bag")}</div>
            <div>
              <div class="stat-value">${Number(m.backlog || 0).toLocaleString()}</div>
              <div class="stat-label">${esc(t("backlog_overdue_label"))}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="stats-card-head">
            <p class="section-kicker" style="margin:0">${esc(t("statistics"))}</p>
            <button class="icon-btn" type="button" title="More">⋯</button>
          </div>
          ${buildBarChart(m)}
        </div>

        ${backlogCardHtml(orders, m)}

        <div class="card">
          <div class="section-head" style="margin-bottom:0.75rem">
            <h3 style="margin:0">${esc(t("review_queue"))}</h3>
            <p class="subtitle" style="margin:0">${orders.length} total · ${QUEUE_PAGE_SIZE} rows per page · delay from rule_master</p>
          </div>
          ${orders.length ? `
            <table>
              <thead>
                <tr>
                  <th style="width:42px"><input type="checkbox" id="dq-select-all" title="Select all on this page" /></th>
                  <th>Order</th><th>Customer</th><th>Product</th><th>Amount</th><th>Status</th>
                  <th>Delay</th><th>Remaining</th><th>Rule</th><th>Placed</th>
                </tr>
              </thead>
              <tbody id="dq-tbody">
                ${pageRows.map((o) => queueRowHtml(o, { selected: selectedIds, pickable: false })).join("")}
              </tbody>
            </table>
            ${pagerHtml({ ...pageInfo, total: orders.length, prefix: "dq" })}
          ` : `<div class="alert alert-success">Queue is clear. No orders pending review.</div>`}
        </div>

        <div class="card ${selectedIds.size ? "" : "hidden"}" id="batch-card">
          <h3 id="dq-batch-title">${esc(t("batch_actions", { n: selectedIds.size }))}</h3>
          <p class="subtitle" id="dq-batch-hint">${pageSelectedCount ? `${pageSelectedCount} selected on this page` : "Selections are kept across pages"}</p>
          <textarea id="batch-comments" rows="3" placeholder="Comments (required for reject / mark as fraud)"></textarea>
          <div class="row-actions">
            <button class="btn btn-primary" id="batch-approve">${esc(t("approve_selected"))}</button>
            <button class="btn btn-secondary" id="batch-reject">${esc(t("reject_selected"))}</button>
            <button class="btn btn-fraud" id="batch-fraud">Mark as Fraud</button>
            <button class="btn btn-secondary" id="batch-clear">Clear Selection</button>
          </div>
        </div>

        ${orders.length ? `
        <div class="card">
          <h3>Order Investigation</h3>
          <div class="field">
            <label>Order ID</label>
            <select id="order-select">${orders.map((o) => `<option value="${esc(o.order_id)}" ${o.order_id === activeId ? "selected" : ""}>${esc(o.order_id)}${o.is_overdue ? " · OVERDUE" : ""}</option>`).join("")}</select>
          </div>
          ${order ? `
            <p>${badge(order.order_status)}</p>
            ${investigationTimingHtml(timing, order)}
            <div style="display:grid;gap:1rem;grid-template-columns:1fr 1fr">
              <div><strong>Customer</strong><br>${esc(order.customer_name)} (${esc(order.user_id)})<br>Email: ${esc(order.email)}${bl.email ? " (blacklisted)" : ""}<br>Phone: ${esc(order.phone_number)}${bl.phone ? " (blacklisted)" : ""}<br>Address: ${esc(order.address || "—")}</div>
              <div><strong>Order</strong><br>${esc(order.product_name)} x${esc(order.quantity)}<br>${money(order.amount)}<br>IP: ${esc(order.ip_address)}${bl.ip ? " (blacklisted)" : ""}<br>Device: ${esc(order.device_id || "—")}</div>
            </div>
            <div class="alert alert-warning" style="margin-top:1rem">Flagged: ${esc(order.flagged_reason)}</div>
            <div class="field"><label>Review comments</label><textarea id="review-comments" rows="3"></textarea></div>
            <div class="row-actions">
              <button class="btn btn-primary" id="approve-one">Approve</button>
              <button class="btn btn-secondary" id="reject-one">Reject</button>
              <button class="btn btn-fraud" id="fraud-one">Mark as Fraud</button>
            </div>
          ` : ""}
        </div>` : ""}
        <div id="dash-error"></div>
      `;

      document.getElementById("app").innerHTML = shell(content, "dashboard");
      bindShell();

      function syncChecks() {
        const allOnPage = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));
        const someOnPage = pageIds.some((id) => selectedIds.has(id));
        const selectAll = document.getElementById("dq-select-all");
        if (selectAll) {
          selectAll.checked = allOnPage;
          selectAll.indeterminate = someOnPage && !allOnPage;
        }
        document.querySelectorAll("#dq-tbody .q-check").forEach((cb) => {
          cb.checked = selectedIds.has(cb.dataset.id);
        });
        const batch = document.getElementById("batch-card");
        const title = document.getElementById("dq-batch-title");
        const hint = document.getElementById("dq-batch-hint");
        if (batch) batch.classList.toggle("hidden", selectedIds.size === 0);
        if (title) title.textContent = t("batch_actions", { n: selectedIds.size });
        if (hint) {
          const onPage = pageIds.filter((id) => selectedIds.has(id)).length;
          hint.textContent = onPage
            ? `${onPage} selected on this page · ${selectedIds.size} total selected`
            : "Selections are kept across pages";
        }
      }

      document.getElementById("dq-select-all")?.addEventListener("change", (e) => {
        if (e.target.checked) pageIds.forEach((id) => selectedIds.add(id));
        else pageIds.forEach((id) => selectedIds.delete(id));
        syncChecks();
      });
      document.querySelectorAll("#dq-tbody .q-check").forEach((cb) => {
        cb.addEventListener("change", () => {
          const id = cb.dataset.id;
          if (cb.checked) selectedIds.add(id); else selectedIds.delete(id);
          syncChecks();
        });
      });

      document.querySelectorAll('#dq-pager .pager-btn').forEach((btn) => {
        btn.addEventListener("click", () => {
          const next = Number(btn.dataset.page);
          if (!next || next < 1 || next > pageInfo.totalPages || next === queuePage) return;
          queuePage = next;
          paint();
        });
      });

      document.getElementById("order-select")?.addEventListener("change", async (e) => {
        activeId = e.target.value;
        detail = await api(`/portal/orders/${encodeURIComponent(activeId)}`);
        paint();
      });

      document.getElementById("approve-one")?.addEventListener("click", async () => {
        const ok = await confirmAction({
          title: "Approve order",
          message: `Approve order ${activeId}? This will clear it from the review queue.`,
          confirmLabel: "Approve",
        });
        if (!ok) return;
        try {
          await api("/approve-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            approved_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: document.getElementById("review-comments")?.value || "",
          })});
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("reject-one")?.addEventListener("click", async () => {
        const comments = (document.getElementById("review-comments")?.value || "").trim();
        if (!comments) return showDashError("Comments required for rejection.");
        const ok = await confirmAction({
          title: "Reject order",
          message: `Reject order ${activeId} without marking it as fraud? Use this for non-fraud reasons (e.g. inventory).`,
          confirmLabel: "Reject",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/reject-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: false,
          })});
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("fraud-one")?.addEventListener("click", async () => {
        const comments = (document.getElementById("review-comments")?.value || "").trim();
        if (!comments) return showDashError("Comments required to mark as fraud.");
        const ok = await confirmAction({
          title: "Mark as fraud",
          message: `Mark order ${activeId} as fraudulent and reject it?`,
          confirmLabel: "Mark as Fraud",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/reject-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: true,
          })});
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("batch-approve")?.addEventListener("click", async () => {
        if (!selectedIds.size) return showDashError("Select at least one order.");
        const count = selectedIds.size;
        const ok = await confirmAction({
          title: "Approve selected orders",
          message: `Approve ${count} selected order${count === 1 ? "" : "s"}?`,
          confirmLabel: "Approve all",
        });
        if (!ok) return;
        try {
          await api("/batch-approve", { method: "PUT", body: JSON.stringify({
            order_ids: [...selectedIds],
            approved_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: document.getElementById("batch-comments")?.value || "",
          })});
          selectedIds = new Set();
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("batch-reject")?.addEventListener("click", async () => {
        const comments = (document.getElementById("batch-comments")?.value || "").trim();
        if (!selectedIds.size) return showDashError("Select at least one order.");
        if (!comments) return showDashError("Batch comments required for rejection.");
        const count = selectedIds.size;
        const ok = await confirmAction({
          title: "Reject selected orders",
          message: `Reject ${count} selected order${count === 1 ? "" : "s"} without marking as fraud?`,
          confirmLabel: "Reject all",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/batch-reject", { method: "PUT", body: JSON.stringify({
            order_ids: [...selectedIds],
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: false,
          })});
          selectedIds = new Set();
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("batch-fraud")?.addEventListener("click", async () => {
        const comments = (document.getElementById("batch-comments")?.value || "").trim();
        if (!selectedIds.size) return showDashError("Select at least one order.");
        if (!comments) return showDashError("Batch comments required to mark as fraud.");
        const count = selectedIds.size;
        const ok = await confirmAction({
          title: "Mark selected as fraud",
          message: `Mark ${count} selected order${count === 1 ? "" : "s"} as fraudulent and reject them?`,
          confirmLabel: "Mark as Fraud",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/batch-reject", { method: "PUT", body: JSON.stringify({
            order_ids: [...selectedIds],
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: true,
          })});
          selectedIds = new Set();
          await reload();
        } catch (ex) { showDashError(ex.message); }
      });
      document.getElementById("batch-clear")?.addEventListener("click", () => {
        selectedIds = new Set();
        syncChecks();
      });

      syncChecks();
    }

    function showDashError(msg) {
      const el = document.getElementById("dash-error");
      if (el) el.innerHTML = `<div class="alert alert-error">${esc(msg)}</div>`;
    }

    async function reload() {
      const fresh = await api("/portal/queue");
      orders = fresh.orders || [];
      Object.assign(m, fresh.metrics || {});
      if (!orders.find((o) => o.order_id === activeId)) activeId = orders[0]?.order_id || "";
      // Keep page in range after delete/approve
      queuePage = Math.min(queuePage, queuePageCount(orders.length));
      detail = activeId ? await api(`/portal/orders/${encodeURIComponent(activeId)}`) : null;
      paint();
    }

    paint();
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(`<div class="alert alert-error">${esc(ex.message)}</div>`, "dashboard");
    bindShell();
  }
}

const ADMIN_TAB_DEFS = [
  {
    id: "queue",
    labelKey: "tab_review_queue",
    blurbKey: "admin_tab_blurb_queue",
    tone: "blue",
    icon: "queue",
  },
  {
    id: "blacklists",
    labelKey: "tab_blacklists",
    blurbKey: "admin_tab_blurb_blacklists",
    tone: "rose",
    icon: "shield",
  },
  {
    id: "permissions",
    labelKey: "tab_permissions",
    blurbKey: "admin_tab_blurb_permissions",
    tone: "indigo",
    icon: "key",
  },
  {
    id: "users",
    labelKey: "tab_user_mgmt",
    blurbKey: "admin_tab_blurb_users",
    tone: "teal",
    icon: "users",
  },
  {
    id: "analytics",
    labelKey: "tab_analytics",
    blurbKey: "admin_tab_blurb_analytics",
    tone: "amber",
    icon: "chart",
  },
  {
    id: "rules",
    labelKey: "tab_rule_mgmt",
    blurbKey: "admin_tab_blurb_rules",
    tone: "navy",
    icon: "rules",
  },
];

function adminTabs() {
  return ADMIN_TAB_DEFS.map((tab) => ({
    ...tab,
    label: t(tab.labelKey),
    blurb: t(tab.blurbKey),
  }));
}

let adminActiveTab = "queue";

function adminTabIcon(kind) {
  const icons = {
    queue: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>`,
    shield: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    key: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>`,
    users: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>`,
    chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6"/></svg>`,
    rules: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7l8-4z"/><path d="M9 12l2 2 4-4"/></svg>`,
  };
  return icons[kind] || icons.queue;
}

function adminTabMeta(tabId) {
  return adminTabs().find((tab) => tab.id === tabId) || adminTabs()[0];
}

function adminTabIntro(tabId) {
  const tab = adminTabMeta(tabId);
  return `
    <div class="admin-section-head tone-${esc(tab.tone)}">
      <span class="admin-section-icon">${adminTabIcon(tab.icon)}</span>
      <div>
        <h2 class="admin-section-title">${esc(tab.label)}</h2>
        <p class="admin-section-sub">${esc(tab.blurb)}</p>
      </div>
    </div>`;
}

function adminStatus(msg, tone = "success") {
  const el = document.getElementById("admin-status");
  if (!el) return;
  el.innerHTML = msg ? `<div class="alert alert-${tone}">${esc(msg)}</div>` : "";
}

function syncAdminTabButtons() {
  document.querySelectorAll("#admin-tabs .admin-tab").forEach((b) => {
    const on = b.dataset.tab === adminActiveTab;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
}

async function renderAdmin() {
  document.getElementById("app").innerHTML = shell(`
    <header class="admin-page-head">
      <div>
        <h1 class="page-title">${esc(t("admin_control_panel"))}</h1>
        <p class="subtitle">${esc(t("admin_subtitle"))}</p>
      </div>
      <div class="admin-page-meta">
        <span class="admin-role-badge">${esc(session.analyst.role)}</span>
        <span class="admin-meta-id">${esc(session.analyst.employee_name)}</span>
      </div>
    </header>

    <nav class="admin-nav" aria-label="Admin tools">
      <div class="admin-tabs" id="admin-tabs" role="tablist">
        ${adminTabs().map((tab) => `
          <button type="button" class="admin-tab tone-${esc(tab.tone)} ${adminActiveTab === tab.id ? "active" : ""}" data-tab="${esc(tab.id)}" role="tab" aria-selected="${adminActiveTab === tab.id}" title="${esc(tab.blurb)}">
            <span class="admin-tab-icon">${adminTabIcon(tab.icon)}</span>
            <span class="admin-tab-label">${esc(tab.label)}</span>
          </button>`).join("")}
      </div>
    </nav>

    <div id="admin-status"></div>
    <div id="admin-body"><div class="admin-loading"><span class="admin-loading-dot"></span> ${esc(t("loading_workspace"))}</div></div>
  `, "admin");
  bindShell();

  document.querySelectorAll("#admin-tabs .admin-tab").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (btn.dataset.tab === adminActiveTab && document.getElementById("admin-tab-main")) return;
      adminActiveTab = btn.dataset.tab;
      syncAdminTabButtons();
      adminStatus("");
      await loadAdminTab(adminActiveTab);
    });
  });

  await loadAdminTab(adminActiveTab);
}

async function loadAdminTab(tab) {
  const body = document.getElementById("admin-body");
  if (!body) return;
  body.innerHTML = `
    <div class="admin-tab-panel admin-tab-enter">
      ${adminTabIntro(tab)}
      <div id="admin-tab-main"><div class="admin-loading"><span class="admin-loading-dot"></span> ${esc(t("loading_named", { name: adminTabMeta(tab).label }))}</div></div>
    </div>`;
  const main = document.getElementById("admin-tab-main");
  try {
    if (tab === "queue") await renderAdminQueue(main);
    else if (tab === "blacklists") renderAdminBlacklists(main);
    else if (tab === "permissions") await renderAdminPermissions(main);
    else if (tab === "users") await renderAdminUsers(main);
    else if (tab === "analytics") await renderAdminAnalytics(main);
    else if (tab === "rules") await renderAdminRules(main);
    else main.innerHTML = `<div class="alert alert-error">${esc(t("unknown_tab"))}</div>`;
  } catch (ex) {
    main.innerHTML = `<div class="alert alert-error">${esc(ex.message)}</div>`;
  }
}

async function renderAdminQueue(body) {
  const sync = await api("/portal/sync-holds", { method: "POST" });
  const data = await api("/portal/queue");
  let orders = data.orders || [];
  const m = data.metrics || {};
  let selected = new Set();
  let activeId = orders[0]?.order_id || "";
  let reviewComments = "";
  let queuePage = 1;

  async function paintQueue() {
    const pageInfo = queuePageSlice(orders, queuePage);
    queuePage = pageInfo.page;
    const pageRows = pageInfo.rows;
    const pageIds = pageRows.map((o) => o.order_id);

    body.innerHTML = `
      ${sync.auto_approved ? `<div class="alert alert-info">${esc(t("auto_approved_hold", { n: sync.auto_approved }))}</div>` : ""}
      <div class="overview-grid" style="margin-bottom:1.25rem">
        <div class="stat-card admin-stat-lift"><div class="stat-icon blue">${overviewIcon("people")}</div><div><div class="stat-value">${m.total || 0}</div><div class="stat-label">${esc(t("total_in_queue"))}</div></div></div>
        <div class="stat-card admin-stat-lift"><div class="stat-icon orange">${overviewIcon("pin")}</div><div><div class="stat-value">${m.pending_review || 0}</div><div class="stat-label">${esc(t("pending_review"))}</div></div></div>
        <div class="stat-card admin-stat-lift"><div class="stat-icon navy">${overviewIcon("mic")}</div><div><div class="stat-value">${m.on_hold || 0}</div><div class="stat-label">${esc(t("on_hold"))}</div></div></div>
        <div class="stat-card admin-stat-lift"><div class="stat-icon pink">${overviewIcon("bag")}</div><div><div class="stat-value">${m.backlog || 0}</div><div class="stat-label">${esc(t("backlog_overdue_label"))}</div></div></div>
      </div>
      ${backlogCardHtml(orders, m)}
      <div class="card">
        <div class="section-head" style="margin-bottom:0.75rem">
          <h3 style="margin:0">${esc(t("review_queue"))}</h3>
          <p class="subtitle" style="margin:0">${orders.length} total · ${QUEUE_PAGE_SIZE} rows per page · delay from rule_master</p>
        </div>
        ${orders.length ? `
          <table>
            <thead>
              <tr>
                <th style="width:42px"><input type="checkbox" id="aq-select-all" title="Select all on this page" /></th>
                <th>Order</th><th>Customer</th><th>Product</th><th>Amount</th><th>Status</th>
                <th>Delay</th><th>Remaining</th><th>Rule</th><th>Placed</th>
              </tr>
            </thead>
            <tbody id="aq-tbody">
              ${pageRows.map((o) => queueRowHtml(o, { selected, pickable: true })).join("")}
            </tbody>
          </table>
          ${pagerHtml({ ...pageInfo, total: orders.length, prefix: "aq" })}
        ` : `<div class="alert alert-success">Queue is clear.</div>`}
      </div>
      <div class="card ${selected.size ? "" : "hidden"}" id="aq-batch">
        <h3 id="aq-batch-title">${esc(t("batch_actions", { n: selected.size }))}</h3>
        <p class="subtitle" id="aq-batch-hint">Selections are kept across pages</p>
        <textarea id="aq-batch-comments" rows="2" placeholder="Comments (required for reject / mark as fraud)"></textarea>
        <div class="row-actions">
          <button type="button" class="btn btn-primary" id="aq-batch-approve">${esc(t("approve_selected"))}</button>
          <button type="button" class="btn btn-secondary" id="aq-batch-reject">${esc(t("reject_selected"))}</button>
          <button type="button" class="btn btn-fraud" id="aq-batch-fraud">Mark as Fraud</button>
          <button type="button" class="btn btn-secondary" id="aq-batch-clear">Clear Selection</button>
        </div>
      </div>
      <div id="aq-detail"></div>
    `;

    function syncSelectionUI() {
      const allOnPage = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
      const someOnPage = pageIds.some((id) => selected.has(id));
      const selectAll = document.getElementById("aq-select-all");
      if (selectAll) {
        selectAll.checked = allOnPage;
        selectAll.indeterminate = someOnPage && !allOnPage;
      }
      body.querySelectorAll("#aq-tbody .q-check").forEach((cb) => {
        cb.checked = selected.has(cb.dataset.id);
      });
      const batch = document.getElementById("aq-batch");
      const title = document.getElementById("aq-batch-title");
      const hint = document.getElementById("aq-batch-hint");
      if (batch) batch.classList.toggle("hidden", selected.size === 0);
      if (title) title.textContent = t("batch_actions", { n: selected.size });
      if (hint) {
        const onPage = pageIds.filter((id) => selected.has(id)).length;
        hint.textContent = onPage
          ? `${onPage} selected on this page · ${selected.size} total selected`
          : "Selections are kept across pages";
      }
    }

    document.getElementById("aq-select-all")?.addEventListener("change", (e) => {
      if (e.target.checked) pageIds.forEach((id) => selected.add(id));
      else pageIds.forEach((id) => selected.delete(id));
      syncSelectionUI();
    });

    body.querySelectorAll("#aq-tbody .q-check").forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = cb.dataset.id;
        if (cb.checked) selected.add(id); else selected.delete(id);
        syncSelectionUI();
      });
    });

    body.querySelectorAll(".aq-pick").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeId = btn.dataset.id;
        loadDetail();
      });
    });

    document.querySelectorAll("#aq-pager .pager-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = Number(btn.dataset.page);
        if (!next || next < 1 || next > pageInfo.totalPages || next === queuePage) return;
        queuePage = next;
        paintQueue();
      });
    });

    document.getElementById("aq-batch-clear")?.addEventListener("click", () => {
      selected = new Set();
      syncSelectionUI();
    });

    document.getElementById("aq-batch-approve")?.addEventListener("click", async () => {
      if (!selected.size) return adminStatus("Select at least one order.", "error");
      const count = selected.size;
      const ok = await confirmAction({
        title: "Approve selected orders",
        message: `Approve ${count} selected order${count === 1 ? "" : "s"}?`,
        confirmLabel: "Approve all",
      });
      if (!ok) return;
      try {
        await api("/batch-approve", { method: "PUT", body: JSON.stringify({
          order_ids: [...selected],
          approved_at: new Date().toISOString(),
          reviewed_by: session.analyst.analyst_id,
          review_comments: document.getElementById("aq-batch-comments")?.value || "",
        })});
        adminStatus(`${count} orders approved.`);
        selected = new Set();
        await refresh();
      } catch (ex) { adminStatus(ex.message, "error"); }
    });

    document.getElementById("aq-batch-reject")?.addEventListener("click", async () => {
      const comments = (document.getElementById("aq-batch-comments")?.value || "").trim();
      if (!selected.size) return adminStatus("Select at least one order.", "error");
      if (!comments) return adminStatus("Batch comments required for rejection.", "error");
      const count = selected.size;
      const ok = await confirmAction({
        title: "Reject selected orders",
        message: `Reject ${count} selected order${count === 1 ? "" : "s"} without marking as fraud?`,
        confirmLabel: "Reject all",
        danger: true,
      });
      if (!ok) return;
      try {
        await api("/batch-reject", { method: "PUT", body: JSON.stringify({
          order_ids: [...selected],
          rejected_at: new Date().toISOString(),
          reviewed_by: session.analyst.analyst_id,
          review_comments: comments,
          is_fraud: false,
        })});
        adminStatus(`${count} orders rejected.`);
        selected = new Set();
        await refresh();
      } catch (ex) { adminStatus(ex.message, "error"); }
    });

    document.getElementById("aq-batch-fraud")?.addEventListener("click", async () => {
      const comments = (document.getElementById("aq-batch-comments")?.value || "").trim();
      if (!selected.size) return adminStatus("Select at least one order.", "error");
      if (!comments) return adminStatus("Batch comments required to mark as fraud.", "error");
      const count = selected.size;
      const ok = await confirmAction({
        title: "Mark selected as fraud",
        message: `Mark ${count} selected order${count === 1 ? "" : "s"} as fraudulent and reject them?`,
        confirmLabel: "Mark as Fraud",
        danger: true,
      });
      if (!ok) return;
      try {
        await api("/batch-reject", { method: "PUT", body: JSON.stringify({
          order_ids: [...selected],
          rejected_at: new Date().toISOString(),
          reviewed_by: session.analyst.analyst_id,
          review_comments: comments,
          is_fraud: true,
        })});
        adminStatus(`${count} orders marked as fraud.`);
        selected = new Set();
        await refresh();
      } catch (ex) { adminStatus(ex.message, "error"); }
    });

    syncSelectionUI();
    await loadDetail();
  }

  async function loadDetail() {
    const detailEl = document.getElementById("aq-detail");
    if (!detailEl || !activeId) {
      if (detailEl) detailEl.innerHTML = "";
      return;
    }
    detailEl.innerHTML = `<p class="subtitle">${esc(t("loading_order", { id: activeId }))}</p>`;
    try {
      const detail = await api(`/portal/orders/${encodeURIComponent(activeId)}`);
      const order = detail.order;
      const bl = detail.blacklists || {};
      detailEl.innerHTML = `
        <div class="card">
          <h3>${esc(t("col_order_id"))} ${esc(order.order_id)} ${badge(order.order_status)}</h3>
          <div style="display:grid;gap:1rem;grid-template-columns:1fr 1fr">
            <div><strong>${esc(t("label_customer"))}</strong><br>${esc(order.customer_name)} (${esc(order.user_id)})<br>
              ${esc(t("email"))}: ${esc(order.email)}${bl.email ? ` (${esc(t("blacklisted_suffix"))})` : ""}<br>
              ${esc(t("phone"))}: ${esc(order.phone_number)}${bl.phone ? ` (${esc(t("blacklisted_suffix"))})` : ""}</div>
            <div><strong>${esc(t("order_details"))}</strong><br>${esc(order.product_name)} x${esc(order.quantity)}<br>
              ${money(order.amount)}<br>${esc(t("label_ip"))}: ${esc(order.ip_address)}${bl.ip ? ` (${esc(t("blacklisted_suffix"))})` : ""}</div>
          </div>
          <div class="alert alert-warning" style="margin-top:1rem">${esc(t("flagged_reason", { reason: order.flagged_reason }))}</div>
          <div class="field"><label>${esc(t("review_comments"))}</label><textarea id="aq-comments" rows="3">${esc(reviewComments)}</textarea></div>
          <div class="row-actions">
            <button type="button" class="btn btn-primary" id="aq-approve">${esc(t("approve_order"))}</button>
            <button type="button" class="btn btn-secondary" id="aq-reject">${esc(t("reject_order"))}</button>
            <button type="button" class="btn btn-fraud" id="aq-fraud">Mark as Fraud</button>
          </div>
        </div>`;

      document.getElementById("aq-comments")?.addEventListener("input", (e) => {
        reviewComments = e.target.value;
      });
      document.getElementById("aq-approve")?.addEventListener("click", async () => {
        const ok = await confirmAction({
          title: "Approve order",
          message: `Approve order ${activeId}? This will clear it from the review queue.`,
          confirmLabel: "Approve",
        });
        if (!ok) return;
        try {
          await api("/approve-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            approved_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: document.getElementById("aq-comments")?.value || "",
          })});
          adminStatus(`Order ${activeId} approved.`);
          await refresh();
        } catch (ex) { adminStatus(ex.message, "error"); }
      });
      document.getElementById("aq-reject")?.addEventListener("click", async () => {
        const comments = (document.getElementById("aq-comments")?.value || "").trim();
        if (!comments) return adminStatus("Comments required for rejection.", "error");
        const ok = await confirmAction({
          title: "Reject order",
          message: `Reject order ${activeId} without marking it as fraud? Use this for non-fraud reasons (e.g. inventory).`,
          confirmLabel: "Reject",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/reject-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: false,
          })});
          adminStatus(`Order ${activeId} rejected.`);
          await refresh();
        } catch (ex) { adminStatus(ex.message, "error"); }
      });
      document.getElementById("aq-fraud")?.addEventListener("click", async () => {
        const comments = (document.getElementById("aq-comments")?.value || "").trim();
        if (!comments) return adminStatus("Comments required to mark as fraud.", "error");
        const ok = await confirmAction({
          title: "Mark as fraud",
          message: `Mark order ${activeId} as fraudulent and reject it?`,
          confirmLabel: "Mark as Fraud",
          danger: true,
        });
        if (!ok) return;
        try {
          await api("/reject-order", { method: "PUT", body: JSON.stringify({
            order_id: activeId,
            rejected_at: new Date().toISOString(),
            reviewed_by: session.analyst.analyst_id,
            review_comments: comments,
            is_fraud: true,
          })});
          adminStatus(`Order ${activeId} marked as fraud.`);
          await refresh();
        } catch (ex) { adminStatus(ex.message, "error"); }
      });
    } catch (ex) {
      detailEl.innerHTML = `<div class="alert alert-error">${esc(ex.message)}</div>`;
    }
  }

  async function refresh() {
    const fresh = await api("/portal/queue");
    orders = fresh.orders || [];
    Object.assign(m, fresh.metrics || {});
    if (!orders.find((o) => o.order_id === activeId)) activeId = orders[0]?.order_id || "";
    queuePage = Math.min(queuePage, queuePageCount(orders.length));
    // Drop selected IDs that no longer exist
    selected = new Set([...selected].filter((id) => orders.some((o) => o.order_id === id)));
    await paintQueue();
  }

  await paintQueue();
}

function renderAdminBlacklists(body) {
  let type = "ip";
  const drafts = { ip: "", phone: "", email: "" };
  const entityMeta = {
    ip: {
      label: "IP Address",
      hint: "Network origin risk",
      placeholder: "e.g. 203.0.113.111",
      field: "IP Lookup",
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>`,
    },
    phone: {
      label: "Phone Number",
      hint: "Contact channel risk",
      placeholder: "e.g. +919876543210",
      field: "Phone Lookup",
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.13.81.36 1.6.7 2.34a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0122 16.92z"/></svg>`,
    },
    email: {
      label: "Email",
      hint: "Account identity risk",
      placeholder: "e.g. fraud@example.com",
      field: "Email Lookup",
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>`,
    },
  };

  body.innerHTML = `
    <div class="admin-feature-grid">
      <div class="card admin-feature-card">
        <h3>Choose entity type</h3>
        <p class="subtitle">Pick what you want to investigate, then look it up instantly.</p>
        <div class="bl-entity-grid" id="bl-type">
          ${Object.entries(entityMeta).map(([key, meta], i) => `
            <button type="button" class="bl-entity-card ${key === type ? "active" : ""}" data-type="${key}">
              <span class="bl-entity-icon">${meta.icon}</span>
              <span class="bl-entity-label">${esc(meta.label)}</span>
              <span class="bl-entity-hint">${esc(meta.hint)}</span>
            </button>`).join("")}
        </div>
      </div>
      <div class="card admin-feature-card">
        <h3 id="bl-heading">IP Lookup</h3>
        <p class="subtitle">Check status first — then blacklist or whitelist with a clear reason.</p>
        <div class="field"><label id="bl-label">IP Lookup</label><input id="bl-value" placeholder="e.g. 203.0.113.111" autocomplete="off" /></div>
        <div class="admin-inline-actions">
          <button type="button" class="btn btn-primary" id="bl-check">Check entity</button>
        </div>
        <div id="bl-result" class="bl-result-panel"></div>
      </div>
    </div>`;

  const input = document.getElementById("bl-value");

  function applyType(next) {
    drafts[type] = input.value;
    type = next;
    const meta = entityMeta[type];
    document.querySelectorAll("#bl-type .bl-entity-card").forEach((x) => {
      x.classList.toggle("active", x.dataset.type === type);
    });
    input.value = drafts[type] || "";
    input.placeholder = meta.placeholder;
    document.getElementById("bl-label").textContent = meta.field;
    document.getElementById("bl-heading").textContent = meta.field;
    document.getElementById("bl-result").innerHTML = "";
    input.focus();
  }

  document.querySelectorAll("#bl-type .bl-entity-card").forEach((b) => {
    b.addEventListener("click", () => applyType(b.dataset.type));
  });

  document.getElementById("bl-check").addEventListener("click", async () => {
    const value = input.value.trim();
    drafts[type] = input.value;
    const out = document.getElementById("bl-result");
    if (!value) return adminStatus("Enter a value to check.", "error");
    try {
      const res = await api(`/portal/blacklist/${type}/${encodeURIComponent(value)}`);
      if (res.entry) {
        out.innerHTML = `
          <div class="bl-status-card danger">
            <div class="bl-status-title">Currently blacklisted</div>
            <div class="bl-status-value">${esc(value)}</div>
            <p class="subtitle">Reason: ${esc(res.entry.reason)} · By: ${esc(res.entry.blacklisted_by_name || res.entry.blacklisted_by)} · Date: ${esc(String(res.entry.blacklisted_at || "").split("T")[0] || res.entry.blacklisted_at)}</p>
            <button type="button" class="btn btn-primary" id="bl-white">Whitelist this entity</button>
          </div>`;
        document.getElementById("bl-white").addEventListener("click", async () => {
          const ok = await confirmAction({
            title: "Whitelist entity",
            message: `Remove ${value} from the blacklist?`,
            confirmLabel: "Whitelist",
          });
          if (!ok) return;
          const ep = type === "ip" ? "whitelist-ip" : type === "phone" ? "whitelist-phone" : "whitelist-email";
          await api(`/${ep}`, { method: "PUT", body: JSON.stringify({
            blacklist_id: res.entry.blacklist_id,
            removed_by: session.analyst.analyst_id,
            removed_at: new Date().toISOString(),
          })});
          adminStatus(`${value} whitelisted.`);
          out.innerHTML = `<div class="bl-status-card success"><div class="bl-status-title">${esc(t("whitelisted"))}</div><div class="bl-status-value">${esc(value)}</div></div>`;
        });
      } else {
        out.innerHTML = `
          <div class="bl-status-card success">
            <div class="bl-status-title">Not on blacklist</div>
            <div class="bl-status-value">${esc(value)}</div>
            <div class="field"><label>Blacklist reason (required)</label><textarea id="bl-reason" rows="2" placeholder="Describe why this entity should be blocked"></textarea></div>
            <button type="button" class="btn btn-danger" id="bl-add">Blacklist this entity</button>
          </div>`;
        document.getElementById("bl-add").addEventListener("click", async () => {
          const reason = document.getElementById("bl-reason").value.trim();
          if (!reason) return adminStatus("A reason is required.", "error");
          const ok = await confirmAction({
            title: "Blacklist entity",
            message: `Blacklist ${value}?\n\nReason: ${reason}`,
            confirmLabel: "Blacklist",
            danger: true,
          });
          if (!ok) return;
          const ep = type === "ip" ? "blacklist-ip" : type === "phone" ? "blacklist-phone" : "blacklist-email";
          const payload = { reason, blacklisted_by: session.analyst.analyst_id };
          if (type === "ip") payload.ip_address = value;
          else if (type === "phone") payload.phone_number = value;
          else payload.email = value;
          await api(`/${ep}`, { method: "POST", body: JSON.stringify(payload) });
          adminStatus(`${value} blacklisted.`);
          out.innerHTML = `<div class="bl-status-card danger"><div class="bl-status-title">${esc(t("now_blacklisted"))}</div><div class="bl-status-value">${esc(value)}</div></div>`;
        });
      }
    } catch (ex) {
      adminStatus(ex.message, "error");
    }
  });
}

async function renderAdminPermissions(body) {
  const data = await api("/portal/permissions");
  const analysts = [...(data.analysts || [])].sort((a, b) =>
    String(a.employee_name || "").localeCompare(String(b.employee_name || "")),
  );
  // Keep page keys in the same official order as auth.ALL_PAGES
  const pageOrder = PAGE_ORDER;
  const pages = pageOrder.filter((p) => (data.all_pages || pageOrder).includes(p));

  if (!analysts.length) {
    body.innerHTML = `
      <div class="card admin-empty-card">
        <div class="admin-empty-icon">${adminTabIcon("users")}</div>
        <h3>No analysts to configure yet</h3>
        <p class="subtitle">Create a non-admin analyst in User Management, then return here to grant page access.</p>
      </div>`;
    return;
  }

  body.innerHTML = `
    <div class="card admin-feature-card">
      <div class="admin-card-head">
        <div>
          <h3 style="margin-bottom:0.35rem">Analyst Page Permissions</h3>
          <p class="subtitle" style="margin-top:0">Grant or revoke access to each page. Admins always have full access and are not listed here.</p>
        </div>
        <span class="admin-pill">${analysts.length} analyst${analysts.length === 1 ? "" : "s"}</span>
      </div>
      <div class="perm-layout">
        <div class="perm-analyst-row">
          <label for="perm-analyst">Select Analyst</label>
          <select id="perm-analyst">
            ${analysts.map((a) =>
              `<option value="${esc(a.analyst_id)}">${esc(a.employee_name)} — ${esc(a.username)} (${esc(a.role)})</option>`,
            ).join("")}
          </select>
        </div>
        <div>
          <p class="section-kicker" style="margin-bottom:0.65rem">Page Access</p>
          <div class="perm-grid" id="perm-checks"></div>
        </div>
        <div class="perm-actions">
          <label class="perm-confirm">
            <input type="checkbox" id="perm-confirm" />
            <span>I confirm these permission changes</span>
          </label>
          <button type="button" class="btn btn-primary" id="perm-save">Save Permissions</button>
        </div>
      </div>
    </div>`;

  function syncChecks() {
    const id = document.getElementById("perm-analyst").value;
    const analyst = analysts.find((a) => a.analyst_id === id);
    const granted = new Set(analyst?.granted_pages || []);
    document.getElementById("perm-checks").innerHTML = pages.map((p) => `
      <label class="perm-item">
        <input type="checkbox" data-page="${esc(p)}" ${granted.has(p) ? "checked" : ""} />
        <span class="perm-item-text">
          <span class="perm-item-title">${esc(data.page_labels?.[p] || pageLabel(p) || p)}</span>
          <span class="perm-item-key">${esc(p)}</span>
        </span>
      </label>`).join("");
  }

  syncChecks();
  document.getElementById("perm-analyst").addEventListener("change", syncChecks);
  document.getElementById("perm-save").addEventListener("click", async () => {
    if (!document.getElementById("perm-confirm").checked) {
      return adminStatus("Please confirm the permission changes.", "error");
    }
    const id = document.getElementById("perm-analyst").value;
    const analyst = analysts.find((a) => a.analyst_id === id);
    const name = analyst?.employee_name || id;
    const permissions = {};
    // Always send all pages in fixed order
    pages.forEach((p) => { permissions[p] = false; });
    document.querySelectorAll("#perm-checks input[data-page]").forEach((cb) => {
      permissions[cb.dataset.page] = cb.checked;
    });
    const grantedLabels = pages
      .filter((p) => permissions[p])
      .map((p) => data.page_labels?.[p] || pageLabel(p) || p);
    const proceed = await confirmAction({
      title: "Save permissions",
      message: `Save page permissions for ${name} (${id})? Granted: ${grantedLabels.length ? grantedLabels.join(", ") : "none"}.`,
      confirmLabel: "Save",
    });
    if (!proceed) return;
    try {
      await api("/permissions/bulk", {
        method: "PUT",
        body: JSON.stringify({
          analyst_id: id,
          permissions,
          granted_by: session.analyst.analyst_id,
        }),
      });
      const refreshed = await api("/portal/permissions");
      const sorted = [...(refreshed.analysts || [])].sort((a, b) =>
        String(a.employee_name || "").localeCompare(String(b.employee_name || "")),
      );
      analysts.splice(0, analysts.length, ...sorted);
      Object.assign(data, refreshed);
      document.getElementById("perm-confirm").checked = false;
      syncChecks();
      adminStatus("Permissions updated successfully.");
      await alertDialog({
        title: "Permissions saved",
        message: `Page permissions for ${name} (${id}) were updated successfully.`,
        confirmLabel: "OK",
      });
    } catch (ex) {
      adminStatus(ex.message, "error");
    }
  });
}

async function renderAdminUsers(body) {
  body.innerHTML = `
    <div class="admin-feature-grid">
      <div class="card admin-feature-card">
        <div class="admin-card-head">
          <div>
            <h3>${esc(t("create_analyst"))}</h3>
            <p class="subtitle">${esc(t("create_analyst_subtitle"))}</p>
          </div>
          <span class="admin-pill tone-teal">New hire</span>
        </div>
        <form id="create-analyst">
          <div style="display:grid;gap:0.75rem;grid-template-columns:1fr 1fr">
            <div class="field"><label>${esc(t("analyst_id"))}</label><input name="analyst_id" placeholder="e.g. A2" required /></div>
            <div class="field"><label>${esc(t("employee_name"))}</label><input name="employee_name" placeholder="e.g. Jane Doe" required /></div>
            <div class="field"><label>${esc(t("username"))}</label><input name="username" placeholder="e.g. jdoe" required /></div>
            <div class="field"><label>${esc(t("password"))}</label><input name="password" type="password" required /></div>
          </div>
          <div class="field">
            <label>${esc(t("role"))}</label>
            <select name="role">
              <option>Fraud Analyst</option>
              <option>Senior Fraud Analyst</option>
              <option>Admin</option>
            </select>
          </div>
          <label class="form-confirm" for="create-confirm">
            <input type="checkbox" id="create-confirm" />
            <span>${esc(t("confirm_create_analyst_chk"))}</span>
          </label>
          <button type="submit" class="btn btn-primary">${esc(t("create_analyst"))}</button>
        </form>
      </div>
      <div class="card admin-feature-card">
        <div class="admin-card-head">
          <div>
            <h3>${esc(t("team_pulse"))}</h3>
            <p class="subtitle">${esc(t("team_pulse_subtitle"))}</p>
          </div>
        </div>
        <div id="perf-stats" class="admin-mini-stats"></div>
        <div id="perf-table"><p class="subtitle">${esc(t("loading_ellipsis"))}</p></div>
      </div>
    </div>`;

  async function loadPerf() {
    const perf = await api("/portal/analytics/analyst-performance");
    const rows = perf.analysts || [];
    const reviewed = rows.reduce((s, a) => s + Number(a.orders_reviewed || 0), 0);
    const rejected = rows.reduce((s, a) => s + Number(a.orders_rejected || 0), 0);
    document.getElementById("perf-stats").innerHTML = `
      <div class="admin-mini-stat"><span class="admin-mini-stat-value">${rows.length}</span><span class="admin-mini-stat-label">${esc(t("analysts_count"))}</span></div>
      <div class="admin-mini-stat"><span class="admin-mini-stat-value">${reviewed}</span><span class="admin-mini-stat-label">${esc(t("reviewed"))}</span></div>
      <div class="admin-mini-stat"><span class="admin-mini-stat-value">${rejected}</span><span class="admin-mini-stat-label">${esc(t("rejected"))}</span></div>`;
    document.getElementById("perf-table").innerHTML = rows.length
      ? `<div class="table-scroll"><table><thead><tr><th>ID</th><th>Name</th><th>Role</th><th>Reviewed</th><th>Rejected</th></tr></thead>
         <tbody>${rows.map((a) => `<tr><td>${esc(a.analyst_id)}</td><td>${esc(a.employee_name)}</td><td>${esc(a.role)}</td><td>${esc(a.orders_reviewed)}</td><td>${esc(a.orders_rejected)}</td></tr>`).join("")}</tbody></table></div>`
      : `<p class="subtitle">${esc(t("no_analysts_found"))}</p>`;
  }

  document.getElementById("create-analyst").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = Object.fromEntries(fd.entries());

    if (!document.getElementById("create-confirm").checked) {
      await alertDialog({
        title: "Confirmation required",
        message: "Please check the confirmation box before creating the analyst profile.",
        confirmLabel: "OK",
      });
      return;
    }

    const proceed = await confirmAction({
      title: "Create analyst profile",
      message: `Create analyst profile for ${payload.employee_name} (${payload.analyst_id}) with role ${payload.role}?`,
      confirmLabel: "Create",
    });
    if (!proceed) return;

    try {
      await api("/create-analyst", { method: "POST", body: JSON.stringify(payload) });
      adminStatus(`Analyst ${payload.employee_name} created.`);
      e.target.reset();
      await loadPerf();
      await alertDialog({
        title: "Analyst created",
        message: `Analyst profile for ${payload.employee_name} (${payload.analyst_id}) was created successfully.`,
        confirmLabel: "OK",
      });
    } catch (ex) {
      adminStatus(ex.message, "error");
      await alertDialog({
        title: "Create failed",
        message: ex.message || "Could not create the analyst profile.",
        confirmLabel: "OK",
      });
    }
  });

  await loadPerf();
}

async function renderAdminAnalytics(body) {
  const summary = await api("/portal/analytics/summary");
  const k = summary.kpis;
  const recent = summary.recent_orders || [];
  const trend = summary.orders_over_time || [];
  let recentPage = 1;

  function recentRowsHtml(pageInfo) {
    if (!pageInfo.rows.length) {
      return `<tr><td colspan="6">No recent orders</td></tr>`;
    }
    return pageInfo.rows.map((r) => `<tr>
      <td>${esc(r.order_id)}</td><td>${esc(r.customer_name)}</td><td>${esc(r.product_name)}</td>
      <td>${money(r.amount)}</td><td>${badge(r.order_status)}</td><td>${esc(r.order_timestamp)}</td>
    </tr>`).join("");
  }

  function paintRecent() {
    const pageInfo = queuePageSlice(recent, recentPage);
    recentPage = pageInfo.page;
    const tbody = document.getElementById("ao-recent-body");
    const wrap = document.getElementById("ao-pager-wrap");
    if (tbody) tbody.innerHTML = recentRowsHtml(pageInfo);
    if (wrap) {
      wrap.innerHTML = pagerHtml({
        ...pageInfo,
        total: recent.length,
        prefix: "ao",
      }) || "";
      wrap.querySelectorAll(".pager-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const next = Number(btn.dataset.page);
          if (!Number.isFinite(next)) return;
          recentPage = next;
          paintRecent();
        });
      });
    }
  }

  const initialPage = queuePageSlice(recent, recentPage);

  body.innerHTML = `
    <div class="overview-grid overview-grid-3" style="margin-bottom:1.25rem">
      <div class="stat-card admin-stat-lift">
        <div class="stat-icon blue">${overviewIcon("orders")}</div>
        <div>
          <div class="stat-value">${Number(k.total_orders || 0).toLocaleString()}</div>
          <div class="stat-label">Total Orders</div>
        </div>
      </div>
      <div class="stat-card admin-stat-lift">
        <div class="stat-icon pink">${overviewIcon("fraud")}</div>
        <div>
          <div class="stat-value">${Number(k.total_fraud || 0).toLocaleString()}</div>
          <div class="stat-label">Total Fraud Orders</div>
        </div>
      </div>
      <div class="stat-card admin-stat-lift">
        <div class="stat-icon orange">${overviewIcon("rate")}</div>
        <div>
          <div class="stat-value">${Number(k.fraud_rate || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}%</div>
          <div class="stat-label">Fraud Rate</div>
        </div>
      </div>
    </div>
    <div class="analytics-grid">
      <div class="card admin-feature-card">
        <div class="admin-card-head">
          <div>
            <h3 style="margin:0">Order Status Distribution</h3>
            <p class="subtitle" style="margin:0.25rem 0 0">Share of all orders by current status</p>
          </div>
        </div>
        ${buildStatusDistribution(k.status_counts || {})}
      </div>
      <div class="card admin-feature-card">
        <div class="admin-card-head">
          <div>
            <h3 style="margin:0">Daily Order Volume — Current Month</h3>
            <p class="subtitle" style="margin:0.25rem 0 0">Orders placed each day this month</p>
          </div>
        </div>
        ${buildDailyVolumeLine(trend)}
      </div>
    </div>
    <div class="card admin-feature-card">
      <div class="section-head" style="margin-bottom:0.75rem">
        <h3 style="margin:0">Recent Orders</h3>
        <p class="subtitle" style="margin:0">${recent.length} total · ${QUEUE_PAGE_SIZE} rows per page</p>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Status</th><th>Placed</th></tr></thead>
          <tbody id="ao-recent-body">${recentRowsHtml(initialPage)}</tbody>
        </table>
      </div>
      <div id="ao-pager-wrap">${pagerHtml({
        ...initialPage,
        total: recent.length,
        prefix: "ao",
      })}</div>
    </div>`;

  document.querySelectorAll("#ao-pager-wrap .pager-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = Number(btn.dataset.page);
      if (!Number.isFinite(next)) return;
      recentPage = next;
      paintRecent();
    });
  });
}

const STATUS_CHART_COLORS = {
  PENDING_REVIEW: "#f59e0b",
  ON_HOLD: "#3b82f6",
  APPROVED: "#10b981",
  COMPLETED: "#059669",
  REJECTED: "#ef4444",
  CANCELLED: "#94a3b8",
};

const STATUS_LABELS = {
  PENDING_REVIEW: "Pending Review",
  ON_HOLD: "On Hold",
  APPROVED: "Approved",
  COMPLETED: "Completed",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
};

function statusChartColor(status, index) {
  if (STATUS_CHART_COLORS[status]) return STATUS_CHART_COLORS[status];
  const fallback = ["#1a237e", "#00897b", "#5e35b1", "#ec407a", "#6d4c41", "#546e7a"];
  return fallback[index % fallback.length];
}

function statusDisplayName(status) {
  return STATUS_LABELS[status] || String(status || "").replaceAll("_", " ");
}

function buildStatusDistribution(statusCounts) {
  const preferredOrder = ["APPROVED", "REJECTED", "PENDING_REVIEW", "ON_HOLD", "COMPLETED", "CANCELLED"];
  const raw = Object.entries(statusCounts || {}).map(([status, count]) => ({
    status,
    count: Number(count) || 0,
  }));
  const known = preferredOrder
    .filter((s) => raw.some((e) => e.status === s))
    .map((s) => raw.find((e) => e.status === s));
  const extras = raw
    .filter((e) => !preferredOrder.includes(e.status))
    .sort((a, b) => b.count - a.count);
  const entries = [...known, ...extras].filter((e) => e.count > 0);

  if (!entries.length) {
    return `<div class="alert alert-info">No order status data available.</div>`;
  }

  const total = entries.reduce((sum, e) => sum + e.count, 0) || 1;
  const size = 220;
  const radius = 78;
  const stroke = 34;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  const rings = entries.map((e, i) => {
    const frac = e.count / total;
    const dash = frac * circumference;
    const gap = circumference - dash;
    const color = statusChartColor(e.status, i);
    const label = statusDisplayName(e.status);
    const pct = ((e.count / total) * 100).toFixed(1);
    const circle = `<circle class="donut-segment" cx="${size / 2}" cy="${size / 2}" r="${radius}"
      fill="transparent" stroke="${color}" stroke-width="${stroke}" stroke-linecap="butt"
      stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-offset}"
      transform="rotate(-90 ${size / 2} ${size / 2})">
      <title>${esc(label)}: ${e.count.toLocaleString()} (${pct}%)</title>
    </circle>`;
    offset += dash;
    return circle;
  }).join("");

  const rows = entries.map((e, i) => {
    const pct = (e.count / total) * 100;
    const color = statusChartColor(e.status, i);
    return `
      <div class="status-dist-row">
        <div class="status-dist-meta">
          <span class="status-dist-swatch" style="background:${color}"></span>
          <span class="status-dist-name">${esc(statusDisplayName(e.status))}</span>
          <span class="status-dist-count">${e.count.toLocaleString()}</span>
          <span class="status-dist-pct">${pct.toFixed(1)}%</span>
        </div>
        <div class="status-dist-track" aria-hidden="true">
          <div class="status-dist-fill" style="width:${Math.max(pct, 0.8)}%;background:${color}"></div>
        </div>
      </div>`;
  }).join("");

  return `
    <div class="status-dist">
      <div class="status-dist-visual">
        <div class="analytics-donut status-dist-donut">
          <svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="Order status distribution">
            <circle cx="${size / 2}" cy="${size / 2}" r="${radius}" fill="transparent" stroke="#eef2f7" stroke-width="${stroke}"></circle>
            ${rings}
          </svg>
          <div class="donut-center">
            <div class="donut-total">${total.toLocaleString()}</div>
            <div class="donut-label">Total orders</div>
          </div>
        </div>
      </div>
      <div class="status-dist-list">${rows}</div>
    </div>`;
}

function buildDailyVolumeLine(trend) {
  const points = (trend || []).map((r) => ({
    date: String(r.order_date || ""),
    count: Number(r.order_count) || 0,
  }));

  if (!points.length) {
    return `<div class="alert alert-info">No orders placed yet this month.</div>`;
  }

  const w = 640;
  const h = 220;
  const padL = 40;
  const padR = 16;
  const padT = 16;
  const padB = 36;
  const maxY = Math.max(...points.map((p) => p.count), 1);
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const coords = points.map((p, i) => {
    const x = padL + (points.length === 1 ? plotW / 2 : (i * plotW) / (points.length - 1));
    const y = padT + plotH - (p.count / maxY) * plotH;
    return { ...p, x, y };
  });

  const line = coords.map((c) => `${c.x},${c.y}`).join(" ");
  const area = `M ${coords[0].x},${padT + plotH} L ${coords.map((c) => `${c.x},${c.y}`).join(" L ")} L ${coords[coords.length - 1].x},${padT + plotH} Z`;
  const gridYs = [0, 0.25, 0.5, 0.75, 1].map((t) => {
    const y = padT + plotH - t * plotH;
    const val = Math.round(maxY * t);
    return `<line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="#eef1f7" stroke-width="1" />
      <text x="${padL - 8}" y="${y + 4}" text-anchor="end" class="chart-axis-text">${val}</text>`;
  }).join("");

  // Show up to ~8 x labels to avoid clutter
  const labelStep = Math.max(1, Math.ceil(coords.length / 8));
  const xLabels = coords.map((c, i) => {
    if (i % labelStep !== 0 && i !== coords.length - 1) return "";
    const short = c.date.length >= 10 ? c.date.slice(5) : c.date; // MM-DD
    return `<text x="${c.x}" y="${h - 10}" text-anchor="middle" class="chart-axis-text">${esc(short)}</text>`;
  }).join("");

  const dots = coords.map((c) => `
    <circle cx="${c.x}" cy="${c.y}" r="3.5" fill="#1976d2">
      <title>${esc(c.date)}: ${c.count} order${c.count === 1 ? "" : "s"}</title>
    </circle>`).join("");

  return `
    <div class="analytics-line-wrap">
      <svg viewBox="0 0 ${w} ${h}" class="analytics-line-svg" role="img" aria-label="Daily order volume line chart">
        ${gridYs}
        <path d="${area}" fill="rgba(25,118,210,0.12)" stroke="none"></path>
        <polyline fill="none" stroke="#1976d2" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="${line}"></polyline>
        ${dots}
        ${xLabels}
      </svg>
      <p class="subtitle" style="margin:0.35rem 0 0">Hover points for exact daily counts · ${points.length} day${points.length === 1 ? "" : "s"} shown</p>
    </div>`;
}

const RULE_ACTIONS = ["HOLD", "REVIEW", "REJECTED", "PASS"];

const RULE_ACTION_HELP = {
  HOLD: "Places matching orders ON HOLD for the configured time window before release.",
  REVIEW: "Sends matching orders to PENDING REVIEW for analyst decision.",
  REJECTED: "Automatically rejects matching orders and marks them as fraud.",
  PASS: "Allows matching orders through as APPROVED (softest outcome when this rule fires).",
};

function describeRuleConfig(rule) {
  const name = rule.rule_name || "This rule";
  const type = rule.rule_type;
  const action = String(rule.action || "REVIEW").toUpperCase();
  const threshold = rule.threshold_value;
  const intervalVal = rule.time_interval_value;
  const intervalUnit = rule.time_interval_unit;

  if (rule.rule_id === "R001") {
    return `Flags P2 iPhone 16 orders for ${action} based on the configured hold window.`;
  }
  if (String(name).toLowerCase().includes("blacklist")) {
    return `Automatically applies ${action} to any order matching a blacklisted entity.`;
  }
  if (["VELOCITY", "BEHAVIORAL"].includes(type) && threshold != null && intervalVal != null) {
    const unit = String(intervalUnit || "interval").toLowerCase();
    return `Triggers ${action} when orders exceed ${threshold} within ${intervalVal} ${unit}(s).`;
  }
  if (type === "LINKAGE" && threshold != null) {
    return `Triggers ${action} when ${threshold} or more linked entities are detected on an order.`;
  }
  return `Triggers ${action} based on the ${type} detection logic configured for this rule.`;
}

async function renderAdminRules(body) {
  const data = await api("/portal/rules");
  const rules = data.rules || [];
  if (!rules.length) {
    body.innerHTML = `<div class="card"><h3>Rule Management</h3><div class="alert alert-info">No rules found in the database.</div></div>`;
    return;
  }

  body.innerHTML = `
    <div class="analytics-grid rule-charts-grid" style="margin-bottom:1rem">
      <div class="card rule-chart-card admin-feature-card">
        <h3>Rule Trigger Statistics</h3>
        <p class="subtitle">How often automated fraud rules are firing.</p>
        <div id="rule-stats-chart" class="rule-chart-body"><p class="subtitle">${esc(t("loading_ellipsis"))}</p></div>
      </div>
      <div class="card rule-chart-card admin-feature-card">
        <h3>Rule Trigger Status</h3>
        <p class="subtitle">Trigger volume by configured rule action.</p>
        <div id="rule-status-chart" class="rule-chart-body"><p class="subtitle">${esc(t("loading_ellipsis"))}</p></div>
      </div>
    </div>
    <div class="card admin-feature-card">
      <div class="admin-card-head">
        <div>
          <h3>Rule Configuration Management</h3>
          <p class="subtitle">Adjust actions, thresholds, and time windows — changes go live for new orders immediately.</p>
        </div>
      </div>
      <div class="field">
        <label>Select Rule</label>
        <select id="rule-select">
          ${rules.map((r) => `<option value="${esc(r.rule_id)}">${esc(r.rule_id)} — ${esc(r.rule_name)}</option>`).join("")}
        </select>
      </div>
      <div id="rule-form"></div>
    </div>`;

  try {
    const stats = await api("/portal/analytics/rule-stats");
    const rows = stats.rules || [];
    document.getElementById("rule-stats-chart").innerHTML = buildRuleTriggerBars(rows);
    document.getElementById("rule-status-chart").innerHTML = buildRuleStatusBars(rows);
  } catch {
    document.getElementById("rule-stats-chart").innerHTML = `<p class="subtitle">${esc(t("could_not_load_rule_stats"))}</p>`;
    document.getElementById("rule-status-chart").innerHTML = `<p class="subtitle">${esc(t("could_not_load_rule_status"))}</p>`;
  }

  async function refreshRuleCharts() {
    try {
      const stats = await api("/portal/analytics/rule-stats");
      const rows = stats.rules || [];
      document.getElementById("rule-stats-chart").innerHTML = buildRuleTriggerBars(rows);
      document.getElementById("rule-status-chart").innerHTML = buildRuleStatusBars(rows);
    } catch {
      /* keep existing charts */
    }
  }

  function paintRule() {
    const id = document.getElementById("rule-select").value;
    const r = rules.find((x) => x.rule_id === id);
    if (!r) return;

    const isR001 = r.rule_id === "R001";
    const isBlacklist = String(r.rule_name || "").toLowerCase().includes("blacklist");
    const locked = isR001 || isBlacklist;
    const currentAction = String(r.action || "REVIEW").toUpperCase();
    const lockedAction = isR001 ? "HOLD" : isBlacklist ? "REJECTED" : currentAction;
    const requiresInterval = (["VELOCITY", "BEHAVIORAL"].includes(r.rule_type) || isR001) && !isBlacklist;
    const requiresThreshold = ["VELOCITY", "BEHAVIORAL", "LINKAGE"].includes(r.rule_type) && !isBlacklist;

    document.getElementById("rule-form").innerHTML = `
      <p id="rule-live-desc"><strong>Description:</strong> ${esc(describeRuleConfig({
        ...r,
        action: lockedAction,
      }))}</p>
      <p><strong>Detection Type:</strong> <code>${esc(r.rule_type)}</code></p>
      ${locked ? `<div class="alert alert-info">Action is locked to <strong>${esc(lockedAction)}</strong> for this rule.</div>` : ""}
      <div class="field">
        <label>Rule Action</label>
        <select id="rule-action" ${locked ? "disabled" : ""}>
          ${RULE_ACTIONS.map((a) =>
            `<option value="${a}" ${a === lockedAction ? "selected" : ""}>${a} — ${esc(RULE_ACTION_HELP[a].split(".")[0])}</option>`,
          ).join("")}
        </select>
        <p class="subtitle" id="rule-action-help">${esc(RULE_ACTION_HELP[lockedAction])}</p>
      </div>
      <div style="display:grid;gap:0.75rem;grid-template-columns:1fr 1fr 1fr">
        <div class="field">
          <label>Threshold</label>
          ${requiresThreshold
            ? `<input id="rule-threshold" type="number" min="0" step="1" value="${r.threshold_value ?? 0}" />`
            : `<p class="subtitle">N/A</p>`}
        </div>
        <div class="field">
          <label>Time Interval</label>
          ${requiresInterval
            ? `<input id="rule-interval" type="number" min="1" step="1" value="${r.time_interval_value ?? 1}" />`
            : `<p class="subtitle">N/A</p>`}
        </div>
        <div class="field">
          <label>Unit</label>
          ${requiresInterval
            ? `<select id="rule-unit">${["MINUTE", "HOUR", "DAY", "WEEK"].map((u) =>
                `<option value="${u}" ${(r.time_interval_unit || "MINUTE") === u ? "selected" : ""}>${u}</option>`).join("")}</select>`
            : `<p class="subtitle">N/A</p>`}
        </div>
      </div>
      <button type="button" class="btn btn-primary" id="rule-save">Save Rule Changes</button>`;

    function readFormState() {
      const action = locked
        ? lockedAction
        : (document.getElementById("rule-action")?.value || lockedAction);
      return {
        ...r,
        action,
        threshold_value: requiresThreshold
          ? Number(document.getElementById("rule-threshold").value)
          : r.threshold_value,
        time_interval_value: requiresInterval
          ? Number(document.getElementById("rule-interval").value)
          : r.time_interval_value,
        time_interval_unit: requiresInterval
          ? document.getElementById("rule-unit").value
          : r.time_interval_unit,
      };
    }

    function syncActionUi() {
      const state = readFormState();
      const help = document.getElementById("rule-action-help");
      const desc = document.getElementById("rule-live-desc");
      if (help) help.textContent = RULE_ACTION_HELP[state.action] || "";
      if (desc) desc.innerHTML = `<strong>Description:</strong> ${esc(describeRuleConfig(state))}`;
    }

    const actionEl = document.getElementById("rule-action");
    if (actionEl && !locked) actionEl.addEventListener("change", syncActionUi);
    ["rule-threshold", "rule-interval", "rule-unit"].forEach((fid) => {
      const el = document.getElementById(fid);
      if (el) el.addEventListener("input", syncActionUi);
      if (el) el.addEventListener("change", syncActionUi);
    });

    document.getElementById("rule-save").addEventListener("click", async () => {
      const state = readFormState();
      if (requiresThreshold && !(state.threshold_value >= 0)) {
        return adminStatus("Threshold must be 0 or greater.", "error");
      }
      if (requiresInterval && !(state.time_interval_value >= 1)) {
        return adminStatus("Time interval must be at least 1.", "error");
      }

      const payload = {
        rule_id: r.rule_id,
        action: state.action,
        threshold_value: requiresThreshold ? state.threshold_value : null,
        time_interval_value: requiresInterval ? state.time_interval_value : null,
        time_interval_unit: requiresInterval ? state.time_interval_unit : null,
      };

      const confirmed = await confirmAction({
        title: `Update rule ${r.rule_id}?`,
        message:
          `Apply action ${payload.action} to ${r.rule_name}.\n\n` +
          `${RULE_ACTION_HELP[payload.action]}\n\n` +
          describeRuleConfig(state),
        confirmLabel: "Yes, update rule",
      });
      if (!confirmed) return;

      try {
        await api("/update-rule", { method: "PUT", body: JSON.stringify(payload) });
        const refreshed = await api("/portal/rules");
        rules.splice(0, rules.length, ...(refreshed.rules || []));
        await refreshRuleCharts();
        adminStatus(`Rule ${r.rule_id} updated — action ${payload.action} is now live.`);
        await confirmAction({
          title: "Rule updated",
          message: `Rule ${r.rule_id} now applies ${payload.action} when triggered.\n\n${RULE_ACTION_HELP[payload.action]}`,
          alertOnly: true,
          confirmLabel: "OK",
        });
        paintRule();
      } catch (ex) {
        adminStatus(ex.message, "error");
      }
    });
  }

  document.getElementById("rule-select").addEventListener("change", paintRule);
  paintRule();
}

const RULE_ACTION_COLORS = {
  HOLD: "#0284c8",
  REVIEW: "#d97706",
  REJECTED: "#e11d48",
  PASS: "#059669",
};

const RULE_STATS_PALETTE = [
  "#0f766e",
  "#0369a1",
  "#1d4ed8",
  "#b45309",
  "#be123c",
  "#15803d",
  "#0e7490",
  "#334155",
  "#c2410c",
  "#1e3a8a",
];

function ruleStatsBarStyle(index) {
  const base = RULE_STATS_PALETTE[index % RULE_STATS_PALETTE.length];
  return `background:linear-gradient(90deg, ${base}, ${base}cc); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.12);`;
}

function ruleStatusBarStyle(action, index) {
  const base = RULE_ACTION_COLORS[action] || RULE_STATS_PALETTE[index % RULE_STATS_PALETTE.length];
  return `background:linear-gradient(180deg, ${base}, ${base}b3); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14);`;
}

function buildRuleTriggerBars(rows) {
  const items = (rows || [])
    .map((r) => ({
      id: String(r.rule_id || ""),
      name: String(r.rule_name || ""),
      label: `${r.rule_id || ""}`,
      full: `${r.rule_id || ""} — ${r.rule_name || ""}`,
      count: Number(r.times_triggered) || 0,
      action: String(r.action || ""),
    }))
    .sort((a, b) => b.count - a.count);

  if (!items.length) {
    return `<div class="alert alert-info">No rule trigger data available.</div>`;
  }

  const max = Math.max(...items.map((i) => i.count), 1);
  const bars = items.map((item, i) => {
    const pct = Math.max(4, Math.round((item.count / max) * 100));
    const color = RULE_STATS_PALETTE[i % RULE_STATS_PALETTE.length];
    return `<div class="rule-bar-row" title="${esc(item.full)}: ${item.count} triggers (${esc(item.action || "—")})">
      <div class="rule-bar-label">
        <strong>${esc(item.label)}</strong>
        <span>${esc(item.name)}</span>
      </div>
      <div class="rule-bar-track">
        <div class="rule-bar-fill" style="width:${pct}%;${ruleStatsBarStyle(i)}"></div>
      </div>
      <div class="rule-bar-value" style="color:${color}">${item.count.toLocaleString()}</div>
    </div>`;
  }).join("");

  return `<div class="rule-bar-chart">${bars}</div>`;
}

function buildRuleStatusBars(rows) {
  const totals = {};
  (rows || []).forEach((r) => {
    const action = String(r.action || "UNKNOWN");
    totals[action] = (totals[action] || 0) + (Number(r.times_triggered) || 0);
  });

  const order = ["HOLD", "REVIEW", "REJECTED", "PASS"];
  const items = [
    ...order.filter((a) => a in totals).map((a) => ({ action: a, count: totals[a] })),
    ...Object.keys(totals)
      .filter((a) => !order.includes(a))
      .map((a) => ({ action: a, count: totals[a] })),
  ];

  if (!items.length || items.every((i) => i.count === 0)) {
    return `<div class="alert alert-info">No rule trigger status data available.</div>`;
  }

  const max = Math.max(...items.map((i) => i.count), 1);
  const total = items.reduce((s, i) => s + i.count, 0);

  const legend = items.map((item, i) => {
    const color = RULE_ACTION_COLORS[item.action] || RULE_STATS_PALETTE[i % RULE_STATS_PALETTE.length];
    return `<div class="legend-item"><span class="legend-dot" style="background:${color}"></span>${esc(item.action)}</div>`;
  }).join("");

  const cols = items.map((item, i) => {
    const h = Math.max(8, Math.round((item.count / max) * 160));
    const color = RULE_ACTION_COLORS[item.action] || RULE_STATS_PALETTE[i % RULE_STATS_PALETTE.length];
    const pct = total ? ((item.count / total) * 100).toFixed(1) : "0.0";
    return `<div class="rule-status-col" title="${esc(item.action)}: ${item.count} (${pct}%)">
      <div class="rule-status-value" style="color:${color}">${item.count.toLocaleString()}</div>
      <div class="rule-status-bar" style="height:${h}px;${ruleStatusBarStyle(item.action, i)}"></div>
      <div class="rule-status-label">${esc(item.action)}</div>
      <div class="rule-status-pct">${pct}%</div>
    </div>`;
  }).join("");

  return `
    <div class="rule-status-chart">
      <div class="chart-legend" style="justify-content:flex-start;margin:0 0 0.75rem">${legend}</div>
      <div class="rule-status-bars">${cols}</div>
      <p class="subtitle" style="margin:0.75rem 0 0">Total triggers across actions: <strong>${total.toLocaleString()}</strong></p>
    </div>`;
}

async function renderPowerBi() {
  let content = `<h1>Analytics Dashboards</h1><p class="subtitle">Loading Power BI...</p>`;
  document.getElementById("app").innerHTML = shell(content, "analytics");
  bindShell();
  try {
    const data = await api("/portal/power-bi");
    content = `<h1>Analytics Dashboards</h1><div class="pbi-frame"><iframe src="${esc(data.embed_url)}" title="Power BI" allowfullscreen></iframe></div>`;
  } catch (ex) {
    content = `<h1>Analytics Dashboards</h1><div class="alert alert-error">${esc(ex.message)}</div>`;
  }
  document.getElementById("app").innerHTML = shell(content, "analytics");
  bindShell();
}

function formatInsightText(text) {
  return esc(text || "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (block) => `<ul class="chat-insight-list">${block.replace(/\n/g, "")}</ul>`)
    .replace(/\n/g, "<br>");
}

const CHART_TAB_LABELS = {
  metric: "Metric",
  bar: "Bar",
  hbar: "Horizontal",
  line: "Line",
  area: "Area",
  pie: "Pie",
  table: "Table",
};

const CHART_COLORS = ["#1a237e", "#1976d2", "#00897b", "#fb8c00", "#ec407a", "#5e35b1", "#43a047", "#6d4c41"];

function renderChartBody(chart, chartType) {
  if (!chart) return "";
  if (chartType === "metric" || chart.type === "metric") {
    const value = typeof chart.value === "number"
      ? chart.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : String(chart.value ?? (chart.values || [])[0] ?? "—");
    return `<div class="chat-metric"><div class="chat-metric-value">${esc(value)}</div><div class="chat-metric-label">${esc(chart.label || chart.y_label || "Result")}</div></div>`;
  }

  const labels = chart.labels || [];
  const values = (chart.values || []).map(Number);
  if (!labels.length || !values.length) {
    return `<p class="subtitle">No chartable series in this result.</p>`;
  }

  const max = Math.max(...values, 1);

  if (chartType === "table") {
    return `<div class="table-scroll"><table>
      <thead><tr><th>${esc(chart.x_label || "Category")}</th><th>${esc(chart.y_label || "Value")}</th></tr></thead>
      <tbody>${labels.map((label, i) => `<tr><td>${esc(label)}</td><td>${esc(String(values[i]))}</td></tr>`).join("")}</tbody>
    </table></div>`;
  }

  if (chartType === "pie") {
    const total = values.reduce((a, b) => a + b, 0) || 1;
    let cursor = 0;
    const stops = values.map((v, i) => {
      const start = cursor;
      cursor += (v / total) * 360;
      return `${CHART_COLORS[i % CHART_COLORS.length]} ${start}deg ${cursor}deg`;
    }).join(", ");
    const legend = labels.map((label, i) => (
      `<div class="legend-item"><span class="legend-dot" style="background:${CHART_COLORS[i % CHART_COLORS.length]}"></span>${esc(label)} (${esc(String(values[i]))})</div>`
    )).join("");
    return `<div class="chat-pie-wrap">
      <div class="chat-pie" style="background:conic-gradient(${stops})"></div>
      <div class="chart-legend">${legend}</div>
    </div>`;
  }

  if (chartType === "hbar") {
    return `<div class="chat-hbars">${labels.map((label, i) => {
      const w = Math.max(6, Math.round((values[i] / max) * 100));
      const color = CHART_COLORS[i % CHART_COLORS.length];
      return `<div class="chat-hbar-row" title="${esc(label)}: ${esc(String(values[i]))}">
        <span class="chat-hbar-label">${esc(label)}</span>
        <div class="chat-hbar-track"><div class="chat-hbar-fill" style="width:${w}%;background:${color}"></div></div>
        <span class="chat-hbar-value">${esc(String(values[i]))}</span>
      </div>`;
    }).join("")}</div>`;
  }

  if (chartType === "line" || chartType === "area") {
    const w = 420;
    const h = 180;
    const pad = 16;
    const pts = values.map((v, i) => {
      const x = pad + (i * (w - pad * 2)) / Math.max(values.length - 1, 1);
      const y = h - pad - ((v / max) * (h - pad * 2));
      return [x, y];
    });
    const polyline = pts.map(([x, y]) => `${x},${y}`).join(" ");
    const areaPath = `M ${pts[0][0]},${h - pad} L ${polyline.replace(/ /g, " L ")} L ${pts[pts.length - 1][0]},${h - pad} Z`;
    const dots = pts.map(([x, y], i) => (
      `<circle cx="${x}" cy="${y}" r="3.5" fill="${CHART_COLORS[i % CHART_COLORS.length]}"><title>${esc(labels[i])}: ${esc(String(values[i]))}</title></circle>`
    )).join("");
    return `<div class="chat-svg-wrap">
      <svg viewBox="0 0 ${w} ${h}" class="chat-line-svg" role="img" aria-label="${esc(chartType)} chart">
        ${chartType === "area" ? `<path d="${areaPath}" fill="rgba(25,118,210,0.18)" stroke="none"></path>` : ""}
        <polyline fill="none" stroke="#1976d2" stroke-width="2.5" points="${polyline}"></polyline>
        ${dots}
      </svg>
      <div class="chat-bar-labels">${labels.map((l) => `<span>${esc(l)}</span>`).join("")}</div>
    </div>`;
  }

  // Default: vertical bar
  const bars = labels.map((label, i) => {
    const h = Math.max(10, Math.round((values[i] / max) * 160));
    const color = CHART_COLORS[i % CHART_COLORS.length];
    return `<div class="chat-bar-col" title="${esc(label)}: ${esc(String(values[i]))}">
      <div class="chat-bar" style="height:${h}px;background:${color}"></div>
      <span class="chat-bar-label">${esc(label)}</span>
    </div>`;
  }).join("");
  return `<div class="chat-bars">${bars}</div>`;
}

function buildChatChart(chart, msgIndex = 0, selectedType = null) {
  if (!chart) return "";

  const types = (chart.types && chart.types.length)
    ? chart.types
    : (chart.type === "metric" ? ["metric"] : ["bar", "hbar", "line", "area", "pie", "table"]);
  const active = selectedType || chart.selectedType || chart.type || types[0];
  const showTabs = types.length > 1 && chart.type !== "metric";

  const tabs = showTabs
    ? `<div class="chat-chart-tabs" role="tablist">
        ${types.map((t) => `<button type="button" class="chat-chart-tab ${t === active ? "active" : ""}" data-msg-idx="${msgIndex}" data-chart-type="${esc(t)}" role="tab" aria-selected="${t === active}">${esc(CHART_TAB_LABELS[t] || t)}</button>`).join("")}
      </div>`
    : "";

  return `<div class="chat-viz" data-msg-idx="${msgIndex}">
    <div class="chat-viz-title">Visualization</div>
    ${tabs}
    <div class="chat-chart-body">${renderChartBody(chart, active)}</div>
    ${chart.x_label || chart.y_label
      ? `<div class="chat-viz-axes">${esc(chart.x_label || "X")} vs ${esc(chart.y_label || "Y")}</div>`
      : ""}
  </div>`;
}

function buildAssistantBubble(m, msgIndex = 0) {
  const insightTitle = esc(m.insight_title || "AI Insights");
  const insights = m.content
    ? `<div class="chat-insights"><div class="chat-section-title">${insightTitle}</div><div class="chat-insight-body">${formatInsightText(m.content)}</div></div>`
    : "";
  const advice = (m.business_advice || []).length
    ? `<div class="chat-advice"><div class="chat-section-title">Business Advice</div><ul>${m.business_advice.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>`
    : "";
  const viz = buildChatChart(m.chart, msgIndex, m.chartType || null);
  const rows = m.rows?.length
    ? `<details class="chat-data"><summary>View result data (${m.rows.length} row${m.rows.length === 1 ? "" : "s"})</summary>
        <div class="table-scroll"><table><thead><tr>${Object.keys(m.rows[0]).map((k) => `<th>${esc(k)}</th>`).join("")}</tr></thead>
        <tbody>${m.rows.map((row) => `<tr>${Object.values(row).map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      </details>`
    : "";
  const followups = (m.followups || []).length
    ? `<div class="chat-followups"><div class="chat-section-title">Suggested follow-up questions</div>
        <div class="chat-followup-list">${m.followups.map((q) => `<button type="button" class="chat-followup-btn" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      </div>`
    : "";
  return `<div class="gpt-row gpt-row-assistant">
    <div class="gpt-avatar gpt-avatar-ai" aria-hidden="true">AI</div>
    <div class="gpt-bubble gpt-bubble-assistant">${insights}${viz}${advice}${rows}${followups}</div>
  </div>`;
}

async function renderChatbot() {
  const examples = [
    { title: t("chat_ex_fraud_title"), prompt: t("chatbot_example_1") },
    { title: t("chat_ex_region_title"), prompt: t("chatbot_example_2") },
    { title: t("chat_ex_best_title"), prompt: t("chatbot_example_5") },
  ];
  document.getElementById("app").innerHTML = shell(`
    <div class="gpt-shell">
      <header class="gpt-top">
        <div>
          <h1 class="gpt-title">${esc(t("nav_analytics_ai"))}</h1>
          <p class="gpt-subtitle">${esc(t("chatbot_subtitle"))}</p>
        </div>
        <button type="button" class="btn btn-secondary" id="chat-clear">${esc(t("chat_new"))}</button>
      </header>
      <div class="gpt-messages" id="chat-log"></div>
      <div class="gpt-composer-wrap">
        <form id="chat-form" class="gpt-composer">
          <textarea id="chat-input" rows="1" placeholder="${esc(t("chat_placeholder"))}" ></textarea>
          <button class="gpt-send" type="submit" title="Send" aria-label="Send">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </form>
        <p class="gpt-disclaimer">${esc(t("chat_disclaimer"))}</p>
      </div>
    </div>
  `, "chatbot");
  bindShell();

  function emptyStateHtml() {
    return `<div class="gpt-empty">
      <div class="gpt-empty-icon">AI</div>
      <h2>${esc(t("chat_empty_title"))}</h2>
      <p>${esc(t("chat_empty_hint"))}</p>
      <div class="gpt-suggestions">
        ${examples.map((e) => `
          <button type="button" class="gpt-suggestion example-btn" data-prompt="${esc(e.prompt)}">
            <strong>${esc(e.title)}</strong>
            <span>${esc(e.prompt)}</span>
          </button>`).join("")}
      </div>
    </div>`;
  }

  function paintChat(opts = {}) {
    const stickBottom = opts.stickBottom !== false;
    const log = document.getElementById("chat-log");
    if (!log) return;
    const prevScroll = log.scrollTop;

    if (!chatMessages.length) {
      log.innerHTML = emptyStateHtml();
      log.classList.add("is-empty");
      document.querySelectorAll(".example-btn").forEach((b) => {
        b.onclick = () => send(b.getAttribute("data-prompt") || b.textContent || "");
      });
      return;
    }

    log.classList.remove("is-empty");
    log.innerHTML = chatMessages.map((m, idx) => {
      if (m.role === "user") {
        return `<div class="gpt-row gpt-row-user">
          <div class="gpt-bubble gpt-bubble-user">${esc(m.content)}</div>
          <div class="gpt-avatar gpt-avatar-user" aria-hidden="true">${esc(initials(session?.analyst?.employee_name || "U"))}</div>
        </div>`;
      }
      return buildAssistantBubble(m, idx);
    }).join("");
    log.scrollTop = stickBottom ? log.scrollHeight : prevScroll;

    document.querySelectorAll(".chat-followup-btn").forEach((btn) => {
      btn.onclick = () => send(btn.getAttribute("data-q") || btn.textContent || "");
    });

    document.querySelectorAll(".chat-chart-tab").forEach((btn) => {
      btn.onclick = () => {
        const idx = Number(btn.getAttribute("data-msg-idx"));
        const type = btn.getAttribute("data-chart-type");
        if (!Number.isFinite(idx) || !chatMessages[idx] || !type) return;
        chatMessages[idx].chartType = type;
        paintChat({ stickBottom: false });
      };
    });
  }

  async function send(text) {
    if (!text.trim()) return;
    if (document.getElementById("chat-form")?.dataset.busy === "1") return;
    const form = document.getElementById("chat-form");
    const sendBtn = form?.querySelector(".gpt-send");
    const inputEl = document.getElementById("chat-input");
    if (form) form.dataset.busy = "1";
    if (sendBtn) sendBtn.disabled = true;
    if (inputEl) inputEl.disabled = true;

    const question = text.trim();
    if (inputEl) inputEl.value = "";
    autosizeInput();
    chatMessages.push({ role: "user", content: question });
    paintChat();
    const history = chatMessages
      .slice(0, -1)
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({
        role: m.role,
        content: m.content,
        sql: m.sql || null,
        df: m.rows || m.df || null,
      }));
    const statusId = `chat-status-${Date.now()}`;
    const log = document.getElementById("chat-log");
    if (log) {
      log.insertAdjacentHTML(
        "beforeend",
        `<div class="gpt-row gpt-row-assistant" id="${statusId}">
          <div class="gpt-avatar gpt-avatar-ai" aria-hidden="true">AI</div>
          <div class="gpt-bubble gpt-bubble-assistant chat-thinking">Analyzing your question…</div>
        </div>`,
      );
      log.scrollTop = log.scrollHeight;
    }
    try {
      const res = await api("/portal/chat", {
        method: "POST",
        body: JSON.stringify({ message: question, history }),
      });
      document.getElementById(statusId)?.remove();
      chatMessages.push({
        role: "assistant",
        content: res.content || "No response received.",
        status: res.status || "success",
        sql: res.sql || null,
        rows: res.rows || null,
        df: res.rows || null,
        chart: res.chart || null,
        chartType: res.chart?.type || null,
        followups: res.followups || [],
        business_advice: res.business_advice || [],
        insight_title: res.insight_title || "AI Insights",
      });
      paintChat();
    } catch (err) {
      document.getElementById(statusId)?.remove();
      const msg = err instanceof Error ? err.message : String(err);
      chatMessages.push({
        role: "assistant",
        content: `Chatbot error: ${msg}`,
        status: "error",
        sql: null,
        rows: null,
        chart: null,
        followups: [],
        business_advice: [],
      });
      paintChat();
    } finally {
      if (form) form.dataset.busy = "0";
      if (sendBtn) sendBtn.disabled = false;
      if (inputEl) {
        inputEl.disabled = false;
        inputEl.focus();
      }
    }
  }

  function autosizeInput() {
    const input = document.getElementById("chat-input");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  document.getElementById("chat-form").onsubmit = (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    send(input.value);
  };
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      document.getElementById("chat-form").requestSubmit();
    }
  });
  document.getElementById("chat-input").addEventListener("input", autosizeInput);
  document.getElementById("chat-clear").onclick = () => { chatMessages = []; paintChat(); };
  paintChat();
  document.getElementById("chat-input")?.focus();
}

function bindShell() {
  bindLanguageToggle("lang-select", () => render());
  document.getElementById("logout-btn")?.addEventListener("click", () => {
    clearSession();
    navigate("login");
  });
}

async function render() {
  const route = currentRoute();

  if (!session) {
    if (route !== "login") return navigate("login");
    return renderLogin();
  }

  const page = ROUTE_PAGES[route];
  if (!page || !hasPage(page)) {
    const first = PAGE_ROUTES[session.granted_pages[0]];
    if (first) return navigate(first);
    document.getElementById("app").innerHTML = `<div class="login-wrap"><div class="login-card"><h2>${esc(t("no_page_access"))}</h2><p>${esc(t("contact_admin_access"))}</p>${languageToggleHtml({ id: "lang-select" })}<button class="btn btn-secondary" id="logout-btn" style="margin-top:1rem">${esc(t("log_out"))}</button></div></div>`;
    bindLanguageToggle("lang-select", () => render());
    document.getElementById("logout-btn").onclick = () => { clearSession(); navigate("login"); };
    return;
  }

  if (route === "dashboard") return renderDashboard();
  if (route === "admin") return renderAdmin();
  if (route === "analytics") return renderPowerBi();
  if (route === "chatbot") return renderChatbot();
}

window.addEventListener("hashchange", render);
if (!location.hash) location.hash = session ? "#/dashboard" : "#/login";
render();
