/**
 * Metro Cart Customer Portal — same Matx shell platform as analyst portal.
 * Features: place order, confirmation, account, forgot/change password.
 */
import {
  t,
  curSym,
  languageToggleHtml,
  bindLanguageToggle,
} from "./i18n.js";

const NAV = [
  { route: "order", labelKey: "shop_place_order", icon: "order" },
  { route: "account", labelKey: "shop_account", icon: "account" },
];

const NAV_ICONS = {
  order: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M6 6L5 3H2"/></svg>`,
  success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>`,
  account: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
};

let session = loadSession();
let lastOrder = loadLastOrder();
let catalogCache = null;

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
  return `${curSym()}${Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

function initials(name) {
  return String(name || "MC")
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function badge(status) {
  return `<span class="badge badge-${esc(status)}">${esc(String(status).replaceAll("_", " "))}</span>`;
}

function currentRoute() {
  const hash = location.hash.replace(/^#\/?/, "") || "order";
  return hash.split("/")[0];
}

function navigate(route) {
  location.hash = `#/${route}`;
  render();
}

function confirmAction(opts) {
  const {
    title = t("confirm"),
    message,
    confirmLabel = t("confirm"),
    cancelLabel = t("cancel"),
  } = opts || {};
  return new Promise((resolve) => {
    document.getElementById("confirm-modal")?.remove();
    const overlay = document.createElement("div");
    overlay.id = "confirm-modal";
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-dialog" role="dialog" aria-modal="true">
        <h3>${esc(title)}</h3>
        <p>${esc(message)}</p>
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

function shell(content, route) {
  const customer = session.customer;
  const items = [...NAV];
  if (lastOrder) {
    items.splice(1, 0, { route: "success", labelKey: "shop_confirmation", icon: "success" });
  }
  const nav = items
    .map(
      (item) => `
      <a href="#/${item.route}" class="nav-link ${route === item.route ? "active" : ""}">
        ${NAV_ICONS[item.icon] || NAV_ICONS.order}
        <span>${esc(t(item.labelKey))}</span>
        <span class="chev">›</span>
      </a>`,
    )
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
  document.getElementById("logout-btn")?.addEventListener("click", () => {
    clearSession();
    navigate("login");
  });
}

function pageHead(title, subtitle) {
  return `
    <div class="section-head" style="margin-bottom:1.25rem">
      <div>
        <p class="section-kicker" style="margin:0 0 0.35rem">${esc(t("customer_app_title"))}</p>
        <h1 class="page-title">${esc(title)}</h1>
        ${subtitle ? `<p class="subtitle" style="margin:0.35rem 0 0">${esc(subtitle)}</p>` : ""}
      </div>
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

async function renderOrder() {
  document.getElementById("app").innerHTML = shell(
    `${pageHead(t("shop_place_order"), t("shop_checkout_lede"))}
     <div class="card"><p class="subtitle" style="margin:0">${esc(t("loading_catalog"))}</p></div>`,
    "order",
  );
  bindShell();

  try {
    const catalog = await ensureCatalog();
    const customer = session.customer;
    const products = catalog.products || [];
    const programs = catalog.programs || [];
    const devices = catalog.devices || [];
    const defaultProgram =
      programs.find((p) => p.program_id === customer.program_id) || programs[0];

    const main = `
      ${pageHead(t("shop_place_order"), t("shop_checkout_lede"))}
      <div class="shop-layout">
        <div>
          ${step(
            "1",
            t("contact_details"),
            "",
            `
            <div class="form-grid">
              <div class="field"><label>${esc(t("name"))}</label><input value="${esc(customer.customer_name)}" disabled /></div>
              <div class="field"><label>${esc(t("phone"))}</label><input value="${esc(customer.phone_number || "")}" disabled /></div>
              <div class="field span-2"><label>${esc(t("email"))}</label><input value="${esc(customer.email || "")}" disabled /></div>
            </div>
            ${
              !(customer.phone_number || "").trim()
                ? `<div class="alert alert-warning">${esc(t("no_phone_warning"))}</div>`
                : ""
            }`,
          )}
          ${step(
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
          )}
          ${step(
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
          )}
          ${step(
            "4",
            t("product_selection"),
            "",
            `
            <div class="form-grid">
              <div class="field">
                <label>${esc(t("product"))}</label>
                <select id="f-product">
                  ${products
                    .map(
                      (p) =>
                        `<option value="${esc(p.product_id)}" data-price="${esc(p.price)}" data-name="${esc(p.product_name)}">${esc(p.product_name)} — ${esc(money(p.price))}</option>`,
                    )
                    .join("")}
                </select>
              </div>
              <div class="field">
                <label>${esc(t("quantity"))}</label>
                <input id="f-qty" type="number" min="1" step="1" value="1" />
              </div>
            </div>`,
          )}
          <div id="order-error"></div>
        </div>

        <aside class="card summary-rail">
          <h3>${esc(t("order_summary"))}</h3>
          <div class="summary-row"><span>${esc(t("label_product"))}</span><strong id="sum-product">—</strong></div>
          <div class="summary-row"><span>${esc(t("quantity"))}</span><strong id="sum-qty">1</strong></div>
          <div class="summary-row"><span>${esc(t("label_customer"))}</span><strong>${esc(customer.customer_name)}</strong></div>
          <div class="summary-total">
            <div class="label">${esc(t("total_price"))}</div>
            <div class="value" id="sum-total">${esc(money(products[0]?.price || 0))}</div>
          </div>
          <button type="button" class="btn btn-primary" style="width:100%;margin-top:1rem" id="btn-purchase">${esc(t("complete_purchase"))}</button>
        </aside>
      </div>`;

    document.getElementById("app").innerHTML = shell(main, "order");
    bindShell();

    const productEl = document.getElementById("f-product");
    const qtyEl = document.getElementById("f-qty");

    function refreshSummary() {
      const opt = productEl.selectedOptions[0];
      const price = Number(opt?.dataset.price || 0);
      const qty = Math.max(1, Number(qtyEl.value) || 1);
      document.getElementById("sum-product").textContent = opt?.dataset.name || "—";
      document.getElementById("sum-qty").textContent = String(qty);
      document.getElementById("sum-total").textContent = money(price * qty);
    }
    productEl.onchange = refreshSummary;
    qtyEl.oninput = refreshSummary;
    refreshSummary();

    document.getElementById("btn-purchase").onclick = async () => {
      const errEl = document.getElementById("order-error");
      errEl.innerHTML = "";
      const street = document.getElementById("f-street").value.trim();
      const city = document.getElementById("f-city").value.trim();
      const state = document.getElementById("f-state").value.trim();
      const zip = document.getElementById("f-zip").value.trim();
      const country = document.getElementById("f-country").value.trim();
      const ip = document.getElementById("f-ip").value.trim();
      const productId = productEl.value;
      const qty = Math.max(1, Number(qtyEl.value) || 1);
      const programId = document.getElementById("f-program").value;
      const deviceId = document.getElementById("f-device").value;
      const product = products.find((p) => p.product_id === productId);
      const amount = Number(product?.price || 0) * qty;

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
        message: [
          t("order_summary"),
          `${t("label_product")}: ${product?.product_name} × ${qty}`,
          `${t("label_amount")}: ${money(amount)}`,
          `${t("label_delivery_address")}: ${street}, ${city}, ${state} ${zip}`,
          `${t("label_ip")}: ${ip}`,
        ].join("\n"),
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
            product_id: productId,
            quantity: qty,
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
        saveLastOrder(result);
        navigate("success");
      } catch (ex) {
        errEl.innerHTML = `<div class="alert alert-error">${esc(ex.message)}</div>`;
        btn.disabled = false;
        btn.textContent = t("complete_purchase");
      }
    };
  } catch (ex) {
    document.getElementById("app").innerHTML = shell(
      `${pageHead(t("shop_place_order"), t("shop_checkout_lede"))}
       <div class="card"><div class="alert alert-error">${esc(ex.message)}</div></div>`,
      "order",
    );
    bindShell();
  }
}

function renderSuccess() {
  if (!lastOrder) return navigate("order");
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
          <p class="success-meta">${esc(lastOrder.product_name)} × ${esc(lastOrder.quantity)} · ${esc(money(lastOrder.amount))}</p>
          <div class="success-id">
            <span>${esc(t("your_order_id"))}</span>
            <strong>${esc(lastOrder.order_id)}</strong>
          </div>
          <button type="button" class="btn btn-primary success-cta" id="btn-another">${esc(t("place_another_order"))}</button>
        </div>
      </div>
    </div>`;
  document.getElementById("app").innerHTML = shell(main, "success");
  bindShell();
  document.getElementById("btn-another").onclick = () => {
    saveLastOrder(null);
    navigate("order");
  };
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
  if (route === "success") return renderSuccess();
  if (route === "account") return renderAccount();
  return renderOrder();
}

window.addEventListener("hashchange", render);
if (!location.hash) location.hash = session ? "#/order" : "#/login";
render();
