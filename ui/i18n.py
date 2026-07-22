"""Lightweight UI i18n (English / Thai) — display-only, no functional impact.

Usage:
    from ui.i18n import t, cur_sym, language_toggle

    language_toggle()
    st.title(t("app_title"))
    st.button(t("log_out"))

Notes:
- Only affects UI labels/text. Currency symbol is always ฿ (display only).
- AI chatbot conversation stays in English regardless of UI language.
- Missing keys fall back to English, then the raw key.
- Every entry MUST have both "en" and "th".
"""
from __future__ import annotations

import streamlit as st

LANG_KEY = "ui_lang"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "th")

# ---------------------------------------------------------------------------
# Translation catalog
# ---------------------------------------------------------------------------
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- App shells / headers ---
    "customer_app_title": {"en": "🛒 Metro Cart", "th": "🛒 เมโทรคาร์ท"},
    "customer_app_subtitle": {
        "en": "Customer Purchase Portal",
        "th": "พอร์ทัลสั่งซื้อสำหรับลูกค้า",
    },
    "internal_app_title": {"en": "Metro Cart PRO", "th": "เมโทรคาร์ท โปร"},
    "internal_app_subtitle": {
        "en": "Fraud Analyst Workspace",
        "th": "พื้นที่ทำงานนักวิเคราะห์การทุจริต",
    },
    "internal_brand": {
        "en": "🏢 Metro Cart Internal",
        "th": "🏢 เมโทรคาร์ท (ภายในองค์กร)",
    },
    "employee_login": {"en": "Employee Login", "th": "เข้าสู่ระบบพนักงาน"},
    "welcome_user": {"en": "Welcome, **{name}**", "th": "ยินดีต้อนรับ **{name}**"},
    "welcome_back": {"en": "Welcome back, {name}!", "th": "ยินดีต้อนรับกลับ {name}!"},

    # --- Common actions ---
    "log_in": {"en": "Log In", "th": "เข้าสู่ระบบ"},
    "log_out": {"en": "Log Out", "th": "ออกจากระบบ"},
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
        "en": "No analyst account found for that username.",
        "th": "ไม่พบบัญชีนักวิเคราะห์สำหรับชื่อผู้ใช้นี้",
    },
    "password_change_login_hint": {
        "en": "Enter your username and current password, then choose a new password (min. 8 characters).",
        "th": "กรอกชื่อผู้ใช้และรหัสผ่านปัจจุบัน จากนั้นตั้งรหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)",
    },
    "back_to_login": {"en": "Back to login", "th": "กลับไปหน้าเข้าสู่ระบบ"},
    "cancel": {"en": "Cancel", "th": "ยกเลิก"},
    "confirm": {"en": "Confirm", "th": "ยืนยัน"},
    "ok": {"en": "OK", "th": "ตกลง"},
    "save": {"en": "Save", "th": "บันทึก"},
    "language": {"en": "Language", "th": "ภาษา"},
    "processing": {"en": "Processing...", "th": "กำลังดำเนินการ..."},
    "minutes_unit": {"en": "{n} min", "th": "{n} นาที"},
    "seconds_unit": {"en": "{n}s", "th": "{n} วินาที"},
    "overdue_flag": {"en": "🔴 Overdue", "th": "🔴 เกินเวลา"},

    # --- Customer login / order form ---
    "customer_login": {"en": "Customer Login", "th": "เข้าสู่ระบบลูกค้า"},
    "user_id": {"en": "User ID", "th": "รหัสผู้ใช้"},
    "password": {"en": "Password", "th": "รหัสผ่าน"},
    "invalid_login": {
        "en": "Invalid user ID or password. Please try again.",
        "th": "รหัสผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองอีกครั้ง",
    },
    "invalid_login_analyst": {
        "en": "Invalid username or password.",
        "th": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
    },
    "username": {"en": "Username", "th": "ชื่อผู้ใช้"},
    "contact_details": {"en": "👤 Contact Details", "th": "👤 ข้อมูลติดต่อ"},
    "name": {"en": "Name", "th": "ชื่อ"},
    "email": {"en": "Email", "th": "อีเมล"},
    "phone": {"en": "Phone", "th": "เบอร์โทรศัพท์"},
    "no_phone_warning": {
        "en": "No phone number on file for your account. Please contact support to add one before placing an order.",
        "th": "บัญชีของคุณยังไม่มีเบอร์โทรศัพท์ กรุณาติดต่อฝ่ายสนับสนุนเพื่อเพิ่มเบอร์ก่อนสั่งซื้อ",
    },
    "delivery_address": {"en": "📍 Delivery Address", "th": "📍 ที่อยู่จัดส่ง"},
    "street": {"en": "Street", "th": "ถนน / ซอย"},
    "city": {"en": "City", "th": "อำเภอ / เขต"},
    "state": {"en": "State", "th": "จังหวัด"},
    "zip_code": {"en": "ZIP Code", "th": "รหัสไปรษณีย์"},
    "country": {"en": "Country", "th": "ประเทศ"},
    "sim_fields": {
        "en": "⚙️ E-Commerce Demo Simulation Fields",
        "th": "⚙️ ฟิลด์จำลองสำหรับการสาธิตอีคอมเมิร์ซ",
    },
    "sim_caption": {
        "en": "IP address, program track, and device are entered manually for testing purposes.",
        "th": "กรอกที่อยู่ IP กลุ่มโปรแกรม และอุปกรณ์ด้วยตนเองเพื่อการทดสอบ",
    },
    "ip_address": {"en": "IP Address", "th": "ที่อยู่ IP"},
    "program_track": {"en": "Program Track", "th": "กลุ่มโปรแกรม"},
    "device": {"en": "Device", "th": "อุปกรณ์"},
    "product_selection": {"en": "🛍️ Product Selection", "th": "🛍️ เลือกสินค้า"},
    "product": {"en": "Product", "th": "สินค้า"},
    "quantity": {"en": "Quantity", "th": "จำนวน"},
    "total_price": {"en": "Total Price", "th": "ราคารวม"},
    "complete_purchase": {"en": "Complete Purchase", "th": "ดำเนินการสั่งซื้อ"},
    "processing_purchase": {
        "en": "Processing your Metro Cart purchase...",
        "th": "กำลังดำเนินการสั่งซื้อจากเมโทรคาร์ท...",
    },
    "order_summary": {
        "en": "### Order Summary — Metro Cart",
        "th": "### สรุปคำสั่งซื้อ — เมโทรคาร์ท",
    },
    "confirm_place_order": {"en": "Confirm Place Order", "th": "ยืนยันการสั่งซื้อ"},
    "confirm_purchase": {"en": "Confirm Purchase", "th": "ยืนยันการซื้อ"},
    "completing_purchase": {
        "en": "Completing your purchase...",
        "th": "กำลังทำรายการซื้อให้เสร็จสิ้น...",
    },
    "order_success": {
        "en": "🎉 Order placed successfully. Thank you for shopping at Metro Cart!",
        "th": "🎉 สั่งซื้อสำเร็จแล้ว ขอบคุณที่เลือกซื้อกับเมโทรคาร์ท!",
    },
    "your_order_id": {"en": "Your Order ID", "th": "หมายเลขคำสั่งซื้อของคุณ"},
    "place_another_order": {"en": "Place Another Order", "th": "สั่งซื้อเพิ่ม"},
    "err_name_required": {"en": "Name is required.", "th": "กรุณากรอกชื่อ"},
    "err_email_required": {
        "en": "A valid email is required.",
        "th": "กรุณากรอกอีเมลที่ถูกต้อง",
    },
    "err_phone_required": {
        "en": "No phone number on file. Please contact support to add one before ordering.",
        "th": "ไม่มีเบอร์โทรศัพท์ในระบบ กรุณาติดต่อฝ่ายสนับสนุนก่อนสั่งซื้อ",
    },
    "err_address_required": {
        "en": "Complete delivery address (Street, City, State, and ZIP Code) is required.",
        "th": "กรุณากรอกที่อยู่จัดส่งให้ครบถ้วน (ถนน, อำเภอ/เขต, จังหวัด, รหัสไปรษณีย์)",
    },
    "err_ip_required": {
        "en": "Please enter an IP address.",
        "th": "กรุณากรอกที่อยู่ IP",
    },
    "label_customer": {"en": "Customer", "th": "ลูกค้า"},
    "label_delivery_address": {"en": "Delivery Address", "th": "ที่อยู่จัดส่ง"},
    "label_ip": {"en": "IP", "th": "IP"},
    "label_device": {"en": "Device", "th": "อุปกรณ์"},
    "label_product": {"en": "Product", "th": "สินค้า"},
    "label_amount": {"en": "Amount", "th": "จำนวนเงิน"},
    "label_address": {"en": "Address", "th": "ที่อยู่"},
    "label_placed_at": {"en": "Placed At", "th": "เวลาที่สั่งซื้อ"},
    "label_name": {"en": "Name", "th": "ชื่อ"},
    "err_api_connection": {
        "en": "API connection failed or timed out. Please ensure the backend server is running and try again.",
        "th": "เชื่อมต่อ API ไม่สำเร็จหรือหมดเวลา กรุณาตรวจสอบว่าเซิร์ฟเวอร์ทำงานอยู่แล้วลองอีกครั้ง",
    },
    "err_order_api_failed": {
        "en": "Failed to call order API. See logs or backend.",
        "th": "เรียก API สั่งซื้อไม่สำเร็จ กรุณาดูบันทึกหรือตรวจสอบแบ็กเอนด์",
    },
    "err_completing_order": {
        "en": "Error while completing order: {exc}",
        "th": "เกิดข้อผิดพลาดขณะทำรายการ: {exc}",
    },

    # --- Analyst dashboard ---
    "fraud_analyst_workspace": {
        "en": "🛡️ Fraud Analyst Workspace",
        "th": "🛡️ พื้นที่ทำงานนักวิเคราะห์การทุจริต",
    },
    "logged_in_as": {
        "en": "Logged in as: **{name}**",
        "th": "เข้าสู่ระบบในชื่อ: **{name}**",
    },
    "queue_overview": {"en": "📊 Queue Overview", "th": "📊 ภาพรวมคิวงาน"},
    "total_in_queue": {"en": "Total in Queue", "th": "จำนวนทั้งหมดในคิว"},
    "pending_review": {"en": "Pending Review", "th": "รอตรวจสอบ"},
    "on_hold": {"en": "On Hold", "th": "ระงับชั่วคราว"},
    "review_queue": {"en": "📋 Review Queue", "th": "📋 คิวตรวจสอบ"},
    "queue_clear": {
        "en": "✅ Queue is clear. No orders pending review.",
        "th": "✅ คิวว่าง ไม่มีคำสั่งซื้อรอตรวจสอบ",
    },
    "select_all_queue": {
        "en": "Select All Orders in Queue",
        "th": "เลือกคำสั่งซื้อทั้งหมดในคิว",
    },
    "batch_actions": {
        "en": "⚡ Batch Actions ({n} selected)",
        "th": "⚡ ดำเนินการเป็นกลุ่ม (เลือก {n} รายการ)",
    },
    "batch_comments": {
        "en": "Batch Review Comments (applied to all selected orders, required)",
        "th": "ความคิดเห็นการตรวจสอบแบบกลุ่ม (ใช้กับทุกรายการที่เลือก — จำเป็น)",
    },
    "approve_selected": {"en": "✅ Approve Selected", "th": "✅ อนุมัติรายการที่เลือก"},
    "reject_selected": {"en": "🚫 Reject Selected", "th": "🚫 ปฏิเสธรายการที่เลือก"},
    "warn_comment_approve": {
        "en": "Please provide a reason in the comments before approving.",
        "th": "กรุณาระบุเหตุผลในความคิดเห็นก่อนอนุมัติ",
    },
    "warn_comment_reject": {
        "en": "Please provide a reason in the comments before rejecting.",
        "th": "กรุณาระบุเหตุผลในความคิดเห็นก่อนปฏิเสธ",
    },
    "single_order_investigation": {
        "en": "🔍 Single Order Investigation",
        "th": "🔍 ตรวจสอบคำสั่งซื้อรายการเดียว",
    },
    "select_order_review": {
        "en": "Select an Order ID to review in detail",
        "th": "เลือกหมายเลขคำสั่งซื้อเพื่อดูรายละเอียด",
    },
    "order_not_found": {
        "en": "Order not found (it may have just been resolved).",
        "th": "ไม่พบคำสั่งซื้อ (อาจเพิ่งได้รับการดำเนินการแล้ว)",
    },
    "customer_details": {"en": "**👤 Customer Details**", "th": "**👤 ข้อมูลลูกค้า**"},
    "order_details": {"en": "**📦 Order Details**", "th": "**📦 รายละเอียดคำสั่งซื้อ**"},
    "flagged_reason": {
        "en": "**🚨 Flagged Reason:** {reason}",
        "th": "**🚨 เหตุผลที่ถูกตั้งค่าสถานะ:** {reason}",
    },
    "analyst_decision": {
        "en": "⚖️ Analyst Decision",
        "th": "⚖️ การตัดสินใจของนักวิเคราะห์",
    },
    "review_comments": {
        "en": "Review Comments (required)",
        "th": "ความคิดเห็นการตรวจสอบ (จำเป็น)",
    },
    "approve_order": {"en": "✅ Approve Order", "th": "✅ อนุมัติคำสั่งซื้อ"},
    "reject_order": {"en": "🚫 Reject Order", "th": "🚫 ปฏิเสธคำสั่งซื้อ"},
    "reject_order_fraud": {
        "en": "☠️ Reject & Mark as Fraud",
        "th": "☠️ ปฏิเสธและระบุว่าเป็นการทุจริต",
    },
    "reject_selected_fraud": {
        "en": "☠️ Reject & Mark as Fraud",
        "th": "☠️ ปฏิเสธและระบุว่าเป็นการทุจริต",
    },
    "access_denied": {
        "en": "Access Denied. Please log in through the main portal.",
        "th": "ไม่มีสิทธิ์เข้าถึง กรุณาเข้าสู่ระบบผ่านพอร์ทัลหลัก",
    },
    "blacklist_reason": {
        "en": "Blacklist Reason (required)",
        "th": "เหตุผลในการขึ้นบัญชีดำ (จำเป็น)",
    },
    "lock_ip": {"en": "Lock IP Address", "th": "ล็อกที่อยู่ IP"},
    "lock_phone": {"en": "Lock Phone Number", "th": "ล็อกเบอร์โทรศัพท์"},
    "lock_email": {"en": "Lock Email Address", "th": "ล็อกอีเมล"},
    "blacklisted_suffix": {"en": "🚫 *(blacklisted)*", "th": "🚫 *(อยู่ในบัญชีดำ)*"},
    "err_blacklist_reason_required": {
        "en": "A reason is required to blacklist this entity.",
        "th": "ต้องระบุเหตุผลก่อนขึ้นบัญชีดำ",
    },
    "already_blacklisted_ip": {
        "en": "🌐 IP **{value}** is already blacklisted (reason: {reason}, by {by} on {at}).",
        "th": "🌐 IP **{value}** อยู่ในบัญชีดำแล้ว (เหตุผล: {reason}, โดย {by} เมื่อ {at})",
    },
    "already_blacklisted_phone": {
        "en": "📱 Phone **{value}** is already blacklisted (reason: {reason}, by {by} on {at}).",
        "th": "📱 เบอร์ **{value}** อยู่ในบัญชีดำแล้ว (เหตุผล: {reason}, โดย {by} เมื่อ {at})",
    },
    "already_blacklisted_email": {
        "en": "📧 Email **{value}** is already blacklisted (reason: {reason}, by {by} on {at}).",
        "th": "📧 อีเมล **{value}** อยู่ในบัญชีดำแล้ว (เหตุผล: {reason}, โดย {by} เมื่อ {at})",
    },
    "security_blacklist_ip": {
        "en": "🌐 Security Action: Blacklist IP {value}",
        "th": "🌐 การรักษาความปลอดภัย: ขึ้นบัญชีดำ IP {value}",
    },
    "security_blacklist_phone": {
        "en": "📱 Security Action: Blacklist Phone {value}",
        "th": "📱 การรักษาความปลอดภัย: ขึ้นบัญชีดำเบอร์ {value}",
    },
    "security_blacklist_email": {
        "en": "📧 Security Action: Blacklist Email {value}",
        "th": "📧 การรักษาความปลอดภัย: ขึ้นบัญชีดำอีเมล {value}",
    },

    # --- Confirmation dialogs ---
    "dlg_confirm_approval_title": {"en": "Confirm Approval", "th": "ยืนยันการอนุมัติ"},
    "dlg_confirm_rejection_title": {"en": "Confirm Rejection", "th": "ยืนยันการปฏิเสธ"},
    "dlg_confirm_batch_approval_title": {
        "en": "Confirm Batch Approval",
        "th": "ยืนยันการอนุมัติเป็นกลุ่ม",
    },
    "dlg_confirm_batch_rejection_title": {
        "en": "Confirm Batch Rejection",
        "th": "ยืนยันการปฏิเสธเป็นกลุ่ม",
    },
    "dlg_no_backlog_title": {"en": "No Backlog Orders", "th": "ไม่มีคำสั่งซื้อค้างตรวจสอบ"},
    "dlg_confirm_blacklist_title": {"en": "Confirm Blacklist", "th": "ยืนยันการขึ้นบัญชีดำ"},
    "confirm_approve_one": {
        "en": "Are you sure you want to approve this order?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการอนุมัติคำสั่งซื้อนี้?",
    },
    "confirm_reject_one": {
        "en": "Are you sure you want to reject this order?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการปฏิเสธคำสั่งซื้อนี้?",
    },
    "confirm_fraud_one": {
        "en": "Are you sure you want to mark this order as fraud?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการระบุว่าคำสั่งซื้อนี้เป็นการทุจริต?",
    },
    "confirm_approve_all_backlog": {
        "en": "Are you sure you want to approve all backlog orders?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการอนุมัติคำสั่งซื้อค้างตรวจสอบทั้งหมด?",
    },
    "confirm_reject_all_backlog": {
        "en": "Are you sure you want to reject all backlog orders?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการปฏิเสธคำสั่งซื้อค้างตรวจสอบทั้งหมด?",
    },
    "confirm_fraud_all_backlog": {
        "en": "Are you sure you want to mark all backlog orders as fraud?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการระบุว่าคำสั่งซื้อค้างตรวจสอบทั้งหมดเป็นการทุจริต?",
    },
    "confirm_approve_selected": {
        "en": "Are you sure you want to approve {n} selected orders?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการอนุมัติคำสั่งซื้อที่เลือก {n} รายการ?",
    },
    "confirm_reject_selected": {
        "en": "Are you sure you want to reject {n} selected orders?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการปฏิเสธคำสั่งซื้อที่เลือก {n} รายการ?",
    },
    "confirm_fraud_selected": {
        "en": "Are you sure you want to mark {n} selected orders as fraud?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการระบุว่าคำสั่งซื้อที่เลือก {n} รายการเป็นการทุจริต?",
    },
    "confirm_approve_btn": {"en": "Confirm Approval", "th": "ยืนยันการอนุมัติ"},
    "confirm_approve_all_btn": {"en": "Confirm Approve All", "th": "ยืนยันอนุมัติทั้งหมด"},
    "confirm_blacklist_btn": {"en": "Confirm Blacklist", "th": "ยืนยันขึ้นบัญชีดำ"},
    "no_backlog_message": {
        "en": "**No backlog orders at the moment.**",
        "th": "**ขณะนี้ไม่มีคำสั่งซื้อค้างตรวจสอบ**",
    },
    "success_order_approved": {
        "en": "Order {order_id} approved.",
        "th": "อนุมัติคำสั่งซื้อ {order_id} แล้ว",
    },
    "success_order_rejected": {
        "en": "Order {order_id} rejected.",
        "th": "ปฏิเสธคำสั่งซื้อ {order_id} แล้ว",
    },
    "success_order_fraud": {
        "en": "Order {order_id} marked as fraud.",
        "th": "ระบุว่าคำสั่งซื้อ {order_id} เป็นการทุจริตแล้ว",
    },
    "success_orders_approved": {
        "en": "{n} orders approved.",
        "th": "อนุมัติแล้ว {n} รายการ",
    },
    "success_orders_processed": {
        "en": "{n} orders processed.",
        "th": "ดำเนินการแล้ว {n} รายการ",
    },
    "confirm_blacklist_ip": {
        "en": "Are you sure you want to blacklist IP **{value}**?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการขึ้นบัญชีดำ IP **{value}**?",
    },
    "confirm_blacklist_phone": {
        "en": "Are you sure you want to blacklist phone **{value}**?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการขึ้นบัญชีดำเบอร์ **{value}**?",
    },
    "confirm_blacklist_email": {
        "en": "Are you sure you want to blacklist email **{value}**?",
        "th": "คุณแน่ใจหรือไม่ว่าต้องการขึ้นบัญชีดำอีเมล **{value}**?",
    },
    "blacklist_ip_warning": {
        "en": "This will block future transactions from this IP address.",
        "th": "การดำเนินการนี้จะบล็อกธุรกรรมในอนาคตจากที่อยู่ IP นี้",
    },
    "blacklist_phone_warning": {
        "en": "This will block future transactions associated with this phone number.",
        "th": "การดำเนินการนี้จะบล็อกธุรกรรมในอนาคตที่เกี่ยวข้องกับเบอร์โทรศัพท์นี้",
    },
    "blacklist_email_warning": {
        "en": "This will block future transactions associated with this email address.",
        "th": "การดำเนินการนี้จะบล็อกธุรกรรมในอนาคตที่เกี่ยวข้องกับอีเมลนี้",
    },
    "success_ip_blacklisted": {
        "en": "IP {value} has been blacklisted.",
        "th": "ขึ้นบัญชีดำ IP {value} แล้ว",
    },
    "success_phone_blacklisted": {
        "en": "Phone {value} has been blacklisted.",
        "th": "ขึ้นบัญชีดำเบอร์ {value} แล้ว",
    },
    "success_email_blacklisted": {
        "en": "Email {value} has been blacklisted.",
        "th": "ขึ้นบัญชีดำอีเมล {value} แล้ว",
    },
    "spinner_approving": {"en": "Processing approval...", "th": "กำลังอนุมัติ..."},
    "spinner_approving_n": {
        "en": "Approving {n} orders...",
        "th": "กำลังอนุมัติ {n} รายการ...",
    },
    "spinner_processing_n": {
        "en": "Processing {n} orders...",
        "th": "กำลังดำเนินการ {n} รายการ...",
    },
    "spinner_blacklist_ip": {
        "en": "Applying blacklist to IP...",
        "th": "กำลังขึ้นบัญชีดำ IP...",
    },
    "spinner_blacklist_phone": {
        "en": "Applying blacklist to phone number...",
        "th": "กำลังขึ้นบัญชีดำเบอร์โทรศัพท์...",
    },
    "spinner_blacklist_email": {
        "en": "Applying blacklist to email...",
        "th": "กำลังขึ้นบัญชีดำอีเมล...",
    },
    "err_invalid_http_method": {
        "en": "Invalid HTTP method: {method}",
        "th": "เมธอด HTTP ไม่ถูกต้อง: {method}",
    },
    "err_api_timeout": {
        "en": "API connection failed or timed out: {exc}",
        "th": "เชื่อมต่อ API ไม่สำเร็จหรือหมดเวลา: {exc}",
    },

    # --- Admin panel ---
    "admin_control_panel": {
        "en": "⚙️ Admin Control Panel",
        "th": "⚙️ แผงควบคุมผู้ดูแลระบบ",
    },
    "logged_in_as_role": {
        "en": "Logged in as: **{name}** ({role})",
        "th": "เข้าสู่ระบบในชื่อ: **{name}** ({role})",
    },
    "tab_review_queue": {
        "en": "⚖️ Review Queue (Override)",
        "th": "⚖️ คิวตรวจสอบ (แทนที่การตัดสินใจ)",
    },
    "tab_blacklists": {"en": "🛡️ Entity Blacklists", "th": "🛡️ บัญชีดำ"},
    "tab_permissions": {
        "en": "🔐 Analyst Permissions",
        "th": "🔐 สิทธิ์การเข้าถึงของนักวิเคราะห์",
    },
    "tab_user_mgmt": {"en": "👥 User Management", "th": "👥 การจัดการผู้ใช้"},
    "tab_analytics": {"en": "📊 Analytics", "th": "📊 การวิเคราะห์ข้อมูล"},
    "tab_rule_mgmt": {"en": "📋 Rule Management", "th": "📋 การจัดการกฎ"},
    "user_management": {
        "en": "### 👥 User Management",
        "th": "### 👥 การจัดการผู้ใช้",
    },
    "user_mgmt_caption": {
        "en": "Create new analyst profiles and monitor current team performance.",
        "th": "สร้างโปรไฟล์นักวิเคราะห์ใหม่และติดตามผลการทำงานของทีม",
    },
    "create_analyst_profile": {
        "en": "➕ Create New Analyst Profile",
        "th": "➕ สร้างโปรไฟล์นักวิเคราะห์ใหม่",
    },
    "analyst_id": {"en": "Analyst ID", "th": "รหัสนักวิเคราะห์"},
    "employee_name": {"en": "Employee Name", "th": "ชื่อพนักงาน"},
    "role": {"en": "Role", "th": "ตำแหน่ง"},
    "confirm_create_analyst_chk": {
        "en": "⚠️ I confirm that I want to create this analyst profile.",
        "th": "⚠️ ฉันยืนยันว่าต้องการสร้างโปรไฟล์นักวิเคราะห์นี้",
    },
    "create_analyst": {"en": "Create Analyst", "th": "สร้างนักวิเคราะห์"},
    "err_all_fields_required": {
        "en": "All fields are required.",
        "th": "กรุณากรอกข้อมูลให้ครบทุกช่อง",
    },
    "warn_confirm_checkbox": {
        "en": "Please check the confirmation box to proceed with creation.",
        "th": "กรุณาทำเครื่องหมายยืนยันเพื่อดำเนินการสร้าง",
    },
    "analyst_performance": {
        "en": "#### 📈 Analyst Performance",
        "th": "#### 📈 ผลการปฏิบัติงานของนักวิเคราะห์",
    },
    "entity_blacklist_mgmt": {
        "en": "### 🛡️ Entity Blacklist Management",
        "th": "### 🛡️ การจัดการบัญชีดำ",
    },
    "blacklist_caption": {
        "en": "Check, blacklist, or whitelist IP addresses, phone numbers, and emails.",
        "th": "ตรวจสอบ ขึ้นบัญชีดำ หรือนำออกจากบัญชีดำ สำหรับ IP เบอร์โทรศัพท์ และอีเมล",
    },
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
    "entity_email": {"en": "📧 Email", "th": "📧 อีเมล"},
    "analyst_page_permissions": {
        "en": "### 🔐 Analyst Page Permissions",
        "th": "### 🔐 สิทธิ์การเข้าถึงหน้าของนักวิเคราะห์",
    },
    "permissions_caption": {
        "en": "Grant or revoke access to each page. Admins always have full access and aren't listed here.",
        "th": "ให้หรือเพิกถอนสิทธิ์การเข้าถึงแต่ละหน้า ผู้ดูแลระบบมีสิทธิ์เต็มเสมอและจะไม่แสดงในรายการนี้",
    },
    "no_non_admin": {
        "en": "No non-admin analysts exist yet.",
        "th": "ยังไม่มีนักวิเคราะห์ที่ไม่ใช่ผู้ดูแลระบบ",
    },
    "select_analyst_edit": {
        "en": "Select Analyst to Edit",
        "th": "เลือกนักวิเคราะห์ที่ต้องการแก้ไข",
    },
    "save_permissions": {"en": "Save Permissions", "th": "บันทึกสิทธิ์การเข้าถึง"},
    "warn_save_perms": {
        "en": "Please check the confirmation box to save these permissions.",
        "th": "กรุณาทำเครื่องหมายยืนยันเพื่อบันทึกสิทธิ์การเข้าถึงนี้",
    },
    "confirm_save_perms_chk": {
        "en": "⚠️ I confirm these permission changes.",
        "th": "⚠️ ฉันยืนยันการเปลี่ยนแปลงสิทธิ์เหล่านี้",
    },
    "recent_orders": {"en": "### Recent Orders", "th": "### คำสั่งซื้อล่าสุด"},
    "total_orders": {"en": "Total Orders", "th": "คำสั่งซื้อทั้งหมด"},
    "total_fraud_orders": {
        "en": "Total Fraud Orders",
        "th": "คำสั่งซื้อที่เป็นการทุจริตทั้งหมด",
    },
    "fraud_rate": {"en": "Fraud Rate", "th": "อัตราการทุจริต"},
    "no_orders_this_month": {
        "en": "No orders placed yet this month.",
        "th": "ยังไม่มีคำสั่งซื้อในเดือนนี้",
    },
    "recent_orders_live": {"en": "#### 🕒 Recent Orders", "th": "#### 🕒 คำสั่งซื้อล่าสุด"},
    "recent_orders_caption": {
        "en": "Live view of the latest system transactions.",
        "th": "มุมมองแบบเรียลไทม์ของธุรกรรมล่าสุดในระบบ",
    },
    "no_recent_orders": {
        "en": "No recent orders found.",
        "th": "ไม่พบคำสั่งซื้อล่าสุด",
    },
    "rule_trigger_stats": {
        "en": "### 📋 Rule Trigger Statistics",
        "th": "### 📋 สถิติการทำงานของกฎ",
    },
    "rule_stats_caption": {
        "en": "Visibility into which automated fraud rules are firing most frequently.",
        "th": "ภาพรวมของกฎตรวจจับการทุจริตอัตโนมัติที่ทำงานบ่อยที่สุด",
    },
    "no_rule_data": {
        "en": "No rule trigger data available to display.",
        "th": "ไม่มีข้อมูลการทำงานของกฎให้แสดง",
    },
    "rule_config_mgmt": {
        "en": "### ⚙️ Rule Configuration Management",
        "th": "### ⚙️ การจัดการค่ากำหนดของกฎ",
    },
    "rule_config_caption": {
        "en": "Adjust actions, thresholds, and time windows for e-commerce fraud detection rules.",
        "th": "ปรับการดำเนินการ เกณฑ์ และช่วงเวลาสำหรับกฎตรวจจับการทุจริตในอีคอมเมิร์ซ",
    },
    "no_rules_found": {
        "en": "No rules found in the database.",
        "th": "ไม่พบกฎในฐานข้อมูล",
    },
    "select_rule_modify": {
        "en": "Select Rule to Modify",
        "th": "เลือกกฎที่ต้องการแก้ไข",
    },
    "configuration_parameters": {
        "en": "Configuration Parameters",
        "th": "พารามิเตอร์การกำหนดค่า",
    },
    "action_locked_hold": {
        "en": "🔒 **Action is locked to HOLD** for the P2 iPhone 16 Rule.",
        "th": "🔒 **การดำเนินการถูกล็อกไว้ที่ HOLD** สำหรับกฎ P2 iPhone 16",
    },
    "action_locked_rejected": {
        "en": "🔒 **Action is strictly locked to REJECTED** for Blacklist entities.",
        "th": "🔒 **การดำเนินการถูกล็อกไว้ที่ REJECTED** สำหรับรายการในบัญชีดำ",
    },
    "rule_action": {"en": "Rule Action", "th": "การดำเนินการของกฎ"},
    "threshold": {"en": "Threshold", "th": "เกณฑ์"},
    "threshold_na": {"en": "Threshold N/A", "th": "ไม่มีเกณฑ์"},
    "time_interval": {"en": "Time Interval", "th": "ช่วงเวลา"},
    "interval_na": {"en": "Interval N/A", "th": "ไม่มีช่วงเวลา"},
    "interval_disabled_r001": {
        "en": "Time Interval is disabled for R001 — use Delay Minutes.",
        "th": "ปิดการใช้ช่วงเวลาสำหรับ R001 — ใช้ค่านาทีที่หน่วงแทน",
    },
    "delay_minutes": {"en": "Delay Minutes", "th": "นาทีที่หน่วง"},
    "delay_minutes_help": {
        "en": "Review timeout before automatic approval (read by fraud engine from rule_master).",
        "th": "ระยะเวลารอตรวจสอบก่อนอนุมัติอัตโนมัติ (ระบบอ่านจากตาราง rule_master)",
    },
    "delay_na_blacklist": {
        "en": "Delay N/A for blacklist rules (immediate reject).",
        "th": "ไม่มีค่าหน่วงสำหรับกฎบัญชีดำ (ปฏิเสธทันที)",
    },
    "unit": {"en": "Unit", "th": "หน่วย"},
    "review_changes": {"en": "Review Changes", "th": "ตรวจสอบการเปลี่ยนแปลง"},
    "review_delay_label": {
        "en": "**Review Delay:** `{minutes}` minutes",
        "th": "**ระยะเวลารอตรวจสอบ:** `{minutes}` นาที",
    },
    "description_label": {"en": "**Description:**", "th": "**คำอธิบาย:**"},
    "detection_type_label": {
        "en": "**Detection Type:**",
        "th": "**ประเภทการตรวจจับ:**",
    },

    # --- Backlog management ---
    "backlog_section": {
        "en": "📥 Backlog Orders",
        "th": "📥 คำสั่งซื้อค้างตรวจสอบ",
    },
    "find_backlog_orders": {
        "en": "Find Backlog Orders",
        "th": "ค้นหาคำสั่งซื้อค้างตรวจสอบ",
    },
    "refresh_backlog": {"en": "Refresh", "th": "รีเฟรช"},
    "loading_backlog": {
        "en": "Detecting backlog orders...",
        "th": "กำลังตรวจหาคำสั่งซื้อค้างตรวจสอบ...",
    },
    "total_backlog": {"en": "Total Backlog", "th": "ค้างตรวจสอบทั้งหมด"},
    "oldest_backlog": {
        "en": "Oldest Backlog Order",
        "th": "คำสั่งซื้อค้างนานที่สุด",
    },
    "max_overdue": {"en": "Max Time Overdue", "th": "เกินเวลามากที่สุด"},
    "backlog_empty_hint": {
        "en": "Click **Find Backlog Orders** to scan for orders past their review delay.",
        "th": "คลิก **ค้นหาคำสั่งซื้อค้างตรวจสอบ** เพื่อสแกนรายการที่เกินเวลารอตรวจสอบ",
    },
    "backlog_bulk_actions": {
        "en": "⚡ Backlog Bulk Actions",
        "th": "⚡ การดำเนินการกลุ่มสำหรับค้างตรวจสอบ",
    },
    "approve_all_backlog": {
        "en": "✅ Approve All Backlog Orders",
        "th": "✅ อนุมัติค้างตรวจสอบทั้งหมด",
    },
    "reject_all_backlog": {
        "en": "🚫 Reject All Backlog Orders",
        "th": "🚫 ปฏิเสธค้างตรวจสอบทั้งหมด",
    },
    "fraud_all_backlog": {
        "en": "☠️ Mark All Backlog Orders as Fraud",
        "th": "☠️ ระบุค้างตรวจสอบทั้งหมดว่าเป็นการทุจริต",
    },
    "backlog_individual_actions": {
        "en": "⚖️ Backlog Order Actions",
        "th": "⚖️ การดำเนินการคำสั่งซื้อค้างตรวจสอบ",
    },
    "select_backlog_order": {
        "en": "Select a backlog order",
        "th": "เลือกคำสั่งซื้อค้างตรวจสอบ",
    },
    "remaining_review": {
        "en": "Remaining Review Time",
        "th": "เวลาตรวจสอบที่เหลือ",
    },
    "time_overdue": {"en": "Time Overdue", "th": "เวลาที่เกินกำหนด"},
    "auto_approved_info": {
        "en": "{n} order(s) auto-approved after exceeding their configured review delay.",
        "th": "อนุมัติอัตโนมัติ {n} รายการ เนื่องจากเกินระยะเวลารอตรวจสอบที่กำหนด",
    },

    # --- Table / column labels ---
    "col_select": {"en": "Select", "th": "เลือก"},
    "col_order_id": {"en": "Order ID", "th": "หมายเลขคำสั่งซื้อ"},
    "col_customer": {"en": "Customer", "th": "ลูกค้า"},
    "col_product": {"en": "Product", "th": "สินค้า"},
    "col_amount": {"en": "Amount", "th": "จำนวนเงิน"},
    "col_status": {"en": "Status", "th": "สถานะ"},
    "col_delay_min": {"en": "Delay (min)", "th": "หน่วง (นาที)"},
    "col_delay_minutes": {"en": "Delay Minutes", "th": "นาทีที่หน่วง"},
    "col_remaining": {"en": "Remaining Review", "th": "เวลาที่เหลือ"},
    "col_overdue": {"en": "Overdue", "th": "เกินเวลา"},
    "col_flag": {"en": "Flag", "th": "สถานะพิเศษ"},
    "col_placed_at": {"en": "Placed At", "th": "เวลาที่สั่งซื้อ"},
    "col_rule_name": {"en": "Rule Name", "th": "ชื่อกฎ"},
    "col_tagged_at": {"en": "Tagged Timestamp", "th": "เวลาที่ถูกตั้งค่าสถานะ"},
    "col_time_overdue": {"en": "Time Overdue", "th": "เวลาที่เกิน"},

    # --- Sidebar navigation ---
    "nav_title": {"en": "Navigation", "th": "เมนูนำทาง"},
    "nav_fraud_dashboard": {
        "en": "Fraud Analyst Dashboard",
        "th": "แดชบอร์ดนักวิเคราะห์การทุจริต",
    },
    "nav_admin_panel": {
        "en": "Admin Control Panel",
        "th": "แผงควบคุมผู้ดูแลระบบ",
    },
    "nav_power_bi": {
        "en": "Analytics Dashboards",
        "th": "แดชบอร์ดการวิเคราะห์ข้อมูล",
    },
    "nav_ai_chatbot": {"en": "AI Chatbot", "th": "แชทบอตเอไอ"},
    "chatbot_title": {
        "en": "Metro Cart Analytics Chatbot",
        "th": "แชทบอตวิเคราะห์เมโทรคาร์ท",
    },
    "chatbot_subtitle": {
        "en": "Ask about orders, fraud, backlog holds, revenue, customers, products, devices, and rules.",
        "th": "สอบถามเกี่ยวกับคำสั่งซื้อ การทุจริต คิวค้างตรวจสอบ รายได้ ลูกค้า สินค้า อุปกรณ์ และกฎ",
    },
    "chatbot_topics": {
        "en": "Orders & sales · Revenue · Fraud & backlog · Customers · Products · Devices · Rules · Geography",
        "th": "คำสั่งซื้อและยอดขาย · รายได้ · การทุจริตและคิวค้าง · ลูกค้า · สินค้า · อุปกรณ์ · กฎ · พื้นที่",
    },
    "chatbot_examples_title": {"en": "Example questions", "th": "ตัวอย่างคำถาม"},
    "chatbot_example_1": {"en": "Total fraudulent orders", "th": "จำนวนคำสั่งซื้อทุจริตรวม"},
    "chatbot_example_2": {"en": "Fraud rate by state", "th": "อัตราการทุจริตตามจังหวัด"},
    "chatbot_example_3": {"en": "Top 10 customers by spending", "th": "ลูกค้าที่ใช้จ่ายสูงสุด 10 อันดับ"},
    "chatbot_example_4": {"en": "Orders currently on hold or pending review", "th": "คำสั่งซื้อที่ถูกพักหรือรอตรวจสอบ"},
    "chatbot_example_5": {"en": "Revenue by product category", "th": "รายได้ตามหมวดสินค้า"},
    "chatbot_input_placeholder": {
        "en": "Ask a Metro Cart analytics question…",
        "th": "ถามคำถามวิเคราะห์เมโทรคาร์ท…",
    },
    "chatbot_clear_history": {"en": "Clear chat history", "th": "ล้างประวัติแชท"},
    "chatbot_groq_connected": {"en": "Groq connected", "th": "เชื่อมต่อ Groq แล้ว"},
    "chatbot_groq_missing": {
        "en": "Groq API key missing — set GROQ_API_KEY in .env",
        "th": "ไม่มีคีย์ Groq — ตั้งค่า GROQ_API_KEY ในไฟล์ .env",
    },
    "chatbot_viz_title": {"en": "Visualization", "th": "แผนภูมิ"},
    "chatbot_insights": {"en": "Key insights", "th": "ข้อมูลเชิงลึกสำคัญ"},
    "chatbot_strategies": {"en": "Growth strategies", "th": "กลยุทธ์การเติบโต"},
    "chatbot_advice": {"en": "Business advice", "th": "คำแนะนำทางธุรกิจ"},
    "chatbot_suggested": {"en": "Suggested questions", "th": "คำถามที่แนะนำ"},
    "chatbot_view_results": {"en": "View result data", "th": "ดูข้อมูลผลลัพธ์"},
    "chatbot_connection": {"en": "Connection", "th": "การเชื่อมต่อ"},
    "no_page_access": {
        "en": "You don't have access to any pages yet. Contact an Admin to request access.",
        "th": "คุณยังไม่มีสิทธิ์เข้าถึงหน้าใด กรุณาติดต่อผู้ดูแลระบบเพื่อขอสิทธิ์",
    },

    # --- Currency-formatted labels ---
    "amount": {"en": "Amount", "th": "จำนวนเงิน"},
    "total_amount": {"en": "Total Amount", "th": "ยอดรวม"},
}


