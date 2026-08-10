"""Generate static/customer-portal/i18n.js from Streamlit catalog."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ui.i18n import TRANSLATIONS  # noqa: E402

KEYS = [
    "customer_app_title",
    "customer_app_subtitle",
    "login_welcome_back",
    "sign_in",
    "sign_in_cta",
    "user_id",
    "password",
    "invalid_login",
    "log_out",
    "language",
    "welcome_back",
    "contact_details",
    "name",
    "email",
    "phone",
    "no_phone_warning",
    "delivery_address",
    "street",
    "city",
    "state",
    "zip_code",
    "country",
    "sim_fields",
    "sim_caption",
    "ip_address",
    "program_track",
    "device",
    "product_selection",
    "product",
    "quantity",
    "total_price",
    "complete_purchase",
    "processing_purchase",
    "order_summary",
    "confirm_place_order",
    "confirm_purchase",
    "completing_purchase",
    "order_success",
    "your_order_id",
    "place_another_order",
    "err_name_required",
    "err_email_required",
    "err_phone_required",
    "err_address_required",
    "err_ip_required",
    "label_customer",
    "label_delivery_address",
    "label_ip",
    "label_device",
    "label_product",
    "label_amount",
    "cancel",
    "confirm",
    "ok",
    "processing",
    "nav_title",
]

EXTRA = {
    "lang_english": {"en": "English", "th": "English"},
    "lang_thai": {"en": "ไทย", "th": "ไทย"},
    "loading_sign_in": {"en": "Logging in…", "th": "กำลังเข้าสู่ระบบ..."},
    "shop_place_order": {"en": "Place Order", "th": "สั่งซื้อ"},
    "shop_browse": {"en": "Shop", "th": "ร้านค้า"},
    "shop_browse_lede": {
        "en": "Browse products and add them to your cart.",
        "th": "เลือกสินค้าและเพิ่มลงในตะกร้า",
    },
    "search": {"en": "Search", "th": "ค้นหา"},
    "search_products": {"en": "Search products", "th": "ค้นหาสินค้า"},
    "search_products_placeholder": {
        "en": "Search by name, category, or product ID…",
        "th": "ค้นหาด้วยชื่อ หมวดหมู่ หรือรหัสสินค้า…",
    },
    "clear_search": {"en": "Clear", "th": "ล้าง"},
    "search_no_results": {
        "en": "No products match your search.",
        "th": "ไม่พบสินค้าที่ตรงกับการค้นหา",
    },
    "search_results_count": {
        "en": "Showing {shown} of {total}",
        "th": "แสดง {shown} จาก {total}",
    },
    "all_categories": {"en": "All", "th": "ทั้งหมด"},
    "filter_by_category": {"en": "Category", "th": "หมวดหมู่"},
    "shop_cat_electronics": {"en": "Electronics", "th": "อิเล็กทรอนิกส์"},
    "shop_cat_appliances": {"en": "Appliances", "th": "เครื่องใช้ไฟฟ้า"},
    "shop_cat_furniture": {"en": "Furniture", "th": "เฟอร์นิเจอร์"},
    "shop_cat_vouchers": {"en": "Vouchers", "th": "บัตรของขวัญ"},
    "shop_categories_label": {"en": "Categories", "th": "หมวดหมู่"},
    "shop_vouchers_label": {"en": "Vouchers", "th": "บัตรของขวัญ"},
    "shop_products_heading": {"en": "Products", "th": "สินค้า"},
    "shop_vouchers": {"en": "Gift credit", "th": "เครดิตของขวัญ"},
    "shop_vouchers_kicker": {"en": "Digital rewards", "th": "รางวัลดิจิทัล"},
    "shop_vouchers_lede": {
        "en": "Prepaid gift credit kept separate from physical products.",
        "th": "เครดิตของขวัญแบบเติมเงิน แยกจากสินค้าทั่วไป",
    },
    "shop_voucher_note": {
        "en": "Digital gift credit — delivered after order approval.",
        "th": "เครดิตของขวัญดิจิทัล — ส่งมอบหลังอนุมัติคำสั่งซื้อ",
    },
    "pagination_page": {"en": "Page {page} of {pages}", "th": "หน้า {page} จาก {pages}"},
    "pagination_prev": {"en": "Previous", "th": "ก่อนหน้า"},
    "pagination_next": {"en": "Next", "th": "ถัดไป"},
    "shop_cart": {"en": "Cart", "th": "ตะกร้า"},
    "shop_cart_lede": {
        "en": "Uncheck items you do not want right now, then place an order for the selected items.",
        "th": "ยกเลิกเลือกสินค้าที่ไม่ต้องการตอนนี้ จากนั้นสั่งซื้อเฉพาะรายการที่เลือก",
    },
    "shop_cart_hint": {
        "en": "Cart has {count} item(s).",
        "th": "ตะกร้ามี {count} รายการ",
    },
    "add_to_cart": {"en": "Add to cart", "th": "เพิ่มลงตะกร้า"},
    "added_to_cart": {
        "en": "Added {name} × {qty} to cart.",
        "th": "เพิ่ม {name} × {qty} ลงตะกร้าแล้ว",
    },
    "view_cart": {"en": "View cart", "th": "ดูตะกร้า"},
    "view_details": {"en": "View details", "th": "ดูรายละเอียด"},
    "continue_shopping": {"en": "Continue shopping", "th": "เลือกสินค้าต่อ"},
    "your_cart": {"en": "Your cart", "th": "ตะกร้าของคุณ"},
    "cart_empty": {
        "en": "Your cart is empty. Add products from Shop.",
        "th": "ตะกร้าว่าง เพิ่มสินค้าจากหน้าร้านค้า",
    },
    "cart_uncheck_hint": {
        "en": "Use the checkbox to include or skip an item for this order. Unchecked items stay in your cart.",
        "th": "ใช้ช่องทำเครื่องหมายเพื่อรวมหรือข้ามสินค้าในคำสั่งนี้ รายการที่ไม่ได้เลือกจะยังอยู่ในตะกร้า",
    },
    "include_in_order": {"en": "Order", "th": "สั่ง"},
    "selected_items": {"en": "Selected items", "th": "รายการที่เลือก"},
    "no_items_selected": {
        "en": "Select at least one item to place an order.",
        "th": "เลือกอย่างน้อยหนึ่งรายการเพื่อสั่งซื้อ",
    },
    "place_selected_order": {"en": "Place order", "th": "สั่งซื้อ"},
    "unit_price": {"en": "Unit price", "th": "ราคาต่อหน่วย"},
    "line_total": {"en": "Line total", "th": "ยอดรายการ"},
    "remove": {"en": "Remove", "th": "ลบ"},
    "shop_confirmation": {"en": "Order Confirmation", "th": "ยืนยันคำสั่งซื้อ"},
    "shop_account": {"en": "My Account", "th": "บัญชีของฉัน"},
    "shop_section": {"en": "Shopping", "th": "ร้านค้า"},
    "hi_user": {"en": "Hi {name}", "th": "สวัสดี {name}"},
    "loading_catalog": {"en": "Loading catalog…", "th": "กำลังโหลดสินค้า…"},
    "order_status_label": {"en": "Status", "th": "สถานะ"},
    "order_status_approved": {"en": "Approved", "th": "อนุมัติแล้ว"},
    "order_status_pending_review": {"en": "Pending review", "th": "รอตรวจสอบ"},
    "order_status_on_hold": {"en": "On hold", "th": "ระงับชั่วคราว"},
    "order_status_rejected": {"en": "Rejected", "th": "ปฏิเสธ"},
    "shop_orders": {"en": "My Orders", "th": "คำสั่งซื้อของฉัน"},
    "shop_orders_lede": {
        "en": "Review past purchases and their current status.",
        "th": "ดูประวัติการสั่งซื้อและสถานะปัจจุบัน",
    },
    "shop_orders_empty": {
        "en": "You have not placed any orders yet.",
        "th": "คุณยังไม่มีคำสั่งซื้อ",
    },
    "shop_orders_count": {"en": "{count} order(s)", "th": "{count} คำสั่งซื้อ"},
    "shop_orders_items_summary": {
        "en": "{name} · {count} items",
        "th": "{name} · {count} รายการ",
    },
    "shop_order_detail": {"en": "Order detail", "th": "รายละเอียดคำสั่งซื้อ"},
    "loading_orders": {"en": "Loading orders…", "th": "กำลังโหลดคำสั่งซื้อ…"},
    "view_order": {"en": "View", "th": "ดู"},
    "view_order_history": {
        "en": "View order history",
        "th": "ดูประวัติคำสั่งซื้อ",
    },
    "back_to_orders": {"en": "Back to orders", "th": "กลับไปคำสั่งซื้อ"},
    "order_date": {"en": "Date", "th": "วันที่"},
    "customer_login_subtitle": {
        "en": "Customer purchase portal",
        "th": "พอร์ทัลสั่งซื้อสำหรับลูกค้า",
    },
    "shop_storefront_tagline": {
        "en": "City shopping, secured checkout — built for Metro Cart.",
        "th": "ช้อปในเมือง ชำระเงินอย่างปลอดภัย — สำหรับเมโทรคาร์ท",
    },
    "shop_checkout_lede": {
        "en": "Confirm your details, pick a product, and place the order in one flow.",
        "th": "ยืนยันข้อมูล เลือกสินค้า และสั่งซื้อในขั้นตอนเดียว",
    },
    "shop_success_lede": {
        "en": "Your order is in the system. Fraud checks may hold or approve it automatically.",
        "th": "คำสั่งซื้อเข้าสู่ระบบแล้ว การตรวจสอบอาจระงับหรืออนุมัติอัตโนมัติ",
    },
    "change_password": {"en": "Change Password", "th": "เปลี่ยนรหัสผ่าน"},
    "current_password": {"en": "Current Password", "th": "รหัสผ่านปัจจุบัน"},
    "new_password": {"en": "New Password", "th": "รหัสผ่านใหม่"},
    "confirm_new_password": {
        "en": "Confirm New Password",
        "th": "ยืนยันรหัสผ่านใหม่",
    },
    "update_password": {"en": "Update Password", "th": "อัปเดตรหัสผ่าน"},
    "password_change_missing_fields": {
        "en": "Please fill in all password fields.",
        "th": "กรุณากรอกข้อมูลรหัสผ่านให้ครบทุกช่อง",
    },
    "password_change_mismatch": {
        "en": "New password and confirmation do not match.",
        "th": "รหัสผ่านใหม่และการยืนยันไม่ตรงกัน",
    },
    "password_change_too_short": {
        "en": "New password must be at least 8 characters.",
        "th": "รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร",
    },
    "password_change_same_as_current": {
        "en": "New password must be different from the current password.",
        "th": "รหัสผ่านใหม่ต้องต่างจากรหัสผ่านปัจจุบัน",
    },
    "password_change_wrong_current": {
        "en": "Current password is incorrect.",
        "th": "รหัสผ่านปัจจุบันไม่ถูกต้อง",
    },
    "password_change_failed": {
        "en": "Unable to change password. Please try again.",
        "th": "ไม่สามารถเปลี่ยนรหัสผ่านได้ กรุณาลองอีกครั้ง",
    },
    "password_change_success": {
        "en": "Password updated successfully.",
        "th": "อัปเดตรหัสผ่านสำเร็จแล้ว",
    },
    "password_change_then_login": {
        "en": "Password updated. Please log in with your new password.",
        "th": "อัปเดตรหัสผ่านแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่",
    },
    "password_change_user_not_found": {
        "en": "No customer account found for that user ID.",
        "th": "ไม่พบบัญชีลูกค้าสำหรับรหัสผู้ใช้นี้",
    },
    "password_change_customer_not_found": {
        "en": "No customer account found for that user ID.",
        "th": "ไม่พบบัญชีลูกค้าสำหรับรหัสผู้ใช้นี้",
    },
    "password_reset_email_mismatch": {
        "en": "User ID and email do not match our records.",
        "th": "รหัสผู้ใช้และอีเมลไม่ตรงกับข้อมูลในระบบ",
    },
    "password_reset_success": {
        "en": "Password reset successfully. Please log in with your new password.",
        "th": "รีเซ็ตรหัสผ่านสำเร็จแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่",
    },
    "password_reset_hint": {
        "en": "Enter your User ID and the email on your account, then choose a new password (min. 8 characters).",
        "th": "กรอกรหัสผู้ใช้และอีเมลในบัญชี จากนั้นตั้งรหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)",
    },
    "forgot_password": {"en": "Forgot password?", "th": "ลืมรหัสผ่าน ?"},
    "password_change_login_hint": {
        "en": "Enter your user ID and current password, then choose a new password (min. 8 characters).",
        "th": "กรอกรหัสผู้ใช้และรหัสผ่านปัจจุบัน จากนั้นตั้งรหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)",
    },
    "back_to_login": {"en": "Back to Login", "th": "กลับไปหน้าเข้าสู่ระบบ"},
}


def strip_md(s: str) -> str:
    return s.replace("**", "").replace("### ", "").replace("#### ", "")


def main() -> None:
    catalog = {k: TRANSLATIONS[k] for k in KEYS if k in TRANSLATIONS}
    catalog.update(EXTRA)
    clean = {
        k: {"en": strip_md(v["en"]), "th": strip_md(v["th"])}
        for k, v in catalog.items()
    }
    catalog_json = json.dumps(clean, ensure_ascii=False, indent=2)
    js = f"""/** Customer shop i18n — EN/TH (parity with Streamlit ui/i18n.py). */
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

export function t(key, params = {{}}) {{
  const entry = TRANSLATIONS[key];
  let text = entry ? (entry[getLang()] || entry.en || "") : "";
  if (!text || text === key) {{
    text = String(key || "")
      .replaceAll("_", " ")
      .trim()
      .replace(/\\b\\w/g, (c) => c.toUpperCase());
  }}
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

setLang(getLang());
"""
    out = ROOT / "static" / "customer-portal" / "i18n.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(js, encoding="utf-8")
    print(f"wrote {out} ({len(clean)} keys)")


if __name__ == "__main__":
    main()
