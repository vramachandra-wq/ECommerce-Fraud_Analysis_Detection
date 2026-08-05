/**
 * Metro Cart Customer Portal — Matx shell + multi-item cart checkout.
 * Flow: Shop (add to cart) → Cart (uncheck / qty) → Place selected → Confirmation.
 */
import {
  t,
  curSym,
  languageToggleHtml,
  bindLanguageToggle,
} from "./i18n.js?v=35";

const NAV = [
  { route: "order", labelKey: "shop_browse", icon: "order" },
  { route: "cart", labelKey: "shop_cart", icon: "cart" },
  { route: "orders", labelKey: "shop_orders", icon: "orders" },
  { route: "account", labelKey: "shop_account", icon: "account" },
];

const NAV_ICONS = {
  order: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M6 6L5 3H2"/></svg>`,
  cart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 3h2l2.4 12.3a2 2 0 002 1.7h7.4a2 2 0 001.9-1.5L21 8H7"/></svg>`,
  orders: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>`,
  success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>`,
  account: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
};

let session = loadSession();
let lastOrder = loadLastOrder();
let catalogCache = null;
let catalogHasVouchers = false;

function loadSession() {
  try {
    return JSON.parse(localStorage.getItem("metro_cart_customer") || "null");
  } catch {
    return null;
  }
}

function saveSession(data) {
  session = data;
  localStorage.setItem("metro_cart_customer", JSON.stringify(data));
  localStorage.setItem("metro_cart_customer_token", data.token);
}

function clearSession() {
  session = null;
  lastOrder = null;
  catalogCache = null;
  catalogHasVouchers = false;
  localStorage.removeItem("metro_cart_customer");
  localStorage.removeItem("metro_cart_customer_token");
  localStorage.removeItem("metro_cart_last_order");
}

function loadLastOrder() {
  try {
    return JSON.parse(localStorage.getItem("metro_cart_last_order") || "null");
  } catch {
    return null;
  }
}

function saveLastOrder(order) {
  lastOrder = order;
  if (order) localStorage.setItem("metro_cart_last_order", JSON.stringify(order));
  else localStorage.removeItem("metro_cart_last_order");
}

/* ── Cart (per customer, localStorage) ─────────────────────────────── */

function cartStorageKey() {
  const uid = session?.customer?.user_id || "guest";
  return `metro_cart_shop_cart_${uid}`;
}

function loadCart() {
  try {
    const raw = JSON.parse(localStorage.getItem(cartStorageKey()) || "[]");
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((x) => x && x.product_id)
      .map((x) => ({
        product_id: String(x.product_id),
        product_name: String(x.product_name || x.product_id),
        category: String(x.category || ""),
        price: Number(x.price) || 0,
        quantity: Math.max(1, Number(x.quantity) || 1),
        selected: x.selected !== false,
      }));
  } catch {
    return [];
  }
}

function saveCart(items) {
  localStorage.setItem(cartStorageKey(), JSON.stringify(items || []));
}

function cartCount() {
  return loadCart().reduce((n, i) => n + Number(i.quantity || 0), 0);
}

function addToCart(product, qty = 1) {
  const items = loadCart();
  const q = Math.max(1, Math.floor(Number(qty) || 1));
  const existing = items.find((i) => i.product_id === product.product_id);
  if (existing) {
    existing.quantity += q;
    existing.selected = true;
    existing.price = Number(product.price) || existing.price;
    existing.product_name = product.product_name || existing.product_name;
    existing.category = product.category || existing.category;
  } else {
    items.push({
      product_id: product.product_id,
      product_name: product.product_name,
      category: product.category || "",
      price: Number(product.price) || 0,
      quantity: q,
      selected: true,
    });
  }
  saveCart(items);
}

function setCartItemQty(productId, qty) {
  const items = loadCart();
  const row = items.find((i) => i.product_id === productId);
  if (!row) return;
  row.quantity = Math.max(1, Math.floor(Number(qty) || 1));
  saveCart(items);
}

function setCartItemSelected(productId, selected) {
  const items = loadCart();
  const row = items.find((i) => i.product_id === productId);
  if (!row) return;
  row.selected = !!selected;
  saveCart(items);
}

function removeFromCart(productId) {
  saveCart(loadCart().filter((i) => i.product_id !== productId));
}

function removeSelectedFromCart() {
  saveCart(loadCart().filter((i) => !i.selected));
}

function selectedCartItems() {
  return loadCart().filter((i) => i.selected);
}

