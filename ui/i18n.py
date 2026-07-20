"""Lightweight UI i18n (English / Thai) — display-only, no functional impact.

Usage:
    from ui.i18n import t, cur, language_toggle

    language_toggle()                 # renders EN/TH switch (call once per page, top of page)
    st.title(t("app_title"))
    st.button(t("log_out"))
    st.metric(t("total_price"), f"{cur()}{total:,.2f}")

Notes:
- Only affects UI labels/text and the currency symbol shown (relabel only —
  the underlying numeric amount is never converted or changed).
- The AI chatbot's own conversation (prompts/answers) always stays in
  English regardless of the selected UI language, per product requirement.
"""
import streamlit as st

LANG_KEY = "ui_lang"
DEFAULT_LANG = "en"

TRANSLATIONS = {
    # --- App shells / headers ---
    "customer_app_title": {"en": "🛒 Metro Cart", "th": "🛒 เมโทรคาร์ท"},
    "customer_app_subtitle": {"en": "Customer Purchase Portal", "th": "พอร์ทัลการสั่งซื้อสำหรับลูกค้า"},
    "internal_app_title": {"en": "Metro Cart PRO", "th": "เมโทรคาร์ท โปร"},
    "internal_app_subtitle": {"en": "Fraud Analyst Workspace", "th": "พื้นที่ทำงานนักวิเคราะห์การทุจริต"},
    "internal_brand": {"en": "🏢 Metro Cart Internal", "th": "🏢 เมโทรคาร์ท ภายในองค์กร"},
    "employee_login": {"en": "Employee Login", "th": "เข้าสู่ระบบพนักงาน"},
    "welcome_user": {"en": "Welcome, **{name}**", "th": "ยินดีต้อนรับ **{name}**"},
    "welcome_back": {"en": "Welcome back, {name}!", "th": "ยินดีต้อนรับกลับมา {name}!"},

    # --- Common actions ---
    "log_in": {"en": "Log In", "th": "เข้าสู่ระบบ"},
    "log_out": {"en": "Log Out", "th": "ออกจากระบบ"},
    "cancel": {"en": "Cancel", "th": "ยกเลิก"},
    "confirm": {"en": "Confirm", "th": "ยืนยัน"},
    "save": {"en": "Save", "th": "บันทึก"},
    "language": {"en": "Language", "th": "ภาษา"},

    # --- Customer login / order form ---
    "customer_login": {"en": "Customer Login", "th": "เข้าสู่ระบบลูกค้า"},
    "user_id": {"en": "User ID", "th": "รหัสผู้ใช้"},
    "password": {"en": "Password", "th": "รหัสผ่าน"},
    "invalid_login": {"en": "Invalid user ID or password. Please try again.", "th": "รหัสผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"},
    "invalid_login_analyst": {"en": "Invalid username or password.", "th": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},
    "username": {"en": "Username", "th": "ชื่อผู้ใช้"},
    "contact_details": {"en": "👤 Contact Details", "th": "👤 ข้อมูลติดต่อ"},
    "name": {"en": "Name", "th": "ชื่อ"},
    "email": {"en": "Email", "th": "อีเมล"},
    "phone": {"en": "Phone", "th": "เบอร์โทรศัพท์"},
    "no_phone_warning": {"en": "No phone number on file for your account. Please contact support to add one before placing an order.", "th": "ไม่มีเบอร์โทรศัพท์ในบัญชีของคุณ กรุณาติดต่อฝ่ายสนับสนุนเพื่อเพิ่มเบอร์ก่อนสั่งซื้อ"},
    "delivery_address": {"en": "📍 Delivery Address", "th": "📍 ที่อยู่จัดส่ง"},
    "street": {"en": "Street", "th": "ถนน"},
    "city": {"en": "City", "th": "เมือง"},
    "state": {"en": "State", "th": "จังหวัด"},
    "zip_code": {"en": "ZIP Code", "th": "รหัสไปรษณีย์"},
    "country": {"en": "Country", "th": "ประเทศ"},
    "sim_fields": {"en": "⚙️ E-Commerce Demo Simulation Fields", "th": "⚙️ ฟิลด์จำลองสำหรับสาธิตอีคอมเมิร์ซ"},
    "sim_caption": {"en": "IP address, program track, and device are entered manually for testing purposes.", "th": "ที่อยู่ IP, กลุ่มโปรแกรม และอุปกรณ์ กรอกด้วยตนเองเพื่อการทดสอบ"},
    "ip_address": {"en": "IP Address", "th": "ที่อยู่ IP"},
    "program_track": {"en": "Program Track", "th": "กลุ่มโปรแกรม"},
    "device": {"en": "Device", "th": "อุปกรณ์"},
    "product_selection": {"en": "🛍️ Product Selection", "th": "🛍️ เลือกสินค้า"},
    "product": {"en": "Product", "th": "สินค้า"},
    "quantity": {"en": "Quantity", "th": "จำนวน"},
    "total_price": {"en": "Total Price", "th": "ราคารวม"},
    "complete_purchase": {"en": "Complete Purchase", "th": "ยืนยันการสั่งซื้อ"},
    "processing_purchase": {"en": "Processing your Metro Cart purchase...", "th": "กำลังดำเนินการสั่งซื้อของคุณ..."},
    "order_summary": {"en": "### Order Summary — Metro Cart", "th": "### สรุปคำสั่งซื้อ — เมโทรคาร์ท"},
    "confirm_place_order": {"en": "Confirm Place Order", "th": "ยืนยันการสั่งซื้อ"},
    "confirm_purchase": {"en": "Confirm Purchase", "th": "ยืนยันการซื้อ"},
    "completing_purchase": {"en": "Completing your purchase...", "th": "กำลังทำรายการซื้อให้เสร็จสิ้น..."},
    "order_success": {"en": "🎉 Order placed successfully. Thank you for shopping at Metro Cart!", "th": "🎉 สั่งซื้อสำเร็จแล้ว ขอบคุณที่เลือกซื้อกับเมโทรคาร์ท!"},
    "your_order_id": {"en": "Your Order ID", "th": "หมายเลขคำสั่งซื้อของคุณ"},
    "place_another_order": {"en": "Place Another Order", "th": "สั่งซื้อเพิ่มอีก"},
    "err_name_required": {"en": "Name is required.", "th": "กรุณากรอกชื่อ"},
    "err_email_required": {"en": "A valid email is required.", "th": "กรุณากรอกอีเมลที่ถูกต้อง"},
    "err_phone_required": {"en": "No phone number on file. Please contact support to add one before ordering.", "th": "ไม่มีเบอร์โทรศัพท์ในระบบ กรุณาติดต่อฝ่ายสนับสนุนก่อนสั่งซื้อ"},
    "err_address_required": {"en": "Complete delivery address (Street, City, State, and ZIP Code) is required.", "th": "กรุณากรอกที่อยู่จัดส่งให้ครบถ้วน (ถนน, เมือง, จังหวัด, รหัสไปรษณีย์)"},
    "err_ip_required": {"en": "Please enter an IP address.", "th": "กรุณากรอกที่อยู่ IP"},

    # --- Analyst dashboard ---
    "fraud_analyst_workspace": {"en": "🛡️ Fraud Analyst Workspace", "th": "🛡️ พื้นที่ทำงานนักวิเคราะห์การทุจริต"},
    "logged_in_as": {"en": "Logged in as: **{name}**", "th": "เข้าสู่ระบบในชื่อ: **{name}**"},
    "queue_overview": {"en": "📊 Queue Overview", "th": "📊 ภาพรวมคิวงาน"},
    "total_in_queue": {"en": "Total in Queue", "th": "จำนวนทั้งหมดในคิว"},
    "pending_review": {"en": "Pending Review", "th": "รอตรวจสอบ"},
    "on_hold": {"en": "On Hold", "th": "ระงับชั่วคราว"},
    "review_queue": {"en": "📋 Review Queue", "th": "📋 คิวตรวจสอบ"},
    "queue_clear": {"en": "✅ Queue is clear. No orders pending review.", "th": "✅ ไม่มีคำสั่งซื้อรอตรวจสอบ"},
    "select_all_queue": {"en": "Select All Orders in Queue", "th": "เลือกคำสั่งซื้อทั้งหมดในคิว"},
    "batch_actions": {"en": "⚡ Batch Actions ({n} selected)", "th": "⚡ ดำเนินการเป็นกลุ่ม (เลือก {n} รายการ)"},
    "batch_comments": {"en": "Batch Review Comments (applied to all selected orders, required)", "th": "ความคิดเห็นการตรวจสอบเป็นกลุ่ม (ใช้กับทุกรายการที่เลือก, จำเป็น)"},
    "approve_selected": {"en": "✅ Approve Selected", "th": "✅ อนุมัติที่เลือก"},
    "reject_selected": {"en": "🚫 Reject Selected", "th": "🚫 ปฏิเสธที่เลือก"},
    "warn_comment_approve": {"en": "Please provide a reason in the comments before approving.", "th": "กรุณาระบุเหตุผลในความคิดเห็นก่อนอนุมัติ"},
    "warn_comment_reject": {"en": "Please provide a reason in the comments before rejecting.", "th": "กรุณาระบุเหตุผลในความคิดเห็นก่อนปฏิเสธ"},
    "single_order_investigation": {"en": "🔍 Single Order Investigation", "th": "🔍 ตรวจสอบคำสั่งซื้อรายการเดียว"},
    "select_order_review": {"en": "Select an Order ID to review in detail", "th": "เลือกหมายเลขคำสั่งซื้อเพื่อตรวจสอบรายละเอียด"},
    "order_not_found": {"en": "Order not found (it may have just been resolved).", "th": "ไม่พบคำสั่งซื้อ (อาจเพิ่งได้รับการดำเนินการแล้ว)"},
    "customer_details": {"en": "**👤 Customer Details**", "th": "**👤 ข้อมูลลูกค้า**"},
    "order_details": {"en": "**📦 Order Details**", "th": "**📦 รายละเอียดคำสั่งซื้อ**"},
    "flagged_reason": {"en": "**🚨 Flagged Reason:** {reason}", "th": "**🚨 เหตุผลที่ถูกตั้งค่าสถานะ:** {reason}"},
    "analyst_decision": {"en": "⚖️ Analyst Decision", "th": "⚖️ การตัดสินใจของนักวิเคราะห์"},
    "review_comments": {"en": "Review Comments (required)", "th": "ความคิดเห็นการตรวจสอบ (จำเป็น)"},
    "approve_order": {"en": "✅ Approve Order", "th": "✅ อนุมัติคำสั่งซื้อ"},
    "reject_order": {"en": "🚫 Reject Order", "th": "🚫 ปฏิเสธคำสั่งซื้อ"},
    "reject_order_fraud": {"en": "☠️ Reject & Mark as Fraud", "th": "☠️ ปฏิเสธและระบุว่าเป็นการทุจริต"},
    "reject_selected_fraud": {"en": "☠️ Reject & Mark as Fraud", "th": "☠️ ปฏิเสธและระบุว่าเป็นการทุจริต"},
    "access_denied": {"en": "Access Denied. Please log in through the main portal.", "th": "ไม่ได้รับอนุญาต กรุณาเข้าสู่ระบบผ่านพอร์ทัลหลัก"},
    "blacklist_reason": {"en": "Blacklist Reason (required)", "th": "เหตุผลในการขึ้นบัญชีดำ (จำเป็น)"},
    "lock_ip": {"en": "Lock IP Address", "th": "ล็อกที่อยู่ IP"},
    "lock_phone": {"en": "Lock Phone Number", "th": "ล็อกเบอร์โทรศัพท์"},
    "lock_email": {"en": "Lock Email Address", "th": "ล็อกอีเมล"},

    # --- Admin panel ---
    "admin_control_panel": {"en": "⚙️ Admin Control Panel", "th": "⚙️ แผงควบคุมผู้ดูแลระบบ"},
    "tab_review_queue": {"en": "⚖️ Review Queue (Override)", "th": "⚖️ คิวตรวจสอบ (แทนที่การตัดสินใจ)"},
    "tab_blacklists": {"en": "🛡️ Entity Blacklists", "th": "🛡️ บัญชีดำ"},
    "tab_permissions": {"en": "🔐 Analyst Permissions", "th": "🔐 สิทธิ์การเข้าถึงของนักวิเคราะห์"},
    "tab_user_mgmt": {"en": "👥 User Management", "th": "👥 การจัดการผู้ใช้งาน"},
    "tab_analytics": {"en": "📊 Analytics", "th": "📊 การวิเคราะห์ข้อมูล"},
    "tab_rule_mgmt": {"en": "📋 Rule Management", "th": "📋 การจัดการกฎ"},
    "user_management": {"en": "### 👥 User Management", "th": "### 👥 การจัดการผู้ใช้งาน"},
    "user_mgmt_caption": {"en": "Create new analyst profiles and monitor current team performance.", "th": "สร้างโปรไฟล์นักวิเคราะห์ใหม่และติดตามผลการทำงานของทีม"},
    "create_analyst_profile": {"en": "➕ Create New Analyst Profile", "th": "➕ สร้างโปรไฟล์นักวิเคราะห์ใหม่"},
    "analyst_id": {"en": "Analyst ID", "th": "รหัสนักวิเคราะห์"},
    "employee_name": {"en": "Employee Name", "th": "ชื่อพนักงาน"},
    "role": {"en": "Role", "th": "ตำแหน่ง"},
    "confirm_create_analyst_chk": {"en": "⚠️ I confirm that I want to create this analyst profile.", "th": "⚠️ ฉันยืนยันว่าต้องการสร้างโปรไฟล์นักวิเคราะห์นี้"},
    "create_analyst": {"en": "Create Analyst", "th": "สร้างนักวิเคราะห์"},
    "err_all_fields_required": {"en": "All fields are required.", "th": "กรุณากรอกข้อมูลให้ครบทุกช่อง"},
    "warn_confirm_checkbox": {"en": "Please check the confirmation box to proceed with creation.", "th": "กรุณาทำเครื่องหมายยืนยันเพื่อดำเนินการสร้าง"},
    "analyst_performance": {"en": "#### 📈 Analyst Performance", "th": "#### 📈 ผลการปฏิบัติงานของนักวิเคราะห์"},
    "entity_blacklist_mgmt": {"en": "### 🛡️ Entity Blacklist Management", "th": "### 🛡️ การจัดการบัญชีดำ"},
    "blacklist_caption": {"en": "Check, blacklist, or whitelist IP addresses, phone numbers, and emails.", "th": "ตรวจสอบ ขึ้นบัญชีดำ หรือนำออกจากบัญชีดำ สำหรับ IP, เบอร์โทรศัพท์ และอีเมล"},
    "entity_type": {"en": "Entity Type", "th": "ประเภทข้อมูล"},
    "ip_lookup": {"en": "IP Lookup", "th": "ค้นหาที่อยู่ IP"},
    "phone_lookup": {"en": "Phone Lookup", "th": "ค้นหาเบอร์โทรศัพท์"},
    "email_lookup": {"en": "Email Lookup", "th": "ค้นหาอีเมล"},
    "check_ip": {"en": "🔍 Check IP", "th": "🔍 ตรวจสอบ IP"},
    "check_phone": {"en": "🔍 Check Phone", "th": "🔍 ตรวจสอบเบอร์โทรศัพท์"},
    "check_email": {"en": "🔍 Check Email", "th": "🔍 ตรวจสอบอีเมล"},
    "whitelist_ip": {"en": "Whitelist IP", "th": "นำ IP ออกจากบัญชีดำ"},
    "whitelist_phone": {"en": "Whitelist Phone", "th": "นำเบอร์โทรศัพท์ออกจากบัญชีดำ"},
    "whitelist_email": {"en": "Whitelist Email", "th": "นำอีเมลออกจากบัญชีดำ"},
    "blacklist_ip": {"en": "Blacklist IP", "th": "ขึ้นบัญชีดำ IP"},
    "blacklist_phone": {"en": "Blacklist Phone", "th": "ขึ้นบัญชีดำเบอร์โทรศัพท์"},
    "blacklist_email": {"en": "Blacklist Email", "th": "ขึ้นบัญชีดำอีเมล"},
    "reason": {"en": "Reason", "th": "เหตุผล"},
    "entity_ip": {"en": "🌐 IP Address", "th": "🌐 ที่อยู่ IP"},
    "entity_phone": {"en": "📱 Phone Number", "th": "📱 เบอร์โทรศัพท์"},
    "entity_email": {"en": "📧 Email", "th": "📧 อีเมล"},    "analyst_page_permissions": {"en": "### 🔐 Analyst Page Permissions", "th": "### 🔐 สิทธิ์การเข้าถึงหน้าของนักวิเคราะห์"},
    "permissions_caption": {"en": "Grant or revoke access to each page. Admins always have full access and aren't listed here.", "th": "ให้หรือเพิกถอนสิทธิ์การเข้าถึงแต่ละหน้า ผู้ดูแลระบบมีสิทธิ์เต็มเสมอและจะไม่แสดงในรายการนี้"},
    "no_non_admin": {"en": "No non-admin analysts exist yet.", "th": "ยังไม่มีนักวิเคราะห์ที่ไม่ใช่ผู้ดูแลระบบ"},
    "select_analyst_edit": {"en": "Select Analyst to Edit", "th": "เลือกนักวิเคราะห์ที่ต้องการแก้ไข"},
    "save_permissions": {"en": "Save Permissions", "th": "บันทึกสิทธิ์การเข้าถึง"},
    "warn_save_perms": {"en": "Please check the confirmation box to save these permissions.", "th": "กรุณาทำเครื่องหมายยืนยันเพื่อบันทึกสิทธิ์การเข้าถึงนี้"},
    "recent_orders": {"en": "### Recent Orders", "th": "### คำสั่งซื้อล่าสุด"},
    "total_orders": {"en": "Total Orders", "th": "คำสั่งซื้อทั้งหมด"},
    "total_fraud_orders": {"en": "Total Fraud Orders", "th": "คำสั่งซื้อที่เป็นการทุจริตทั้งหมด"},
    "fraud_rate": {"en": "Fraud Rate", "th": "อัตราการทุจริต"},
    "no_orders_this_month": {"en": "No orders placed yet this month.", "th": "ยังไม่มีคำสั่งซื้อในเดือนนี้"},
    "recent_orders_live": {"en": "#### 🕒 Recent Orders", "th": "#### 🕒 คำสั่งซื้อล่าสุด"},
    "recent_orders_caption": {"en": "Live view of the latest system transactions.", "th": "มุมมองแบบเรียลไทม์ของธุรกรรมล่าสุดในระบบ"},
    "no_recent_orders": {"en": "No recent orders found.", "th": "ไม่พบคำสั่งซื้อล่าสุด"},
    "rule_trigger_stats": {"en": "### 📋 Rule Trigger Statistics", "th": "### 📋 สถิติการทำงานของกฎ"},
    "rule_stats_caption": {"en": "Visibility into which automated fraud rules are firing most frequently.", "th": "ภาพรวมของกฎตรวจจับการทุจริตที่ทำงานบ่อยที่สุด"},
    "no_rule_data": {"en": "No rule trigger data available to display.", "th": "ไม่มีข้อมูลการทำงานของกฎให้แสดง"},
    "rule_config_mgmt": {"en": "### ⚙️ Rule Configuration Management", "th": "### ⚙️ การจัดการค่ากำหนดของกฎ"},
    "rule_config_caption": {"en": "Adjust actions, thresholds, and time windows for e-commerce fraud detection rules.", "th": "ปรับการดำเนินการ เกณฑ์ และช่วงเวลาสำหรับกฎตรวจจับการทุจริตในอีคอมเมิร์ซ"},
    "no_rules_found": {"en": "No rules found in the database.", "th": "ไม่พบกฎในฐานข้อมูล"},
    "select_rule_modify": {"en": "Select Rule to Modify", "th": "เลือกกฎที่ต้องการแก้ไข"},
    "configuration_parameters": {"en": "Configuration Parameters", "th": "พารามิเตอร์การกำหนดค่า"},
    "action_locked_hold": {"en": "🔒 **Action is locked to HOLD** for the P2 iPhone 16 Rule.", "th": "🔒 **การดำเนินการถูกล็อกไว้ที่ HOLD** สำหรับกฎ P2 iPhone 16"},
    "action_locked_rejected": {"en": "🔒 **Action is strictly locked to REJECTED** for Blacklist entities.", "th": "🔒 **การดำเนินการถูกล็อกไว้ที่ REJECTED** สำหรับรายการในบัญชีดำ"},
    "rule_action": {"en": "Rule Action", "th": "การดำเนินการของกฎ"},
    "threshold": {"en": "Threshold", "th": "เกณฑ์"},
    "threshold_na": {"en": "Threshold N/A", "th": "ไม่มีเกณฑ์"},
    "time_interval": {"en": "Time Interval", "th": "ช่วงเวลา"},
    "interval_na": {"en": "Interval N/A", "th": "ไม่มีช่วงเวลา"},
    "unit": {"en": "Unit", "th": "หน่วย"},
    "review_changes": {"en": "Review Changes", "th": "ตรวจสอบการเปลี่ยนแปลง"},

    # --- Sidebar navigation (analyst_app.py) ---
    "nav_title": {"en": "Navigation", "th": "เมนูนำทาง"},
    "nav_fraud_dashboard": {"en": "Fraud Analyst Dashboard", "th": "แดชบอร์ดนักวิเคราะห์การทุจริต"},
    "nav_admin_panel": {"en": "Admin Control Panel", "th": "แผงควบคุมผู้ดูแลระบบ"},
    "nav_power_bi": {"en": "Analytics Dashboards", "th": "แดชบอร์ดการวิเคราะห์ข้อมูล"},
    "nav_ai_chatbot": {"en": "AI Chatbot", "th": "แชทบอตเอไอ"},
    "no_page_access": {"en": "You don't have access to any pages yet. Contact an Admin to request access.", "th": "คุณยังไม่มีสิทธิ์เข้าถึงหน้าใด กรุณาติดต่อผู้ดูแลระบบเพื่อขอสิทธิ์"},

    # --- Currency-formatted labels ---
    "amount": {"en": "Amount", "th": "จำนวนเงิน"},
    "total_amount": {"en": "Total Amount", "th": "ยอดรวม"},
}


