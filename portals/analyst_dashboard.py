"""Fraud Analyst Dashboard: queue of ON_HOLD / PENDING_REVIEW orders."""
import sys
from datetime import datetime
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from database.connection import get_cursor
from fraud_engine.auto_approval import sync_expired_holds
from utils.queries import get_active_blacklist_entry, get_order_detail, get_queue_orders

STATUS_ICONS = {
    "ON_HOLD": "⏳",
    "PENDING_REVIEW": "🕵️",
    "APPROVED": "✅",
    "REJECTED": "🚫",
}

def inject_dashboard_css():
    st.markdown("""
        <style>
        .dashboard-card {
            background-color: var(--background-color);
            color: var(--text-color);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border: 1px solid var(--secondary-background-color);
            margin-bottom: 20px;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            display: inline-block;
            text-shadow: 0 1px 1px rgba(0,0,0,0.2);
        }
        .status-PENDING_REVIEW { background-color: #f59e0b; color: #ffffff; border: 1px solid #d97706; }
        .status-ON_HOLD { background-color: #3b82f6; color: #ffffff; border: 1px solid #2563eb; }
        .status-APPROVED { background-color: #10b981; color: #ffffff; border: 1px solid #059669; }
        .status-REJECTED { background-color: #ef4444; color: #ffffff; border: 1px solid #dc2626; }
        </style>
    """, unsafe_allow_html=True)


# --- DIALOG FUNCTIONS ---

@st.dialog("Confirm Approval")
def confirm_approve_order(analyst_id, order_id, comments):
    st.write(f"Are you sure you want to **approve** order `{order_id}`?")
    if st.button("Yes, Approve", type="primary", use_container_width=True):
        response = requests.put(
            "http://127.0.0.1:8000/approve-order",
            json={
                "approved_at": str(datetime.now()),
                "reviewed_by": analyst_id,
                "review_comments": comments or None,
                "order_id": order_id,
            },
        )

        if response.status_code != 200:
            st.error(response.text)
            return
        st.success(f"Order {order_id} approved.")
        st.rerun()

@st.dialog("Confirm Rejection")
def confirm_reject_order(analyst_id, order_id, comments):
    st.write(f"Are you sure you want to **reject** order `{order_id}`?")
    st.warning("This will mark the order as fraudulent.")
    if st.button("Yes, Reject", type="primary", use_container_width=True):
        response = requests.put(
            "http://127.0.0.1:8000/reject-order",
            json={
                "rejected_at": str(datetime.now()),
                "reviewed_by": analyst_id,
                "review_comments": comments,
                "order_id": order_id,
            },
        )

        if response.status_code != 200:
            st.error(response.text)
            return
        st.success(f"Order {order_id} rejected.")
        st.rerun()
        
@st.dialog("Confirm Batch Approval")
def confirm_batch_approve(analyst_id, order_ids, comments):
    st.write(f"Are you sure you want to **approve** {len(order_ids)} orders?")
    if st.button("Yes, Approve All", type="primary", use_container_width=True):
        response = requests.put(
            "http://127.0.0.1:8000/batch-approve",
            json={
                "approved_at": str(datetime.now()),
                "reviewed_by": analyst_id,
                "review_comments": comments or None,
                "order_ids": order_ids,
            },
        )

        if response.status_code != 200:
            st.error(response.text)
            return
        st.success(f"{len(order_ids)} orders approved.")
        st.rerun()

@st.dialog("Confirm Batch Rejection")
def confirm_batch_reject(analyst_id, order_ids, comments):
    st.write(f"Are you sure you want to **reject** {len(order_ids)} orders?")
    st.warning("This will mark these orders as fraudulent.")
    if st.button("Yes, Reject All", type="primary", use_container_width=True):
        response = requests.put(
            "http://127.0.0.1:8000/batch-reject",
            json={
                "rejected_at": str(datetime.now()),
                "reviewed_by": analyst_id,
                "review_comments": comments,
                "order_ids": order_ids,
            },
        )

        if response.status_code != 200:
            st.error(response.text)
            return
        st.success(f"{len(order_ids)} orders rejected.")
        st.rerun()

@st.dialog("Confirm IP Blacklist")
def confirm_blacklist_ip(analyst_id, ip_address, reason):
    st.write(f"Are you sure you want to blacklist IP **{ip_address}**?")
    st.error("This will block future transactions from this IP address.")
    if st.button("Yes, Blacklist IP", type="primary", use_container_width=True):
        response = requests.post(
            "http://127.0.0.1:8000/blacklist-ip",
            json={
                "ip_address": ip_address,
                "reason": reason,
                "blacklisted_by": analyst_id,
            },
        )

        if response.status_code != 200:
            st.error(response.text)
            return
        st.success(f"IP {ip_address} has been blacklisted.")
        st.rerun()

# --- MAIN DASHBOARD LOGIC ---

