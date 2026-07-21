"""Fraud Analyst Dashboard: queue of ON_HOLD / PENDING_REVIEW orders."""
import sys
from datetime import datetime
from pathlib import Path
import requests
import time

from config import API_BASE_URL, API_TIMEOUT
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from database.connection import get_cursor
from fraud_engine.auto_approval import sync_expired_holds
from utils.queries import (
    get_active_blacklist_entry, 
    get_active_phone_blacklist_entry, 
    get_active_email_blacklist_entry,
    get_order_detail, 
    get_queue_orders
)
from utils.pii import display_pii
from ui.i18n import t, cur_sym

STATUS_ICONS = {
    "ON_HOLD": "⏳",
    "PENDING_REVIEW": "🕵️",
    "APPROVED": "✅",
    "REJECTED": "🚫",
}

def _build_api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
def _send_api_request(method: str, path: str, **kwargs):
    """Centralized request helper with timeout and error handling.

    Returns the `requests.Response` on success, or `None` on failure.
    """
    url = _build_api_url(path)
    try:
        func = getattr(requests, method.lower())
    except AttributeError:
        st.error(f"Invalid HTTP method: {method}")
        return None

    try:
        resp = func(url, timeout=API_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        st.error(f"API connection failed or timed out: {exc}")
        return None

    if not resp.ok:
        # Attempt to show a helpful error body
        body = resp.text if resp.text else f"HTTP {resp.status_code}"
        st.error(body)
    return resp


def inject_dashboard_css():
    st.markdown("""
        <style>
        /* Use the global variables defined by ui/style.py so light/dark themes stay consistent */
        .dashboard-card {
            background-color: var(--card-bg);
            color: var(--text);
            border-radius: 8px;
            padding: 20px;
            box-shadow: none !important;
            border: 1px solid var(--border);
            margin-bottom: 20px;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            display: inline-block;
            text-shadow: none;
        }
        .status-PENDING_REVIEW { background-color: #f59e0b; color: #0f172a; border: 1px solid rgba(217,119,6,0.15); }
        .status-ON_HOLD { background-color: #3b82f6; color: #ffffff; border: 1px solid rgba(37,99,235,0.12); }
        .status-APPROVED { background-color: #10b981; color: #ffffff; border: 1px solid rgba(5,150,105,0.12); }
        .status-REJECTED { background-color: #ef4444; color: #ffffff; border: 1px solid rgba(220,38,38,0.12); }
        </style>
    """, unsafe_allow_html=True)


# --- CACHED DATABASE SYNC ---

@st.cache_data(ttl=300)
def sync_database_holds():
    """Caches the database synchronization to prevent it from firing on every UI rerun.
    TTL of 300 seconds means this background cleanup only runs once every 5 minutes."""
    with get_cursor(commit=True) as (conn, cur):
        return sync_expired_holds(conn, cur)


# --- DIALOG FUNCTIONS ---

@st.dialog("Confirm Approval")
def confirm_approve_order(analyst_id, order_id, comments):
    st.write(f"Are you sure you want to **approve** order `{order_id}`?")
    if st.button("Confirm Approval", type="primary", use_container_width=True):
        with st.spinner("Processing approval (completing sale)..."):
            response = _send_api_request(
                "put",
                "approve-order",
                json={
                    "approved_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments,
                    "order_id": order_id,
                },
            )

        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"Order {order_id} approved.")
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Rejection")
def confirm_reject_order(analyst_id, order_id, comments, is_fraud=False):
    action_label = "reject and mark as **fraud**" if is_fraud else "reject"
    st.write(f"Are you sure you want to {action_label} order `{order_id}`?")

    if st.button("Confirm Rejection", type="primary", use_container_width=True):
        with st.spinner("Processing rejection (cancelling order)..."):
            response = _send_api_request(
                "put",
                "reject-order",
                json={
                    "is_fraud": is_fraud,
                    "rejected_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments,
                    "order_id": order_id,
                },
            )

        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"Order {order_id} rejected" + (" and marked as fraud." if is_fraud else "."))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Batch Approval")