function selectedCartTotal() {
  return selectedCartItems().reduce(
    (sum, i) => sum + Number(i.price) * Number(i.quantity),
    0,
  );
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
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
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

/** Format timestamps for display as UTC (naive values treated as UTC). */
function formatUtc(value) {
  if (value == null || value === "") return "—";
  const raw = String(value).trim();
  if (!raw || raw.toLowerCase() === "null" || raw.toLowerCase() === "none") return "—";
  let iso = raw.replace(" ", "T");
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(iso) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(iso)) {
    iso = iso.replace(/\.\d+$/, "") + "Z";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return raw;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`;
}

function money(n) {
  return `${curSym()}${Number(n).toLocaleString("th-TH", { minimumFractionDigits: 2 })}`;
}

function initials(name) {
  return String(name || "MC")
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function currentRoute() {
  const hash = location.hash.replace(/^#\/?/, "") || "order";
  return hash.split("/")[0];
}

function currentRouteParts() {
  return location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
}

function navigate(route) {
  location.hash = `#/${route}`;
  render();
}

function confirmAction(opts) {
  const {
    title = t("confirm"),
    message,
    bodyHtml,
    confirmLabel = t("confirm"),
    cancelLabel = t("cancel"),
  } = opts || {};
  return new Promise((resolve) => {
    document.getElementById("confirm-modal")?.remove();
    const overlay = document.createElement("div");
    overlay.id = "confirm-modal";
    overlay.className = "confirm-overlay";
    const body =
      bodyHtml != null
        ? `<div class="confirm-body">${bodyHtml}</div>`
        : `<p class="confirm-message">${esc(message || "")}</p>`;
    overlay.innerHTML = `
      <div class="confirm-dialog confirm-dialog--order" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h3 id="confirm-title">${esc(title)}</h3>
        ${body}
        <div class="confirm-actions">
          <button type="button" class="btn btn-secondary" data-confirm="no">${esc(cancelLabel)}</button>
          <button type="button" class="btn btn-primary" data-confirm="yes">${esc(confirmLabel)}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const finish = (v) => {
      overlay.remove();
      resolve(v);
    };
    overlay.querySelector('[data-confirm="no"]').onclick = () => finish(false);
    overlay.querySelector('[data-confirm="yes"]').onclick = () => finish(true);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) finish(false);
    });
  });
}

function orderConfirmBodyHtml(items, amount, addressLine, ip) {
  const rows = (items || [])
    .map(
      (i) => `
      <li class="confirm-order-item">
        <span class="confirm-order-name">${esc(i.product_name)} × ${esc(i.quantity)}</span>
        <strong class="confirm-order-price">${esc(money(i.price * i.quantity))}</strong>
      </li>`,
    )
    .join("");
  return `
    <div class="confirm-order">
      <p class="confirm-order-heading">${esc(t("order_summary"))}</p>
      <ul class="confirm-order-items">${rows}</ul>
      <div class="confirm-order-total">
        <span>${esc(t("label_amount") || t("total_price"))}</span>
        <strong>${esc(money(amount))}</strong>
      </div>
      <dl class="confirm-order-meta">
        <div class="confirm-order-meta-row">
          <dt>${esc(t("label_delivery_address"))}</dt>
          <dd>${esc(addressLine)}</dd>
        </div>
        <div class="confirm-order-meta-row">
          <dt>${esc(t("label_ip"))}</dt>
          <dd>${esc(ip)}</dd>
        </div>
      </dl>
    </div>`;
}

function shell(content, route) {
  const customer = session.customer;
  const items = [...NAV];
  if (lastOrder) {
    items.splice(2, 0, { route: "success", labelKey: "shop_confirmation", icon: "success" });
  }
  const count = cartCount();
  const nav = items
    .map((item) => {
      const badge =
        item.route === "cart" && count > 0
          ? `<span class="nav-badge" aria-label="${esc(count)} items in cart">${esc(count > 99 ? "99+" : count)}</span>`
          : "";
      return `
      <a href="#/${item.route}" class="nav-link ${route === item.route ? "active" : ""}">
        ${NAV_ICONS[item.icon] || NAV_ICONS.order}
        <span class="nav-link-text">${esc(t(item.labelKey))}${badge}</span>
        <span class="chev">›</span>
      </a>`;
    })
    .join("");

  return `
    <div class="app-frame">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-logo">M</div>
          <div class="sidebar-brand-name">${esc(t("customer_app_title"))}</div>
        </div>
        <div class="sidebar-section">${esc(t("shop_section"))}</div>
        ${nav}
        <div class="sidebar-footer">
          <button type="button" class="btn btn-logout" id="logout-btn">${esc(t("log_out"))}</button>
        </div>
      </aside>
      <div class="main-wrap">
        <header class="topbar">
          <div class="topbar-left">
            <span class="subtitle" style="margin:0">${esc(t("customer_login_subtitle"))}</span>
          </div>
          <div class="topbar-right">
            ${languageToggleHtml({ id: "lang-select" })}
            <a href="#/cart" class="cart-chip" title="${esc(t("shop_cart"))}">
              ${NAV_ICONS.cart}
              <span>${esc(t("shop_cart"))}</span>
              ${count > 0 ? `<span class="nav-badge">${esc(count)}</span>` : ""}
            </a>
            <div class="user-chip">
              <span class="user-chip-text">${esc(t("hi_user", { name: customer.customer_name }))}</span>
              <div class="user-avatar">${esc(initials(customer.customer_name))}</div>
            </div>
          </div>
        </header>
        <main class="content">${content}</main>
      </div>
    </div>`;
}

function bindShell() {
  bindLanguageToggle("lang-select", () => render());
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try {
      await api("/shop/auth/logout", { method: "POST" });
    } catch {
      /* still clear local session */
    }
    clearSession();
    navigate("login");
  });
}

function pageHead(title, subtitle, trailing = "") {
  return `
    <div class="section-head shop-section-head">
      <div class="shop-section-copy">
        <p class="section-kicker" style="margin:0 0 0.35rem">${esc(t("customer_app_title"))}</p>
        <h1 class="page-title">${esc(title)}</h1>
        ${subtitle ? `<p class="subtitle" style="margin:0.35rem 0 0">${esc(subtitle)}</p>` : ""}
      </div>
      ${trailing ? `<div class="shop-section-actions">${trailing}</div>` : ""}
    </div>`;
}

async function renderLogin(mode = "login") {
  const isForgot = mode === "forgot_password";
  const isChange = mode === "change_password";

  let title;
  let subtitle;
  let fields;
  let actions;

  if (isForgot) {
    title = t("forgot_password");
    subtitle = t("password_reset_hint");
    fields = `
      <div class="field"><label>${esc(t("user_id"))}</label><input name="user_id" required autocomplete="username" /></div>
      <div class="field"><label>${esc(t("email"))}</label><input name="email" type="email" required autocomplete="email" /></div>
      <div class="field"><label>${esc(t("new_password"))}</label><input name="new_password" type="password" required autocomplete="new-password" /></div>
      <div class="field"><label>${esc(t("confirm_new_password"))}</label><input name="confirm_password" type="password" required autocomplete="new-password" /></div>`;
    actions = `
      <button class="btn btn-primary" style="width:100%" type="submit">${esc(t("update_password"))}</button>
      <button type="button" class="btn btn-secondary" style="width:100%;margin-top:0.65rem" id="back-login">${esc(t("back_to_login"))}</button>`;
  } else if (isChange) {
    title = t("change_password");
    subtitle = t("password_change_login_hint");
    fields = `
      <div class="field"><label>${esc(t("user_id"))}</label><input name="user_id" required autocomplete="username" /></div>
      <div class="field"><label>${esc(t("current_password"))}</label><input name="current_password" type="password" required autocomplete="current-password" /></div>
      <div class="field"><label>${esc(t("new_password"))}</label><input name="new_password" type="password" required autocomplete="new-password" /></div>
      <div class="field"><label>${esc(t("confirm_new_password"))}</label><input name="confirm_password" type="password" required autocomplete="new-password" /></div>`;
    actions = `
      <button class="btn btn-primary" style="width:100%" type="submit">${esc(t("update_password"))}</button>
      <button type="button" class="btn btn-secondary" style="width:100%;margin-top:0.65rem" id="back-login">${esc(t("back_to_login"))}</button>`;
  } else {
    title = t("customer_app_title");
    subtitle = t("customer_login_subtitle");
    fields = `
      <div class="field"><label>${esc(t("user_id"))}</label><input name="user_id" required autocomplete="username" /></div>
      <div class="field"><label>${esc(t("password"))}</label><input name="password" type="password" required autocomplete="current-password" /></div>
      <div class="login-links">
        <button type="button" class="link-btn" id="goto-forgot-password">${esc(t("forgot_password"))}</button>
      </div>`;
    actions = `
      <button class="btn btn-primary" style="width:100%" type="submit">${esc(t("sign_in"))}</button>
      <button type="button" class="btn btn-secondary" style="width:100%;margin-top:0.65rem" id="goto-change-password">${esc(t("change_password"))}</button>`;
  }

  document.getElementById("app").innerHTML = `
    <div class="login-wrap">
      <div class="login-lang">${languageToggleHtml({ id: "lang-select-login" })}</div>
      <form class="login-card" id="login-form">
        <div class="login-logo-row">
          <div class="sidebar-logo">M</div>
          <h1>${esc(title)}</h1>
        </div>
        <p class="subtitle" style="margin-top:0">${esc(subtitle)}</p>
        <div id="login-error"></div>
        ${fields}
        ${actions}
      </form>
    </div>`;

  bindLanguageToggle("lang-select-login", () => renderLogin(mode));
  document.getElementById("goto-forgot-password")?.addEventListener("click", () => renderLogin("forgot_password"));
  document.getElementById("goto-change-password")?.addEventListener("click", () => renderLogin("change_password"));
  document.getElementById("back-login")?.addEventListener("click", () => renderLogin("login"));

  document.getElementById("login-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = document.getElementById("login-error");
    err.innerHTML = "";
    try {
      if (isForgot) {
        await api(
          "/shop/auth/reset-password",
          {
            method: "POST",
            body: JSON.stringify({
              user_id: fd.get("user_id"),
              email: fd.get("email"),
              new_password: fd.get("new_password"),
              confirm_password: fd.get("confirm_password"),
            }),
          },
          false,
        );
        err.innerHTML = `<div class="alert alert-success">${esc(t("password_reset_success"))}</div>`;
        setTimeout(() => renderLogin("login"), 1400);
        return;
      }
      if (isChange) {
        await api(
          "/shop/auth/change-password",
          {
            method: "POST",
            body: JSON.stringify({
              user_id: fd.get("user_id"),
              current_password: fd.get("current_password"),
              new_password: fd.get("new_password"),
              confirm_password: fd.get("confirm_password"),
            }),
          },
          false,
        );
        err.innerHTML = `<div class="alert alert-success">${esc(t("password_change_then_login"))}</div>`;
        setTimeout(() => renderLogin("login"), 1200);
        return;
      }
      const data = await api(
        "/shop/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            user_id: fd.get("user_id"),
            password: fd.get("password"),
          }),
        },
        false,
      );
      saveSession(data);
      saveLastOrder(null);
      navigate("order");
    } catch (ex) {
      const fallback = isForgot || isChange ? "password_change_failed" : "invalid_login";
      err.innerHTML = `<div class="alert alert-error">${esc(ex.message || t(fallback))}</div>`;
    }
  };
}

async function ensureCatalog() {
  if (catalogCache) return catalogCache;
  catalogCache = await api("/shop/catalog");
  catalogHasVouchers = (catalogCache.products || []).some((p) => isVoucherProduct(p));
  return catalogCache;
}

function step(num, title, sub, body) {
  return `
    <section class="card">
      <div class="step-head">
        <div class="step-num">${esc(num)}</div>
        <div>
          <h2>${esc(title)}</h2>
          ${sub ? `<p>${esc(sub)}</p>` : ""}
        </div>
      </div>
      ${body}
    </section>`;
}

/** Shop browse — add products to cart */
const SHOP_PAGE_SIZE = 12;
let shopSearchQuery = sessionStorage.getItem("metro_cart_shop_search") || "";
let shopCategory = sessionStorage.getItem("metro_cart_shop_category") || "all";
let shopPage = Math.max(1, Number(sessionStorage.getItem("metro_cart_shop_page")) || 1);

const SHOP_CATEGORY_ORDER = ["Electronics", "Appliances", "Furniture"];

/** Map DB categories for shop display (Peripherals roll into Electronics). */
function shopDisplayCategory(category) {
  const raw = String(category || "").trim();
  if (!raw) return "Other";
  if (raw.toLowerCase() === "peripherals") return "Electronics";
  return raw;
}

function isVoucherProduct(product) {
  return shopDisplayCategory(product?.category).toLowerCase() === "vouchers";
}

function shopCategoryLabel(category) {
  if (category === "Electronics") return t("shop_cat_electronics") || "Electronics";
  if (category === "Appliances") return t("shop_cat_appliances") || "Appliances";
  if (category === "Furniture") return t("shop_cat_furniture") || "Furniture";
  if (category === "Vouchers") return t("shop_cat_vouchers") || "Gift vouchers";
  return category;
}

function uniqueCategories(products) {
  // Vouchers use a dedicated top-right button — not a category chip.
  const cats = [
    ...new Set(
      (products || [])
        .map((p) => shopDisplayCategory(p.category))
        .filter((c) => c && c !== "Other" && c.toLowerCase() !== "vouchers"),
    ),
  ];
  return cats.sort((a, b) => {
    const ia = SHOP_CATEGORY_ORDER.indexOf(a);
    const ib = SHOP_CATEGORY_ORDER.indexOf(b);
    if (ia !== -1 || ib !== -1) return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    return a.localeCompare(b);
  });
}

function filterProducts(products, query, category = "all") {
  let list = products || [];
  if (category === "Vouchers") {
    list = list.filter((p) => isVoucherProduct(p));
  } else {
    list = list.filter((p) => !isVoucherProduct(p));
    if (category && category !== "all") {
      list = list.filter((p) => shopDisplayCategory(p.category) === category);
    }
  }
  const q = String(query || "").trim().toLowerCase();
  if (!q) return list;
  return list.filter((p) => {
    const displayCat = shopDisplayCategory(p.category);
    const hay = [
      p.product_name,
      p.category,
      displayCat,
      p.product_id,
      String(p.price ?? ""),
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

function paginateProducts(products, page, pageSize = SHOP_PAGE_SIZE) {
  const total = products.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize) || 1);
  const safePage = Math.min(Math.max(1, Number(page) || 1), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: products.slice(start, start + pageSize),
    page: safePage,
    totalPages,
    total,
    shown: Math.min(pageSize, Math.max(0, total - start)),
  };
}

function categoryChipsHtml(categories, active) {
  const chips = [
    { id: "all", label: t("all_categories") },
    ...categories.map((c) => ({ id: c, label: shopCategoryLabel(c) })),
  ];
  return chips
    .map(
      (c) => `
        <button
          type="button"
          class="category-chip ${active === c.id ? "active" : ""}"
          data-category="${esc(c.id)}"
          role="tab"
          aria-selected="${active === c.id ? "true" : "false"}"
        >${esc(c.label)}</button>`,
    )
    .join("");
}

function shopFilterRowHtml(categories, active) {
  return `
      <section class="filter-panel filter-panel-categories" aria-label="${esc(t("filter_by_category"))}">
        <p class="filter-panel-label">${esc(t("shop_categories_label") || "Categories")}</p>
        <div class="category-filter" role="tablist">${categoryChipsHtml(
          categories,
          active === "Vouchers" ? "" : active,
        )}</div>
      </section>`;
}

function shopVouchersButtonHtml(active) {
  const isActive = active === "Vouchers";
  return `<button
      type="button"
      id="shop-vouchers-btn"
      class="shop-vouchers-btn ${isActive ? "active" : ""}"
      data-category="Vouchers"
      aria-pressed="${isActive ? "true" : "false"}"
      title="${esc(t("shop_cat_vouchers") || "Vouchers")}"
    >${esc(t("shop_cat_vouchers") || "Vouchers")}</button>`;
}

function paginationHtml(page, totalPages) {
  if (totalPages <= 1) return "";
  return `
    <nav class="shop-pagination" aria-label="Pagination">
      <button type="button" class="btn btn-secondary" id="shop-page-prev" ${
        page <= 1 ? "disabled" : ""
      }>${esc(t("pagination_prev"))}</button>
      <span class="shop-page-label">${esc(t("pagination_page", { page, pages: totalPages }))}</span>
      <button type="button" class="btn btn-secondary" id="shop-page-next" ${
        page >= totalPages ? "disabled" : ""
      }>${esc(t("pagination_next"))}</button>
    </nav>`;
}

function productCardsHtml(products) {
  if (!products.length) {
    return `<div class="card"><p class="subtitle" style="margin:0">${esc(t("search_no_results"))}</p></div>`;
  }
  return products
    .map((p) => {
      const displayCat = shopDisplayCategory(p.category);
      return `
      <article class="product-card" data-product-id="${esc(p.product_id)}">
        <div class="product-card-body">
          <p class="product-cat">${esc(shopCategoryLabel(displayCat))}</p>
          <h3 class="product-name">${esc(p.product_name)}</h3>
          <p class="product-price">${esc(money(p.price))}</p>
        </div>
        <div class="product-card-actions">
          <label class="qty-inline">
            <span>${esc(t("quantity"))}</span>
            <input type="number" min="1" step="1" value="1" class="product-qty" aria-label="${esc(t("quantity"))}" />
          </label>
          <button type="button" class="btn btn-primary btn-add-cart">${esc(t("add_to_cart"))}</button>
        </div>
      </article>`;
    })
    .join("");
}

async function renderOrder() {
  document.getElementById("app").innerHTML = shell(
    `${pageHead(t("shop_browse"), t("shop_browse_lede"))}
     <div class="card"><p class="subtitle" style="margin:0">${esc(t("loading_catalog"))}</p></div>`,
    "order",
  );
  bindShell();

  try {
    const catalog = await ensureCatalog();
    const products = catalog.products || [];
    const categories = uniqueCategories(products);
    const hasVouchers = products.some((p) => isVoucherProduct(p));
    // Migrate old chip selections (e.g. Peripherals) to display categories.
    if (shopCategory && shopCategory !== "all" && shopCategory !== "Vouchers") {
      shopCategory = shopDisplayCategory(shopCategory);
    }
    if (
      shopCategory !== "all" &&
      shopCategory !== "Vouchers" &&
      !categories.includes(shopCategory)
    ) {
      shopCategory = "all";
      sessionStorage.setItem("metro_cart_shop_category", shopCategory);
    }
    if (shopCategory === "Vouchers" && !hasVouchers) {
      shopCategory = "all";
      sessionStorage.setItem("metro_cart_shop_category", shopCategory);
    }

    const filtered = filterProducts(products, shopSearchQuery, shopCategory);
    const pageData = paginateProducts(filtered, shopPage);
    shopPage = pageData.page;
    sessionStorage.setItem("metro_cart_shop_page", String(shopPage));

    const main = `
      ${pageHead(
        t("shop_browse"),
        t("shop_browse_lede"),
        hasVouchers ? shopVouchersButtonHtml(shopCategory) : "",
      )}
      <div class="shop-top">
        <div class="shop-top-bar">
          <form class="shop-search" id="shop-search-form" role="search">
            <label class="sr-only" for="shop-search-input">${esc(t("search_products"))}</label>
            <input
              id="shop-search-input"
              type="search"
              placeholder="${esc(t("search_products_placeholder"))}"
              value="${esc(shopSearchQuery)}"
              autocomplete="off"
            />
            <button type="submit" class="btn btn-primary">${esc(t("search"))}</button>
            ${
              shopSearchQuery
                ? `<button type="button" class="btn btn-secondary" id="shop-search-clear">${esc(t("clear_search"))}</button>`
                : ""
            }
          </form>
        </div>
        <p class="shop-results-count" id="shop-results-count">${esc(
          t("search_results_count", {
            shown: pageData.shown,
            total: pageData.total,
          }),
        )}</p>
        <div class="shop-filter-row">
          ${shopFilterRowHtml(categories, shopCategory)}
        </div>
      </div>
      <div id="shop-toast"></div>
      <p class="shop-products-heading">${esc(t("shop_products_heading") || "Products")}</p>
      <div class="product-grid" id="product-grid">${productCardsHtml(pageData.items)}</div>
      <div id="shop-pagination">${paginationHtml(pageData.page, pageData.totalPages)}</div>`;

    document.getElementById("app").innerHTML = shell(main, "order");
    bindShell();

    const searchInput = document.getElementById("shop-search-input");
    const grid = document.getElementById("product-grid");
    const pagerHost = document.getElementById("shop-pagination");

    function syncCategoryChips() {
      document.querySelectorAll(".category-chip").forEach((chip) => {
        const active = chip.dataset.category === shopCategory;
        chip.classList.toggle("active", active);
        chip.setAttribute("aria-selected", active ? "true" : "false");
      });
      const voucherBtn = document.getElementById("shop-vouchers-btn");
      if (voucherBtn) {
        const active = shopCategory === "Vouchers";
        voucherBtn.classList.toggle("active", active);
        voucherBtn.setAttribute("aria-pressed", active ? "true" : "false");
      }
    }

    function onVoucherClick() {
      shopCategory = shopCategory === "Vouchers" ? "all" : "Vouchers";
      refreshProductView({ resetPage: true });
    }
    document.getElementById("shop-vouchers-btn")?.addEventListener("click", onVoucherClick);

    function refreshProductView({ resetPage = false } = {}) {
      if (resetPage) shopPage = 1;
      const nextFiltered = filterProducts(products, shopSearchQuery, shopCategory);
      const nextPage = paginateProducts(nextFiltered, shopPage);
      shopPage = nextPage.page;
      sessionStorage.setItem("metro_cart_shop_search", shopSearchQuery);
      sessionStorage.setItem("metro_cart_shop_category", shopCategory);
      sessionStorage.setItem("metro_cart_shop_page", String(shopPage));

      if (grid) grid.innerHTML = productCardsHtml(nextPage.items);
      if (pagerHost) pagerHost.innerHTML = paginationHtml(nextPage.page, nextPage.totalPages);
      bindPagination();

      const countEl = document.getElementById("shop-results-count");
      if (countEl) {
        countEl.textContent = t("search_results_count", {
          shown: nextPage.shown,
          total: nextPage.total,
        });
      }

      syncCategoryChips();

      const clearBtn = document.getElementById("shop-search-clear");
      const form = document.getElementById("shop-search-form");
      if (shopSearchQuery && !clearBtn && form) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-secondary";
        btn.id = "shop-search-clear";
        btn.textContent = t("clear_search");
        form.appendChild(btn);
        btn.addEventListener("click", () => {
          if (searchInput) searchInput.value = "";
          applySearch("", { refocus: true });
        });
      } else if (!shopSearchQuery && clearBtn) {
        clearBtn.remove();
      }
      bindProductCards(products);
    }

    function applySearch(nextQuery, { refocus = false } = {}) {
      shopSearchQuery = String(nextQuery || "");
      refreshProductView({ resetPage: true });
      if (refocus) searchInput?.focus();
    }

    function bindPagination() {
      document.getElementById("shop-page-prev")?.addEventListener("click", () => {
        if (shopPage <= 1) return;
        shopPage -= 1;
        refreshProductView();
        grid?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      document.getElementById("shop-page-next")?.addEventListener("click", () => {
        shopPage += 1;
        refreshProductView();
        grid?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }

    function bindProductCards(allProducts) {
      document.querySelectorAll(".product-card").forEach((card) => {
        const pid = card.dataset.productId;
        const product = allProducts.find((p) => p.product_id === pid);
        card.querySelector(".btn-add-cart")?.addEventListener("click", () => {
          const qty = Math.max(1, Number(card.querySelector(".product-qty")?.value) || 1);
          addToCart(product, qty);
          sessionStorage.setItem(
            "metro_cart_shop_toast",
            t("added_to_cart", { name: product.product_name, qty }),
          );
          renderOrder();
        });
      });
    }

    document.getElementById("shop-search-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      applySearch(searchInput?.value || "");
    });

    let searchTimer = null;
    searchInput?.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => applySearch(searchInput.value), 180);
    });

    document.getElementById("shop-search-clear")?.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      applySearch("", { refocus: true });
    });

    document.querySelectorAll(".category-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const next = chip.dataset.category || "all";
        if (next === shopCategory) return;
        shopCategory = next;
        refreshProductView({ resetPage: true });
      });
    });

    bindPagination();
    bindProductCards(products);

    const toastMsg = sessionStorage.getItem("metro_cart_shop_toast");
    if (toastMsg) {
      sessionStorage.removeItem("metro_cart_shop_toast");
      const toast = document.getElementById("shop-toast");
      if (toast) toast.innerHTML = `<div class="alert alert-success">${esc(toastMsg)}</div>`;
    }

    if (shopSearchQuery) searchInput?.focus();
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(
      `${pageHead(t("shop_browse"), t("shop_browse_lede"))}
       <div class="card"><div class="alert alert-error">${esc(ex.message)}</div></div>`,
      "order",
    );
    bindShell();
  }
}

/** Cart — uncheck items, edit qty, checkout selected */
async function renderCart() {
  document.getElementById("app").innerHTML = shell(
    `${pageHead(t("shop_cart"), t("shop_cart_lede"))}
     <div class="card"><p class="subtitle" style="margin:0">${esc(t("loading_catalog"))}</p></div>`,
    "cart",
  );
  bindShell();

  try {
    const catalog = await ensureCatalog();
    const customer = session.customer;
    const programs = catalog.programs || [];
    const devices = catalog.devices || [];
    const defaultProgram =
      programs.find((p) => p.program_id === customer.program_id) || programs[0];
    const cart = loadCart();
    const selected = selectedCartItems();
    const selectedTotal = selectedCartTotal();

    const rows = cart.length
      ? cart
          .map(
            (item) => `
        <tr class="cart-row ${item.selected ? "" : "cart-row-off"}" data-product-id="${esc(item.product_id)}">
          <td class="cart-check">
            <input type="checkbox" class="cart-select" ${item.selected ? "checked" : ""} aria-label="${esc(t("include_in_order"))}" />
          </td>
          <td>
            <div class="cart-item-name">${esc(item.product_name)}</div>
            <div class="cart-item-meta">${esc(shopCategoryLabel(shopDisplayCategory(item.category)) || "—")} · ${esc(item.product_id)}</div>
          </td>
          <td class="cart-num cart-price">${esc(money(item.price))}</td>
          <td class="cart-qty-col">
            <input type="number" class="cart-qty" min="1" step="1" value="${esc(item.quantity)}" ${item.selected ? "" : "disabled"} />
          </td>
          <td class="cart-num cart-line">${esc(money(item.price * item.quantity))}</td>
          <td class="cart-actions">
            <button type="button" class="btn btn-secondary btn-sm cart-remove">${esc(t("remove"))}</button>
          </td>
        </tr>`,
          )
          .join("")
      : "";

    const cartTable = cart.length
      ? `
      <div class="cart-table-wrap">
        <table class="cart-table">
          <thead>
            <tr>
              <th class="cart-check">${esc(t("include_in_order"))}</th>
              <th>${esc(t("product"))}</th>
              <th class="cart-num">${esc(t("unit_price"))}</th>
              <th class="cart-qty-col">${esc(t("quantity"))}</th>
              <th class="cart-num">${esc(t("line_total"))}</th>
              <th class="cart-actions"></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="subtitle cart-select-hint">${esc(t("cart_uncheck_hint"))}</p>`
      : `<div class="alert alert-warning">${esc(t("cart_empty"))}</div>
         <a class="btn btn-primary" href="#/order">${esc(t("shop_browse"))}</a>`;

    const main = `
      ${pageHead(t("shop_cart"), t("shop_cart_lede"))}
      <div class="shop-layout">
        <div>
          ${step("1", t("your_cart"), t("cart_uncheck_hint"), cartTable)}
          ${
            cart.length
              ? step(
                  "2",
                  t("delivery_address"),
                  "",
                  `
            <div class="form-grid">
              <div class="field"><label>${esc(t("street"))}</label><input id="f-street" value="${esc(customer.street || "")}" /></div>
              <div class="field"><label>${esc(t("city"))}</label><input id="f-city" value="${esc(customer.city || "")}" /></div>
              <div class="field"><label>${esc(t("state"))}</label><input id="f-state" value="${esc(customer.state || "")}" /></div>
              <div class="field"><label>${esc(t("zip_code"))}</label><input id="f-zip" value="${esc(customer.zip_code || "")}" /></div>
              <div class="field span-2"><label>${esc(t("country"))}</label><input id="f-country" value="${esc(customer.country || "India")}" /></div>
            </div>`,
                )
              : ""
          }
          ${
            cart.length
              ? step(
                  "3",
                  t("sim_fields"),
                  t("sim_caption"),
                  `
            <div class="form-grid-3">
              <div class="field"><label>${esc(t("ip_address"))}</label><input id="f-ip" placeholder="e.g. 203.0.113.111" /></div>
              <div class="field">
                <label>${esc(t("program_track"))}</label>
                <select id="f-program">
                  ${programs
                    .map(
                      (p) =>
                        `<option value="${esc(p.program_id)}" ${
                          defaultProgram && p.program_id === defaultProgram.program_id ? "selected" : ""
                        }>${esc(p.program_id)} — ${esc(p.program_name)}</option>`,
                    )
                    .join("")}
                </select>
              </div>
              <div class="field">
                <label>${esc(t("device"))}</label>
                <select id="f-device">
                  ${devices
                    .map(
                      (d) =>
                        `<option value="${esc(d.device_id)}">${esc(d.device_id)} — ${esc(d.device_name)}</option>`,
                    )
                    .join("")}
                </select>
              </div>
            </div>`,
                )
              : ""
          }
          <div id="order-error"></div>
        </div>

        ${
          cart.length
            ? `<aside class="card summary-rail">
          <h3>${esc(t("order_summary"))}</h3>
          <div class="summary-row"><span>${esc(t("selected_items"))}</span><strong id="sum-count">${esc(selected.length)}</strong></div>
          <div class="summary-row"><span>${esc(t("label_customer"))}</span><strong>${esc(customer.customer_name)}</strong></div>
          <div id="sum-lines" class="sum-lines">
            ${
              selected.length
                ? selected
                    .map(
                      (i) =>
                        `<div class="summary-row"><span>${esc(i.product_name)} × ${esc(i.quantity)}</span><strong>${esc(money(i.price * i.quantity))}</strong></div>`,
                    )
                    .join("")
                : `<p class="subtitle">${esc(t("no_items_selected"))}</p>`
            }
          </div>
          <div class="summary-total">
            <div class="label">${esc(t("total_price"))}</div>
            <div class="value" id="sum-total">${esc(money(selectedTotal))}</div>
          </div>
          <div class="summary-actions">
            <button type="button" class="btn btn-primary" id="btn-purchase" ${
              selected.length ? "" : "disabled"
            }>${esc(t("place_selected_order"))}</button>
            <a class="btn btn-secondary" href="#/order">${esc(t("continue_shopping"))}</a>
          </div>
        </aside>`
            : ""
        }
      </div>`;

    document.getElementById("app").innerHTML = shell(main, "cart");
    bindShell();

    function refreshSummaryUi() {
      const sel = selectedCartItems();
      const total = selectedCartTotal();
      const countEl = document.getElementById("sum-count");
      const totalEl = document.getElementById("sum-total");
      const linesEl = document.getElementById("sum-lines");
      const btn = document.getElementById("btn-purchase");
      if (countEl) countEl.textContent = String(sel.length);
      if (totalEl) totalEl.textContent = money(total);
      if (linesEl) {
        linesEl.innerHTML = sel.length
          ? sel
              .map(
                (i) =>
                  `<div class="summary-row"><span>${esc(i.product_name)} × ${esc(i.quantity)}</span><strong>${esc(money(i.price * i.quantity))}</strong></div>`,
              )
              .join("")
          : `<p class="subtitle">${esc(t("no_items_selected"))}</p>`;
      }
      if (btn) btn.disabled = !sel.length;
    }

    document.querySelectorAll(".cart-row").forEach((row) => {
      const pid = row.dataset.productId;
      const selectEl = row.querySelector(".cart-select");
      const qtyEl = row.querySelector(".cart-qty");
      const lineEl = row.querySelector(".cart-line");

      selectEl?.addEventListener("change", () => {
        setCartItemSelected(pid, selectEl.checked);
        row.classList.toggle("cart-row-off", !selectEl.checked);
        if (qtyEl) qtyEl.disabled = !selectEl.checked;
        refreshSummaryUi();
      });

      qtyEl?.addEventListener("change", () => {
        const q = Math.max(1, Number(qtyEl.value) || 1);
        qtyEl.value = String(q);
        setCartItemQty(pid, q);
        const item = loadCart().find((i) => i.product_id === pid);
        if (lineEl && item) lineEl.textContent = money(item.price * item.quantity);
        refreshSummaryUi();
      });

      row.querySelector(".cart-remove")?.addEventListener("click", () => {
        removeFromCart(pid);
        renderCart();
      });
    });

    document.getElementById("btn-purchase")?.addEventListener("click", async () => {
      const errEl = document.getElementById("order-error");
      errEl.innerHTML = "";
      const toOrder = selectedCartItems();
      if (!toOrder.length) {
        errEl.innerHTML = `<div class="alert alert-error">${esc(t("no_items_selected"))}</div>`;
        return;
      }

      const street = document.getElementById("f-street").value.trim();
      const city = document.getElementById("f-city").value.trim();
      const state = document.getElementById("f-state").value.trim();
      const zip = document.getElementById("f-zip").value.trim();
      const country = document.getElementById("f-country").value.trim();
      const ip = document.getElementById("f-ip").value.trim();
      const programId = document.getElementById("f-program").value;
      const deviceId = document.getElementById("f-device").value;
      const amount = selectedCartTotal();

      const errors = [];
      if (!(customer.phone_number || "").trim()) errors.push(t("err_phone_required"));
      if (!street || !city || !state || !zip) errors.push(t("err_address_required"));
      if (!ip) errors.push(t("err_ip_required"));
      if (errors.length) {
        errEl.innerHTML = errors.map((e) => `<div class="alert alert-error">${esc(e)}</div>`).join("");
        return;
      }

      const ok = await confirmAction({
        title: t("confirm_place_order"),
        bodyHtml: orderConfirmBodyHtml(
          toOrder,
          amount,
          `${street}, ${city}, ${state} ${zip}`,
          ip,
        ),
        confirmLabel: t("confirm_purchase"),
        cancelLabel: t("cancel"),
      });
      if (!ok) return;

      const btn = document.getElementById("btn-purchase");
      btn.disabled = true;
      btn.textContent = t("completing_purchase");
      try {
        const result = await api("/shop/orders", {
          method: "POST",
          body: JSON.stringify({
            items: toOrder.map((i) => ({
              product_id: i.product_id,
              quantity: Number(i.quantity),
            })),
            program_id: programId,
            device_id: deviceId,
            ip_address: ip,
            street,
            city,
            state,
            zip_code: zip,
            country: country || "India",
          }),
        });
        removeSelectedFromCart();
        saveLastOrder(result);
        navigate("success");
      } catch (ex) {
        errEl.innerHTML = `<div class="alert alert-error">${esc(ex.message)}</div>`;
        btn.disabled = false;
        btn.textContent = t("place_selected_order");
      }
    });
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(
      `${pageHead(t("shop_cart"), t("shop_cart_lede"))}
       <div class="card"><div class="alert alert-error">${esc(ex.message)}</div></div>`,
      "cart",
    );
    bindShell();
  }
}

function renderSuccess() {
  if (!lastOrder) return navigate("order");
  const items = Array.isArray(lastOrder.items) ? lastOrder.items : [];
  const itemsHtml = items.length
    ? `<ul class="success-items">
        ${items
          .map(
            (i) =>
              `<li><span>${esc(i.product_name)} × ${esc(i.quantity)}</span><strong>${esc(money(i.line_amount))}</strong></li>`,
          )
          .join("")}
      </ul>`
    : `<p class="success-meta">${esc(lastOrder.product_name)} × ${esc(lastOrder.quantity)} · ${esc(money(lastOrder.amount))}</p>`;

  const main = `
    <div class="success-page">
      <div class="section-head success-page-head">
        <div>
          <p class="section-kicker" style="margin:0 0 0.35rem">${esc(t("customer_app_title"))}</p>
          <h1 class="page-title">${esc(t("shop_confirmation"))}</h1>
        </div>
      </div>
      <div class="card success-card">
        <div class="success-stage">
          <div class="success-mark">✓</div>
          <h1>${esc(t("order_success"))}</h1>
          ${itemsHtml}
          <p class="success-meta">${esc(t("label_amount"))}: ${esc(money(lastOrder.amount))}</p>
          <div class="success-id">
            <span>${esc(t("your_order_id"))}</span>
            <strong>${esc(lastOrder.order_id)}</strong>
          </div>
          <button type="button" class="btn btn-primary success-cta" id="btn-another">${esc(t("place_another_order"))}</button>
          <button type="button" class="btn btn-secondary success-cta" style="margin-top:0.65rem" id="btn-orders">${esc(t("view_order_history"))}</button>
          <button type="button" class="btn btn-secondary success-cta" style="margin-top:0.65rem" id="btn-cart">${esc(t("view_cart"))}</button>
        </div>
      </div>
    </div>`;
  document.getElementById("app").innerHTML = shell(main, "success");
  bindShell();
  document.getElementById("btn-another").onclick = () => {
    saveLastOrder(null);
    navigate("order");
  };
  document.getElementById("btn-cart").onclick = () => {
    saveLastOrder(null);
    navigate("cart");
  };
  document.getElementById("btn-orders")?.addEventListener("click", () => {
    saveLastOrder(null);
    navigate("orders");
  });
}

async function renderOrders() {
  const parts = currentRouteParts();
  const detailId = parts[0] === "orders" && parts[1] ? parts[1] : "";

  if (detailId) {
    return renderOrderDetail(detailId);
  }

  document.getElementById("app").innerHTML = shell(
    `${pageHead(t("shop_orders"), t("shop_orders_lede"))}
     <div class="card"><p class="subtitle" style="margin:0">${esc(t("loading_orders"))}</p></div>`,
    "orders",
  );
  bindShell();

  try {
    const data = await api("/shop/orders?limit=50&offset=0");
    const orders = Array.isArray(data.orders) ? data.orders : [];
    const total = Number(data.total) || orders.length;

    let body;
    if (!orders.length) {
      body = `
        <div class="card history-empty">
          <p>${esc(t("shop_orders_empty"))}</p>
          <a class="btn btn-primary" href="#/order">${esc(t("shop_browse"))}</a>
        </div>`;
    } else {
      const rows = orders
        .map((o) => {
          const summary =
            Number(o.item_count) > 1
              ? t("shop_orders_items_summary", {
                  name: o.product_name || o.order_id,
                  count: o.item_count,
                })
              : o.product_name || "—";
          return `
          <tr class="history-row" data-order-id="${esc(o.order_id)}" tabindex="0" role="link">
            <td><strong>${esc(o.order_id)}</strong></td>
            <td>${esc(formatUtc(o.order_timestamp))}</td>
            <td>${esc(summary)}</td>
            <td>${esc(money(o.amount))}</td>
            <td>${esc(o.quantity)}</td>
            <td><a class="btn btn-secondary btn-sm" href="#/orders/${esc(o.order_id)}">${esc(t("view_order"))}</a></td>
          </tr>`;
        })
        .join("");
      body = `
        <div class="card history-card">
          <div class="history-meta">${esc(t("shop_orders_count", { count: total }))}</div>
          <div class="table-wrap">
            <table class="history-table">
              <thead>
                <tr>
                  <th>${esc(t("your_order_id"))}</th>
                  <th>${esc(t("order_date"))}</th>
                  <th>${esc(t("label_product"))}</th>
                  <th>${esc(t("label_amount"))}</th>
                  <th>${esc(t("quantity"))}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>`;
    }

    document.getElementById("app").innerHTML = shell(
      `${pageHead(t("shop_orders"), t("shop_orders_lede"))}${body}`,
      "orders",
    );
    bindShell();

    document.querySelectorAll(".history-row").forEach((row) => {
      const go = () => navigate(`orders/${row.dataset.orderId}`);
      row.addEventListener("click", (ev) => {
        if (ev.target.closest("a")) return;
        go();
      });
      row.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          go();
        }
      });
    });
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(
      `${pageHead(t("shop_orders"), t("shop_orders_lede"))}
       <div class="card"><div class="alert alert-error">${esc(ex.message)}</div></div>`,
      "orders",
    );
    bindShell();
  }
}

async function renderOrderDetail(orderId) {
  document.getElementById("app").innerHTML = shell(
    `${pageHead(t("shop_order_detail"), t("shop_orders_lede"))}
     <div class="card"><p class="subtitle" style="margin:0">${esc(t("loading_orders"))}</p></div>`,
    "orders",
  );
  bindShell();

  try {
    const order = await api(`/shop/orders/${encodeURIComponent(orderId)}`);
    const items = Array.isArray(order.items) ? order.items : [];
    const itemsHtml = items.length
      ? `<ul class="success-items">
          ${items
            .map(
              (i) =>
                `<li><span>${esc(i.product_name)} × ${esc(i.quantity)}</span><strong>${esc(money(i.line_amount))}</strong></li>`,
            )
            .join("")}
        </ul>`
      : `<p class="success-meta">${esc(order.product_name)} × ${esc(order.quantity)}</p>`;

    const address =
      order.delivery_address ||
      [order.street, order.city, order.state, order.zip_code, order.country]
        .map((x) => String(x || "").trim())
        .filter(Boolean)
        .join(", ") ||
      order.address ||
      "—";

    const main = `
      ${pageHead(
        t("shop_order_detail"),
        order.order_id,
        `<a class="btn btn-secondary" href="#/orders">${esc(t("back_to_orders"))}</a>`,
      )}
      <div class="card history-detail">
        <div class="history-detail-top">
          <div>
            <p class="section-kicker" style="margin:0 0 0.35rem">${esc(t("your_order_id"))}</p>
            <h2 class="page-title" style="font-size:1.25rem;margin:0">${esc(order.order_id)}</h2>
          </div>
        </div>
        <dl class="confirm-order-meta">
          <div class="confirm-order-meta-row">
            <dt>${esc(t("order_date"))}</dt>
            <dd>${esc(formatUtc(order.order_timestamp))}</dd>
          </div>
          <div class="confirm-order-meta-row">
            <dt>${esc(t("label_amount"))}</dt>
            <dd>${esc(money(order.amount))}</dd>
          </div>
          <div class="confirm-order-meta-row">
            <dt>${esc(t("quantity"))}</dt>
            <dd>${esc(order.quantity)}</dd>
          </div>
          <div class="confirm-order-meta-row">
            <dt>${esc(t("label_delivery_address"))}</dt>
            <dd>${esc(address)}</dd>
          </div>
        </dl>
        <p class="confirm-order-heading">${esc(t("order_summary"))}</p>
        ${itemsHtml}
      </div>`;

    document.getElementById("app").innerHTML = shell(main, "orders");
    bindShell();
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(
      `${pageHead(
        t("shop_order_detail"),
        "",
        `<a class="btn btn-secondary" href="#/orders">${esc(t("back_to_orders"))}</a>`,
      )}
       <div class="card"><div class="alert alert-error">${esc(ex.message)}</div></div>`,
      "orders",
    );
    bindShell();
  }
}

function renderAccount() {
  const c = session.customer;
  const main = `
    ${pageHead(t("shop_account"), t("welcome_back", { name: c.customer_name }))}
    <div class="shop-layout single">
      <div>
        ${step(
          "1",
          t("contact_details"),
          "",
          `
          <div class="form-grid">
            <div class="field"><label>${esc(t("user_id"))}</label><input value="${esc(c.user_id)}" disabled /></div>
            <div class="field"><label>${esc(t("name"))}</label><input value="${esc(c.customer_name)}" disabled /></div>
            <div class="field"><label>${esc(t("email"))}</label><input value="${esc(c.email || "")}" disabled /></div>
            <div class="field"><label>${esc(t("phone"))}</label><input value="${esc(c.phone_number || "")}" disabled /></div>
          </div>`,
        )}
        ${step(
          "2",
          t("delivery_address"),
          "",
          `
          <div class="form-grid">
            <div class="field"><label>${esc(t("street"))}</label><input value="${esc(c.street || "")}" disabled /></div>
            <div class="field"><label>${esc(t("city"))}</label><input value="${esc(c.city || "")}" disabled /></div>
            <div class="field"><label>${esc(t("state"))}</label><input value="${esc(c.state || "")}" disabled /></div>
            <div class="field"><label>${esc(t("zip_code"))}</label><input value="${esc(c.zip_code || "")}" disabled /></div>
            <div class="field span-2"><label>${esc(t("country"))}</label><input value="${esc(c.country || "")}" disabled /></div>
          </div>`,
        )}
        ${step(
          "3",
          t("change_password"),
          t("password_change_login_hint"),
          `
          <form id="account-password-form">
            <div id="pw-status"></div>
            <div class="form-grid">
              <div class="field span-2"><label>${esc(t("current_password"))}</label><input name="current_password" type="password" required autocomplete="current-password" /></div>
              <div class="field"><label>${esc(t("new_password"))}</label><input name="new_password" type="password" required autocomplete="new-password" /></div>
              <div class="field"><label>${esc(t("confirm_new_password"))}</label><input name="confirm_password" type="password" required autocomplete="new-password" /></div>
            </div>
            <button type="submit" class="btn btn-primary">${esc(t("update_password"))}</button>
          </form>`,
        )}
      </div>
    </div>`;
  document.getElementById("app").innerHTML = shell(main, "account");
  bindShell();

  document.getElementById("account-password-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const status = document.getElementById("pw-status");
    status.innerHTML = "";
    try {
      await api("/shop/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: fd.get("current_password"),
          new_password: fd.get("new_password"),
          confirm_password: fd.get("confirm_password"),
        }),
      });
      status.innerHTML = `<div class="alert alert-success">${esc(t("password_change_success"))}</div>`;
      e.target.reset();
    } catch (ex) {
      status.innerHTML = `<div class="alert alert-error">${esc(ex.message || t("password_change_failed"))}</div>`;
    }
  };
}

async function render() {
  const route = currentRoute();
  if (!session) {
    if (route !== "login") return navigate("login");
    return renderLogin();
  }
  if (route === "login") return navigate("order");
  try {
    await ensureCatalog();
  } catch {
    /* catalog optional for shell vouchers button */
  }
  if (route === "success") return renderSuccess();
  if (route === "account") return renderAccount();
  if (route === "cart") return renderCart();
  if (route === "orders") return renderOrders();
  return renderOrder();
}

window.addEventListener("hashchange", render);
if (!location.hash) location.hash = session ? "#/order" : "#/login";
render();