def _lang() -> str:
    return st.session_state.get(LANG_KEY, DEFAULT_LANG)


def t(key: str, **kwargs) -> str:
    """Translate a UI string key into the active language, with optional
    .format(**kwargs) substitution. Falls back to English, then the raw key,
    if a translation is missing."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_lang(), entry.get("en", key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def cur_sym() -> str:
    """Currency symbol shown in the UI. Always Thai Baht (฿), regardless of
    the selected UI language — display label only, the underlying numeric
    amount is never converted or changed."""
    return "฿"


def language_toggle():
    """Renders a compact EN / Thai language switch. Call once near the top
    of each page (e.g. right after apply_theme() / render_app_shell())."""
    if LANG_KEY not in st.session_state:
        st.session_state[LANG_KEY] = DEFAULT_LANG

    cols = st.columns([0.82, 0.18])
    with cols[1]:
        choice = st.selectbox(
            t("language"),
            options=["en", "th"],
            format_func=lambda code: "English" if code == "en" else "ไทย (Thai)",
            index=["en", "th"].index(st.session_state[LANG_KEY]),
            key="_lang_selector",
            label_visibility="collapsed",
        )
    if choice != st.session_state[LANG_KEY]:
        st.session_state[LANG_KEY] = choice
        st.rerun()