def _validate_catalog() -> None:
    """Ensure every entry has both en and th (dev-time safety net)."""
    for key, entry in TRANSLATIONS.items():
        if "en" not in entry or "th" not in entry:
            raise ValueError(f"i18n key '{key}' must define both 'en' and 'th'")


_validate_catalog()


def _lang() -> str:
    lang = st.session_state.get(LANG_KEY, DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """Translate a UI string key into the active language.

    Falls back: active lang → English → raw key.
    Supports ``str.format(**kwargs)`` substitution.
    """
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_lang()) or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def format_duration_minutes(minutes) -> str:
    """Localized remaining/overdue duration display."""
    try:
        m = float(minutes)
    except (TypeError, ValueError):
        return "—"
    if m < 1:
        secs = max(0, int(round(m * 60)))
        return t("seconds_unit", n=secs) if secs > 0 else t("minutes_unit", n=0)
    return t("minutes_unit", n=f"{m:.0f}")


def cur_sym() -> str:
    """Currency symbol shown in the UI. Always Thai Baht (฿)."""
    return "฿"


def language_toggle() -> None:
    """Renders a compact EN / Thai language switch."""
    if LANG_KEY not in st.session_state:
        st.session_state[LANG_KEY] = DEFAULT_LANG

    cols = st.columns([0.78, 0.22])
    with cols[1]:
        choice = st.selectbox(
            t("language"),
            options=list(SUPPORTED_LANGS),
            format_func=lambda code: "English" if code == "en" else "ไทย (Thai)",
            index=list(SUPPORTED_LANGS).index(_lang()),
            key="_lang_selector",
            label_visibility="collapsed",
        )
    if choice != st.session_state[LANG_KEY]:
        st.session_state[LANG_KEY] = choice
        st.rerun()