def confirm_batch_approve(analyst_id, order_ids, comments):
    st.write(f"Are you sure you want to **approve** {len(order_ids)} orders?")
    if st.button("Confirm Approve All", type="primary", use_container_width=True):
        with st.spinner(f"Approving {len(order_ids)} orders (completing sales)..."):
            response = _send_api_request(
                "put",
                "batch-approve",
                json={
                    "approved_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments,
                    "order_ids": order_ids,
                },
            )

        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"{len(order_ids)} orders approved.")
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Batch Rejection")
def confirm_batch_reject(analyst_id, order_ids, comments, is_fraud=False):
    action_label = "reject and mark as **fraud**" if is_fraud else "reject"
    st.write(f"Are you sure you want to {action_label} {len(order_ids)} orders?")

    if st.button("Confirm Reject All", type="primary", use_container_width=True):
        with st.spinner(f"Rejecting {len(order_ids)} orders (cancelling orders)..."):
            response = _send_api_request(
                "put",
                "batch-reject",
                json={
                    "is_fraud": is_fraud,
                    "rejected_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments,
                    "order_ids": order_ids,
                },
            )

        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"{len(order_ids)} orders rejected" + (" and marked as fraud." if is_fraud else "."))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm IP Blacklist")
def confirm_blacklist_ip(analyst_id, ip_address, reason):
    st.write(f"Are you sure you want to blacklist IP **{ip_address}**?")
    st.error("This will block future transactions from this IP address.")
    if st.button("Confirm Blacklist", type="primary", use_container_width=True):
        with st.spinner("Applying blacklist to IP..."):
            response = _send_api_request(
                "post",
                "blacklist-ip",
                json={
                    "ip_address": ip_address,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"IP {ip_address} has been blacklisted.")
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Phone Blacklist")
def confirm_blacklist_phone(analyst_id, phone_number, reason):
    st.write(f"Are you sure you want to blacklist phone **{phone_number}**?")
    st.error("This will block future transactions associated with this phone number.")
    if st.button("Confirm Blacklist", type="primary", use_container_width=True):
        with st.spinner("Applying blacklist to phone number..."):
            response = _send_api_request(
                "post",
                "blacklist-phone",
                json={
                    "phone_number": phone_number,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"Phone {phone_number} has been blacklisted.")
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Email Blacklist")
def confirm_blacklist_email(analyst_id, email, reason):
    st.write(f"Are you sure you want to blacklist email **{email}**?")
    st.error("This will block future transactions associated with this email address.")
    if st.button("Confirm Blacklist", type="primary", use_container_width=True):
        with st.spinner("Applying blacklist to email..."):
            response = _send_api_request(
                "post",
                "blacklist-email",
                json={
                    "email": email,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response:
            return
        if response.status_code != 200:
            return
        st.success(f"Email {email} has been blacklisted.")
        time.sleep(1)
        st.rerun()


# --- MAIN DASHBOARD LOGIC ---

def render_queue_and_review(analyst: dict):
    """Shared queue + review UI, reused by both the Analyst Dashboard and Admin overrides."""
    inject_dashboard_css()
    
    # Run the cached synchronization task
    auto_approved = sync_database_holds()
    if auto_approved:
        st.info(f"{auto_approved} order(s) auto-approved in the recent background sync after their 180-minute hold window elapsed.")

    with get_cursor() as (conn, cur):
        queue_df = get_queue_orders(cur)

    # --- TOP LEVEL METRICS ---
    st.markdown(f"#### {t('queue_overview')}")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    total_pending = len(queue_df[queue_df['order_status'] == 'PENDING_REVIEW']) if not queue_df.empty else 0
    total_hold = len(queue_df[queue_df['order_status'] == 'ON_HOLD']) if not queue_df.empty else 0
    
    with metric_col1:
        st.metric(t("total_in_queue"), len(queue_df))
    with metric_col2:
        st.metric(t("pending_review"), total_pending)
    with metric_col3:
        st.metric(t("on_hold"), total_hold)

    st.divider()

    st.markdown(f"#### {t('review_queue')}")
    if queue_df.empty:
        st.success(t("queue_clear"))
        return

    # --- BATCH SELECTION & DATA EDITOR ---
    select_all = st.checkbox(t("select_all_queue"))
    queue_df.insert(0, "Select", select_all)

    edited_df = st.data_editor(
        queue_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "order_id": "Order ID",
            "customer_name": "Customer",
            "product_name": "Product",
            "amount": st.column_config.NumberColumn("Amount", format=f"{cur_sym()} %.2f"),
            "order_status": "Status",
            "order_timestamp": st.column_config.DatetimeColumn("Placed At", format="D MMM YYYY, h:mm a"),
        },
        disabled=["order_id", "customer_name", "product_name", "amount", "order_status", "order_timestamp"]
    )

    selected_order_ids = edited_df[edited_df["Select"]]["order_id"].tolist()

    # --- BATCH ACTIONS PANEL ---
    if selected_order_ids:
        st.markdown(f"#### {t('batch_actions', n=len(selected_order_ids))}")
        with st.container(border=True):
            batch_comments = st.text_area(t("batch_comments"), key="batch_comments")
            
            col_batch_app, col_batch_rej, col_batch_fraud = st.columns(3)
            with col_batch_app:
                if st.button(t("approve_selected"), type="primary", use_container_width=True):
                    if not batch_comments.strip():
                        st.warning(t("warn_comment_approve"))
                    else:
                        confirm_batch_approve(analyst["analyst_id"], selected_order_ids, batch_comments)
            with col_batch_rej:
                if st.button(t("reject_selected"), use_container_width=True):
                    if not batch_comments.strip():
                        st.warning(t("warn_comment_reject"))
                    else:
                        confirm_batch_reject(analyst["analyst_id"], selected_order_ids, batch_comments, is_fraud=False)
            with col_batch_fraud:
                if st.button(t("reject_selected_fraud"), use_container_width=True):
                    if not batch_comments.strip():
                        st.warning(t("warn_comment_reject"))
                    else:
                        confirm_batch_reject(analyst["analyst_id"], selected_order_ids, batch_comments, is_fraud=True)
        
    st.divider()
    
    # --- SINGLE ORDER INVESTIGATION ---
    st.markdown(f"#### {t('single_order_investigation')}")
    order_id = st.selectbox(t("select_order_review"), queue_df["order_id"].tolist())
    if not order_id:
        return

    with get_cursor() as (conn, cur):
        order = get_order_detail(cur, order_id)
        # Fetch blacklist statuses for IP, Phone, and Email
        blacklist_entry = get_active_blacklist_entry(cur, order["ip_address"]) if order else None
        phone_blacklist_entry = get_active_phone_blacklist_entry(cur, order["phone_number"]) if order else None
        email_blacklist_entry = get_active_email_blacklist_entry(cur, order["email"]) if order else None

    if not order:
        st.warning(t("order_not_found"))
        return

    # --- ORDER DETAIL CARD ---
    status_class = f"status-{order['order_status']}"
    
    st.markdown(f"""
        <div class="dashboard-card">
            <h3 style="margin-top: 0;">Order {order['order_id']} 
            <span class="status-badge {status_class}">{STATUS_ICONS.get(order['order_status'], '')} {order['order_status']}</span>
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(t("customer_details"))
        st.write(f"**Name:** {order['customer_name']} ({order['user_id']})")
        st.write(
            f"**Email:** {display_pii(order['email'], field='email', analyst=analyst)}"
            + (" 🚫 *(blacklisted)*" if email_blacklist_entry else "")
        )
        st.write(
            f"**Phone:** {display_pii(order['phone_number'], field='phone', analyst=analyst)}"
            + (" 🚫 *(blacklisted)*" if phone_blacklist_entry else "")
        )
        st.write(f"**Address:** {display_pii(order['address'], field='address', analyst=analyst)}") 
    with col2:
        st.markdown(t("order_details"))
        st.write(f"**Product:** {order['product_name']} x{order['quantity']}")
        st.write(f"**Amount:** {cur_sym()}{order['amount']:,.2f}")
        st.write(
            f"**IP Address:** {display_pii(order['ip_address'], field='ip', analyst=analyst)}"
            + (" 🚫 *(blacklisted)*" if blacklist_entry else "")
        )
        st.write(f"**Device:** {order['device_id']}")
        st.write(f"**Placed At:** {order['order_timestamp']}")

    st.error(t("flagged_reason", reason=order['flagged_reason']))

    # Render blacklist action expanders
    _blacklist_ip_action(analyst, order["ip_address"], blacklist_entry, key_suffix=order_id)
    _blacklist_phone_action(analyst, order["phone_number"], phone_blacklist_entry, key_suffix=order_id)
    _blacklist_email_action(analyst, order["email"], email_blacklist_entry, key_suffix=order_id)

    # --- SINGLE ACTION DECISION ---
    st.markdown(f"#### {t('analyst_decision')}")
    with st.container(border=True):
        comments = st.text_area(t("review_comments"), key=f"comments_{order_id}")

        col_approve, col_reject, col_fraud = st.columns(3)
        with col_approve:
            if st.button(t("approve_order"), type="primary", key=f"approve_{order_id}", use_container_width=True):
                if not comments.strip():
                    st.warning(t("warn_comment_approve"))
                else:
                    confirm_approve_order(analyst["analyst_id"], order_id, comments)
                
        with col_reject:
            if st.button(t("reject_order"), key=f"reject_{order_id}", use_container_width=True):
                if not comments.strip():
                    st.warning(t("warn_comment_reject"))
                else:
                    confirm_reject_order(analyst["analyst_id"], order_id, comments, is_fraud=False)

        with col_fraud:
            if st.button(t("reject_order_fraud"), key=f"reject_fraud_{order_id}", use_container_width=True):
                if not comments.strip():
                    st.warning(t("warn_comment_reject"))
                else:
                    confirm_reject_order(analyst["analyst_id"], order_id, comments, is_fraud=True)


def _blacklist_ip_action(analyst: dict, ip_address: str, blacklist_entry: dict, key_suffix: str):
    if blacklist_entry:
        st.info(
            f"🌐 IP **{ip_address}** is already blacklisted "
            f"(reason: {blacklist_entry['reason']}, by {blacklist_entry['blacklisted_by_name'] or blacklist_entry['blacklisted_by']} "
            f"on {blacklist_entry['blacklisted_at']})."
        )
        return

    with st.expander(f"🌐 Security Action: Blacklist IP {ip_address}"):
        with st.form(f"blacklist_ip_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_ip_reason_{key_suffix}")
            submitted = st.form_submit_button(t("lock_ip"))
            if submitted:
                if not reason.strip():
                    st.error("A reason is required to blacklist an IP address.")
                else:
                    confirm_blacklist_ip(analyst["analyst_id"], ip_address, reason.strip())

def _blacklist_phone_action(analyst: dict, phone_number: str, blacklist_entry: dict, key_suffix: str):
    if not phone_number:
        return
        
    if blacklist_entry:
        st.info(
            f"📱 Phone **{phone_number}** is already blacklisted "
            f"(reason: {blacklist_entry['reason']}, by {blacklist_entry['blacklisted_by_name'] or blacklist_entry['blacklisted_by']} "
            f"on {blacklist_entry['blacklisted_at']})."
        )
        return

    with st.expander(f"📱 Security Action: Blacklist Phone {phone_number}"):
        with st.form(f"blacklist_phone_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_phone_reason_{key_suffix}")
            submitted = st.form_submit_button(t("lock_phone"))
            if submitted:
                if not reason.strip():
                    st.error("A reason is required to blacklist a phone number.")
                else:
                    confirm_blacklist_phone(analyst["analyst_id"], phone_number, reason.strip())

def _blacklist_email_action(analyst: dict, email: str, blacklist_entry: dict, key_suffix: str):
    if not email:
        return
        
    if blacklist_entry:
        st.info(
            f"📧 Email **{email}** is already blacklisted "
            f"(reason: {blacklist_entry['reason']}, by {blacklist_entry['blacklisted_by_name'] or blacklist_entry['blacklisted_by']} "
            f"on {blacklist_entry['blacklisted_at']})."
        )
        return

    with st.expander(f"📧 Security Action: Blacklist Email {email}"):
        with st.form(f"blacklist_email_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_email_reason_{key_suffix}")
            submitted = st.form_submit_button(t("lock_email"))
            if submitted:
                if not reason.strip():
                    st.error("A reason is required to blacklist an email address.")
                else:
                    confirm_blacklist_email(analyst["analyst_id"], email, reason.strip())

def render():
    analyst = st.session_state.get("analyst")
    if not analyst:
        st.error(t("access_denied"))
        return

    st.header(t("fraud_analyst_workspace"))
    st.caption(t("logged_in_as", name=analyst['employee_name']))
    render_queue_and_review(analyst)