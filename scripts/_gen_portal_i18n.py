"""Generate static/analyst-portal/i18n.js from Streamlit ui/i18n catalog."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ui.i18n import TRANSLATIONS  # noqa: E402

EXTRA = {
    "workspace": {"en": "Workspace", "th": "พื้นที่ทำงาน"},
    "hi_user": {"en": "Hi {name}", "th": "สวัสดี {name}"},
    "analyst_login_subtitle": {
        "en": "Internal fraud analyst login",
        "th": "เข้าสู่ระบบนักวิเคราะห์การทุจริตภายใน",
    },
    "pager_showing": {
        "en": "Showing {start}-{end} of {total} · Page {page} of {total_pages} · {size} per page",
        "th": "แสดง {start}-{end} จาก {total} · หน้า {page} จาก {total_pages} · หน้าละ {size}",
    },
    "pager_prev": {"en": "Prev", "th": "ก่อนหน้า"},
    "pager_next": {"en": "Next", "th": "ถัดไป"},
    "select_all_page": {"en": "Select all on this page", "th": "เลือกทั้งหมดในหน้านี้"},
    "col_order_short": {"en": "Order", "th": "คำสั่งซื้อ"},
    "col_delay_short": {"en": "Delay", "th": "หน่วง"},
    "col_placed_short": {"en": "Placed", "th": "สั่งเมื่อ"},
    "col_rule_short": {"en": "Rule", "th": "กฎ"},
    "backlog_title_overdue": {"en": "Backlog (overdue)", "th": "ค้างตรวจสอบ (เกินเวลา)"},
    "backlog_none_open": {
        "en": "No overdue orders. Review window still open for all queue items.",
        "th": "ไม่มีคำสั่งซื้อเกินเวลา ยังอยู่ในช่วงตรวจสอบทั้งหมด",
    },
    "backlog_past_delay": {
        "en": "{n} order(s) past delay window",
        "th": "คำสั่งซื้อเกินช่วงหน่วง {n} รายการ",
    },
    "backlog_max_overdue": {"en": "max overdue {mins}", "th": "เกินเวลามากสุด {mins}"},
    "backlog_showing_preview": {
        "en": "Showing {shown} of {total}. Overdue rows are highlighted in the full Review Queue below.",
        "th": "แสดง {shown} จาก {total} แถวที่เกินเวลาถูกไฮไลต์ในคิวตรวจสอบด้านล่าง",
    },
    "review_delay": {"en": "Review Delay", "th": "ระยะเวลารอตรวจสอบ"},
    "time_left": {"en": "Time Left", "th": "เวลาที่เหลือ"},
    "triggered_rule": {"en": "Triggered Rule", "th": "กฎที่ถูกเรียก"},
    "overdue_with_time": {"en": "Overdue {mins}", "th": "เกินเวลา {mins}"},
    "confirm_action": {"en": "Confirm action", "th": "ยืนยันการดำเนินการ"},
    "success": {"en": "Success", "th": "สำเร็จ"},
    "unknown_tab": {"en": "Unknown tab.", "th": "ไม่รู้จักแท็บนี้"},
    "loading_order": {"en": "Loading order {id}...", "th": "กำลังโหลดคำสั่งซื้อ {id}..."},
    "whitelisted": {"en": "Whitelisted", "th": "นำออกจากบัญชีดำแล้ว"},
    "now_blacklisted": {"en": "Now blacklisted", "th": "ขึ้นบัญชีดำแล้ว"},
    "could_not_load_rule_stats": {
        "en": "Could not load rule stats.",
        "th": "โหลดสถิติกฎไม่ได้",
    },
    "could_not_load_rule_status": {
        "en": "Could not load rule status.",
        "th": "โหลดสถานะกฎไม่ได้",
    },
    "lang_english": {"en": "English", "th": "English"},
    "lang_thai": {"en": "ไทย", "th": "ไทย"},
    "contact_admin_access": {
        "en": "Contact an administrator.",
        "th": "กรุณาติดต่อผู้ดูแลระบบ",
    },
    "minutes_short": {"en": "{n}m", "th": "{n}น."},
    "hours_mins_short": {"en": "{h}h {m}m", "th": "{h}ชม. {m}น."},
    "hours_short": {"en": "{h}h", "th": "{h}ชม."},
    "nav_analytics_ai": {
        "en": "Analytics AI Chatbot",
        "th": "แชทบอตเอไอการวิเคราะห์",
    },
    "overview": {"en": "Overview", "th": "ภาพรวม"},
    "statistics": {"en": "Statistics", "th": "สถิติ"},
    "orders_in_queue": {"en": "Orders in Queue", "th": "คำสั่งซื้อในคิว"},
    "backlog_overdue_label": {"en": "Backlog (Overdue)", "th": "ค้างตรวจสอบ (เกินเวลา)"},
    "period_this_month": {"en": "This Month", "th": "เดือนนี้"},
    "period_this_week": {"en": "This Week", "th": "สัปดาห์นี้"},
    "period_today": {"en": "Today", "th": "วันนี้"},
    "loading_dashboard": {"en": "Loading dashboard...", "th": "กำลังโหลดแดชบอร์ด..."},
    "loading_ellipsis": {"en": "Loading...", "th": "กำลังโหลด..."},
    "loading_workspace": {"en": "Loading workspace…", "th": "กำลังโหลดพื้นที่ทำงาน…"},
    "loading_named": {"en": "Loading {name}…", "th": "กำลังโหลด {name}…"},
    "admin_subtitle": {
        "en": "Manage queue, access, rules, and risk entities",
        "th": "จัดการคิว สิทธิ์ กฎ และเอนทิตีความเสี่ยง",
    },
    "admin_tab_blurb_queue": {
        "en": "Triage held and pending orders",
        "th": "คัดกรองคำสั่งซื้อที่ระงับและรอตรวจสอบ",
    },
    "admin_tab_blurb_blacklists": {
        "en": "Block or clear IP, phone, email",
        "th": "บล็อกหรือปลดบล็อก IP เบอร์โทร อีเมล",
    },
    "admin_tab_blurb_permissions": {
        "en": "Control page access by analyst",
        "th": "ควบคุมสิทธิ์เข้าถึงหน้าตามนักวิเคราะห์",
    },
    "admin_tab_blurb_users": {
        "en": "Create analysts and track work",
        "th": "สร้างนักวิเคราะห์และติดตามงาน",
    },
    "admin_tab_blurb_analytics": {
        "en": "Ops KPIs, trends, and volume",
        "th": "KPI การดำเนินงาน แนวโน้ม และปริมาณ",
    },
    "admin_tab_blurb_rules": {
        "en": "Tune actions, thresholds, windows",
        "th": "ปรับการดำเนินการ เกณฑ์ และช่วงเวลา",
    },
    "auto_approved_hold": {
        "en": "{n} order(s) auto-approved after hold window.",
        "th": "อนุมัติอัตโนมัติ {n} รายการหลังครบช่วงระงับ",
    },
    "chat_new": {"en": "New chat", "th": "แชทใหม่"},
    "chat_placeholder": {
        "en": "Message Analytics AI Chatbot…",
        "th": "พิมพ์ข้อความถึงแชทบอตเอไอ…",
    },
    "chat_disclaimer": {
        "en": "Answers are generated from live analytics data. Review insights before acting.",
        "th": "คำตอบสร้างจากข้อมูลวิเคราะห์แบบเรียลไทม์ โปรดตรวจสอบก่อนดำเนินการ",
    },
    "chat_empty_title": {
        "en": "How can I help with fraud analytics?",
        "th": "ต้องการความช่วยเหลือด้านการวิเคราะห์การทุจริตอย่างไร?",
    },
    "chat_empty_hint": {
        "en": "Ask a question, or start with one of these:",
        "th": "ถามคำถาม หรือเริ่มจากตัวอย่างเหล่านี้:",
    },
    "chat_ex_fraud_title": {"en": "Fraud volume", "th": "ปริมาณการทุจริต"},
    "chat_ex_region_title": {"en": "By region", "th": "ตามภูมิภาค"},
    "chat_ex_best_title": {"en": "Bestsellers", "th": "สินค้าขายดี"},
    "create_analyst_subtitle": {
        "en": "Spin up a profile so they can start reviewing risk work.",
        "th": "สร้างโปรไฟล์เพื่อเริ่มงานตรวจสอบความเสี่ยง",
    },
    "team_pulse": {"en": "Team pulse", "th": "ภาพรวมทีม"},
    "team_pulse_subtitle": {
        "en": "Who is clearing volume and catching fraud.",
        "th": "ใครเคลียร์งานและจับการทุจริตได้",
    },
    "analysts_count": {"en": "Analysts", "th": "นักวิเคราะห์"},
    "reviewed": {"en": "Reviewed", "th": "ตรวจสอบแล้ว"},
    "rejected": {"en": "Rejected", "th": "ปฏิเสธแล้ว"},
    "no_analysts_found": {"en": "No analysts found.", "th": "ไม่พบนักวิเคราะห์"},
    "confirmation_required": {"en": "Confirmation required", "th": "ต้องยืนยัน"},
    "create_analyst_confirm_title": {
        "en": "Create analyst profile",
        "th": "สร้างโปรไฟล์นักวิเคราะห์",
    },
}


def strip_md(s: str) -> str:
    return (
        s.replace("**", "")
        .replace("### ", "")
        .replace("#### ", "")
    )


def main() -> None:
    catalog = {**TRANSLATIONS, **EXTRA}
    clean = {
        k: {"en": strip_md(v["en"]), "th": strip_md(v["th"])}
        for k, v in catalog.items()
    }

    catalog_json = json.dumps(clean, ensure_ascii=False, indent=2)
    js = f"""/** Metro Cart portal i18n — English / Thai (parity with Streamlit ui/i18n.py). */