def render_queue_and_review(analyst: dict):
    """Shared queue + review UI, reused by both the Analyst Dashboard and Admin overrides."""
    inject_dashboard_css()
    
    with get_cursor(commit=True) as (conn, cur):
        auto_approved = sync_expired_holds(conn, cur)
    if auto_approved:
        st.info(f"{auto_approved} order(s) auto-approved after their 180-minute hold window elapsed.")

    with get_cursor() as (conn, cur):
        queue_df = get_queue_orders(cur)

    # --- TOP LEVEL METRICS ---
    st.markdown("#### 📊 Queue Overview")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    total_pending = len(queue_df[queue_df['order_status'] == 'PENDING_REVIEW']) if not queue_df.empty else 0
    total_hold = len(queue_df[queue_df['order_status'] == 'ON_HOLD']) if not queue_df.empty else 0
    
    with metric_col1:
        st.metric("Total in Queue", len(queue_df))
    with metric_col2:
        st.metric("Pending Review", total_pending)
    with metric_col3:
        st.metric("On Hold", total_hold)

    st.divider()

    st.markdown("#### 📋 Review Queue")
    if queue_df.empty:
        st.success("✅ Queue is clear. No orders pending review.")
        return

    # --- BATCH SELECTION & DATA EDITOR ---
    select_all = st.checkbox("Select All Orders in Queue")
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
            "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
            "order_status": "Status",
            "order_timestamp": st.column_config.DatetimeColumn("Placed At", format="D MMM YYYY, h:mm a"),
        },
        disabled=["order_id", "customer_name", "product_name", "amount", "order_status", "order_timestamp"]
    )

    selected_order_ids = edited_df[edited_df["Select"]]["order_id"].tolist()

    # --- BATCH ACTIONS PANEL ---
    if selected_order_ids:
        st.markdown(f"#### ⚡ Batch Actions ({len(selected_order_ids)} selected)")
        with st.container(border=True):
            batch_comments = st.text_area("Batch Review Comments (applied to all selected orders, required for rejection)", key="batch_comments")
            
            col_batch_app, col_batch_rej = st.columns(2)
            with col_batch_app:
                if st.button("✅ Approve Selected", type="primary", use_container_width=True):
                    confirm_batch_approve(analyst["analyst_id"], selected_order_ids, batch_comments)
            with col_batch_rej:
                if st.button("🚫 Reject Selected", use_container_width=True):
                    if not batch_comments.strip():
                        st.warning("Please provide a reason in the comments before rejecting.")
                    else:
                        confirm_batch_reject(analyst["analyst_id"], selected_order_ids, batch_comments)
        
    st.divider()
    
    # --- SINGLE ORDER INVESTIGATION ---
    st.markdown("#### 🔍 Single Order Investigation")
    order_id = st.selectbox("Select an Order ID to review in detail", queue_df["order_id"].tolist())
    if not order_id:
        return

    with get_cursor() as (conn, cur):
        order = get_order_detail(cur, order_id)
        blacklist_entry = get_active_blacklist_entry(cur, order["ip_address"]) if order else None

    if not order:
        st.warning("Order not found (it may have just been resolved).")
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
        st.markdown("**👤 Customer Details**")
        st.write(f"**Name:** {order['customer_name']} ({order['user_id']})")
        st.write(f"**Email:** {order['email']}")
        st.write(f"**Phone:** {order['phone_number']}")
        st.write(f"**Address:** {order['address']}") 
    with col2:
        st.markdown("**📦 Order Details**")
        st.write(f"**Product:** {order['product_name']} x{order['quantity']}")
        st.write(f"**Amount:** ₹{order['amount']:,.2f}")
        st.write(f"**IP Address:** {order['ip_address']}" + (" 🚫 *(blacklisted)*" if blacklist_entry else ""))
        st.write(f"**Device:** {order['device_id']}")
        st.write(f"**Placed At:** {order['order_timestamp']}")

    st.error(f"**🚨 Flagged Reason:** {order['flagged_reason']}")

    _blacklist_ip_action(analyst, order["ip_address"], blacklist_entry, key_suffix=order_id)

    # --- SINGLE ACTION DECISION ---
    st.markdown("#### ⚖️ Analyst Decision")
    with st.container(border=True):
        comments = st.text_area("Review Comments (required for rejection, optional for approval)", key=f"comments_{order_id}")

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("✅ Approve Order", type="primary", key=f"approve_{order_id}", use_container_width=True):
                confirm_approve_order(analyst["analyst_id"], order_id, comments)
                
        with col_reject:
            if st.button("🚫 Reject Order", key=f"reject_{order_id}", use_container_width=True):
                if not comments.strip():
                    st.warning("Please provide a reason in the comments before rejecting.")
                else:
                    confirm_reject_order(analyst["analyst_id"], order_id, comments)


def _blacklist_ip_action(analyst: dict, ip_address: str, blacklist_entry: dict, key_suffix: str):
    """Blacklist-IP action surfaced from within order review, per-IP, with a mandatory reason."""
    if blacklist_entry:
        st.info(
            f"🚫 IP **{ip_address}** is already blacklisted "
            f"(reason: {blacklist_entry['reason']}, by {blacklist_entry['blacklisted_by_name'] or blacklist_entry['blacklisted_by']} "
            f"on {blacklist_entry['blacklisted_at']})."
        )
        return

    with st.expander(f"🛡️ Security Action: Blacklist IP {ip_address}"):
        with st.form(f"blacklist_form_{key_suffix}"):
            reason = st.text_area("Blacklist Reason (required)", key=f"blacklist_reason_{key_suffix}")
            submitted = st.form_submit_button("Lock IP Address")
            if submitted:
                if not reason.strip():
                    st.error("A reason is required to blacklist an IP address.")
                else:
                    confirm_blacklist_ip(analyst["analyst_id"], ip_address, reason.strip())


def render():
    # Auth is handled centrally by analyst_app.py
    analyst = st.session_state.get("analyst")
    if not analyst:
        st.error("Access Denied. Please log in through the main portal.")
        return

    st.header(f"🛡️ Fraud Analyst Workspace")
    st.caption(f"Logged in as: **{analyst['employee_name']}**")
    render_queue_and_review(analyst)