const LANG_KEY = "metro_cart_ui_lang";
const DEFAULT_LANG = "en";
const SUPPORTED_LANGS = ["en", "th"];

export const TRANSLATIONS = {catalog_json};

export function getLang() {{
  try {{
    const lang = localStorage.getItem(LANG_KEY) || DEFAULT_LANG;
    return SUPPORTED_LANGS.includes(lang) ? lang : DEFAULT_LANG;
  }} catch {{
    return DEFAULT_LANG;
  }}
}}

export function setLang(lang) {{
  const next = SUPPORTED_LANGS.includes(lang) ? lang : DEFAULT_LANG;
  localStorage.setItem(LANG_KEY, next);
  document.documentElement.lang = next === "th" ? "th" : "en";
  return next;
}}

/** Translate key; falls back en → key. Supports {{name}} style placeholders. */
export function t(key, params = {{}}) {{
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  let text = entry[getLang()] || entry.en || key;
  if (params && typeof params === "object") {{
    for (const [k, v] of Object.entries(params)) {{
      text = text.replaceAll("{{" + k + "}}", String(v ?? ""));
    }}
  }}
  return text;
}}

export function curSym() {{
  return "฿";
}}

export function languageToggleHtml({{ id = "lang-select" }} = {{}}) {{
  const lang = getLang();
  return `
    <label class="lang-toggle" title="${{t("language")}}">
      <span class="lang-toggle-label">${{t("language")}}</span>
      <select id="${{id}}" aria-label="${{t("language")}}">
        <option value="en" ${{lang === "en" ? "selected" : ""}}>${{t("lang_english")}}</option>
        <option value="th" ${{lang === "th" ? "selected" : ""}}>${{t("lang_thai")}}</option>
      </select>
    </label>`;
}}

export function bindLanguageToggle(selectId, onChange) {{
  const el = document.getElementById(selectId);
  if (!el) return;
  el.value = getLang();
  el.onchange = () => {{
    setLang(el.value);
    onChange?.(el.value);
  }};
}}

// Apply document lang on load
setLang(getLang());
"""

    out = ROOT / "static" / "analyst-portal" / "i18n.js"
    out.write_text(js, encoding="utf-8")
    print(f"wrote {out} ({len(clean)} keys, {out.stat().st_size} bytes)")

    # Also copy catalog JSON for React source
    json_out = ROOT / "analyst-portal" / "src" / "i18n" / "catalog.json"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {json_out}")


if __name__ == "__main__":
    main()
