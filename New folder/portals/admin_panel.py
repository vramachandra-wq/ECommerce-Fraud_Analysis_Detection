"""Admin Control Panel: user management, analytics, rule stats, overrides."""
import sys
from pathlib import Path
import requests
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

import plotly.express as px
import streamlit as st
from config import API_BASE_URL, API_TIMEOUT
from database.connection import get_cursor
from auth.analyst_auth import ALL_PAGES, PAGE_LABELS
from fraud_engine.auto_approval import sync_expired_holds
from portals.analyst_dashboard import render_queue_and_review
from utils.queries import (
    get_active_blacklist_entry,
    get_active_phone_blacklist_entry,
    get_active_email_blacklist_entry,
    get_analyst_performance,
    get_kpis,
    get_orders_over_time,
    get_permission_matrix,
    get_recent_orders,
    get_rule_stats
)


def _inject_tab_bar_css():
    # Scoped to the "admin_tab_bar" container key (Streamlit renders it as
    # class "st-key-admin_tab_bar") so this never touches the sidebar's own
    # radio-based navigation or any other radio widget in the app.
    st.markdown("""
        <style>
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] {
            display: flex !important;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] label {
            display: flex !important;
            flex: 0 0 auto;
            width: 220px;
            box-sizing: border-box;
            justify-content: center;
            align-items: center;
            text-align: center;
            background-color: var(--secondary-background-color) !important;
            border: 1px solid rgba(128, 128, 128, 0.3) !important;
            border-radius: 8px !important;
            padding: 0.5rem 0.75rem !important;
            margin: 0 !important;
            cursor: pointer;
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #dc2626 !important;
            border-color: #dc2626 !important;
        }
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            font-weight: 600 !important;
        }
        div[class*="st-key-admin_tab_bar"] div[role="radiogroup"] label > div:first-child {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)


def _build_api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _send_api_request(method: str, endpoint: str, payload: dict):
    try:
        if method.lower() == "post":
            response = requests.post(_build_api_url(endpoint), json=payload, timeout=API_TIMEOUT)
        elif method.lower() == "put":
            response = requests.put(_build_api_url(endpoint), json=payload, timeout=API_TIMEOUT)
        else:
            raise ValueError(f"Unsupported API method: {method}")
    except requests.exceptions.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return None

    if response.status_code != 200:
        st.error(f"API error ({response.status_code}): {response.text}")
        return None

    return response


@st.dialog("Confirm Create Analyst")
def confirm_create_analyst(payload: dict):
    st.markdown("### Create New Analyst — Confirm Details")
    st.json(payload)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Analyst Account", type="primary", use_container_width=True):
            with st.spinner("Creating analyst account..."):
                resp = _send_api_request("post", "create-analyst", payload)
            if resp is not None:
                st.success(f"✅ Analyst {payload.get('employee_name')} created.")
                time.sleep(1)
                st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Confirm Blacklist Action")
def confirm_blacklist_action(endpoint: str, payload: dict, entity_label: str):
    st.warning(f"Are you sure you want to blacklist {entity_label}?")
    st.json(payload)
    if st.button(f"Confirm Blacklist", type="primary", use_container_width=True):
        with st.spinner("Applying blacklist..."):
            resp = _send_api_request("post", endpoint, payload)
        if resp is not None:
            st.success(f"{entity_label} blacklisted.")
            time.sleep(1)
            st.rerun()
    if st.button("Cancel", use_container_width=True):
        st.rerun()


@st.dialog("Confirm Whitelist Action")
def confirm_whitelist_action(endpoint: str, payload: dict, entity_label: str):
    st.warning(f"Are you sure you want to whitelist {entity_label}? This will remove it from the blacklist.")
    st.json(payload)
    if st.button(f"Confirm Whitelist", type="primary", use_container_width=True):
        with st.spinner("Removing from blacklist..."):
            resp = _send_api_request("put", endpoint, payload)
        if resp is not None:
            st.success(f"{entity_label} whitelisted.")
            time.sleep(1)
            st.rerun()
    if st.button("Cancel", use_container_width=True):
        st.rerun()


def _tab_user_management():
    st.markdown("### 👥 User Management")
    st.caption("Create new analyst profiles and monitor current team performance.")

    with st.expander("➕ Create New Analyst Profile", expanded=True):
        with st.form("create_analyst"):
            col1, col2 = st.columns(2)
            with col1:
                analyst_id = st.text_input("Analyst ID", placeholder="e.g. A2")
                employee_name = st.text_input("Employee Name", placeholder="e.g. Jane Doe")
            with col2:
                username = st.text_input("Username", placeholder="e.g. jdoe")
                password = st.text_input("Password", type="password")
            
            role = st.selectbox("Role", ["Fraud Analyst", "Senior Fraud Analyst", "Admin"])
            
            st.divider()
            confirm = st.checkbox("⚠️ I confirm that I want to create this analyst profile.")
            submitted = st.form_submit_button("Create Analyst", type="primary")

    if submitted:
        if not all([analyst_id, employee_name, username, password]):
            st.error("All fields are required.")
        elif not confirm:
            st.warning("Please check the confirmation box to proceed with creation.")
        else:
            payload = {
                "analyst_id": analyst_id,
                "employee_name": employee_name,
                "username": username,
                "password": password,
                "role": role,
            }
            confirm_create_analyst(payload)


    st.markdown("#### 📈 Analyst Performance")
    with get_cursor() as (conn, cur):
        perf_df = get_analyst_performance(cur)
    st.dataframe(perf_df, use_container_width=True, hide_index=True)


def _tab_blacklists(analyst: dict):
    st.markdown("### 🛡️ Entity Blacklist Management")
    st.caption("Check, blacklist, or whitelist IP addresses, phone numbers, and emails.")
    
    entity_type = st.radio(
        "Entity Type",
        ["🌐 IP Address", "📱 Phone Number", "📧 Email"],
        horizontal=True,
        label_visibility="collapsed",
        key="blacklist_entity_type",
    )

    # --- IP SECTION ---
    if entity_type == "🌐 IP Address":
        col_lookup, _ = st.columns([1, 1])
        with col_lookup:
            ip_address = st.text_input("IP Lookup", placeholder="e.g. 203.0.113.111", key="ip_lookup")
            if st.button("🔍 Check IP", key="btn_check_ip"):
                st.session_state.blacklist_checked_ip = ip_address.strip()

        checked_ip = st.session_state.get("blacklist_checked_ip")
        if checked_ip:
            st.divider()
            with get_cursor() as (conn, cur):
                entry = get_active_blacklist_entry(cur, checked_ip)

            if entry:
                st.error(f"🚫 **{checked_ip}** is currently blacklisted.")
                st.write(f"**Reason:** {entry['reason']} | **By:** {entry['blacklisted_by_name'] or entry['blacklisted_by']} | **Date:** {str(entry['blacklisted_at']).split()[0]}")
                if st.button("Whitelist IP", type="primary", key="whitelist_ip"):
                    payload = {"removed_by": analyst["analyst_id"], "removed_at": str(datetime.now()), "blacklist_id": entry["blacklist_id"]}
                    confirm_whitelist_action("whitelist-ip", payload, f"IP {checked_ip}")
            else:
                st.success(f"✅ **{checked_ip}** is safe.")
                with st.form("form_bl_ip"):
                    reason = st.text_area("Reason")
                    if st.form_submit_button("Blacklist IP", type="primary") and reason:
                        payload = {"ip_address": checked_ip, "reason": reason, "blacklisted_by": analyst["analyst_id"]}
                        confirm_blacklist_action("blacklist-ip", payload, f"IP {checked_ip}")

    # --- PHONE SECTION ---
    elif entity_type == "📱 Phone Number":
        col_lookup, _ = st.columns([1, 1])
        with col_lookup:
            phone = st.text_input("Phone Lookup", placeholder="e.g. +919876543210", key="phone_lookup")
            if st.button("🔍 Check Phone", key="btn_check_phone"):
                st.session_state.blacklist_checked_phone = phone.strip()

        checked_phone = st.session_state.get("blacklist_checked_phone")
        if checked_phone:
            st.divider()
            with get_cursor() as (conn, cur):
                entry = get_active_phone_blacklist_entry(cur, checked_phone)

            if entry:
                st.error(f"🚫 **{checked_phone}** is currently blacklisted.")
                st.write(f"**Reason:** {entry['reason']} | **By:** {entry['blacklisted_by_name'] or entry['blacklisted_by']} | **Date:** {str(entry['blacklisted_at']).split()[0]}")
                if st.button("Whitelist Phone", type="primary", key="whitelist_phone"):
                    payload = {"removed_by": analyst["analyst_id"], "removed_at": str(datetime.now()), "blacklist_id": entry["blacklist_id"]}
                    confirm_whitelist_action("whitelist-phone", payload, f"Phone {checked_phone}")
            else:
                st.success(f"✅ **{checked_phone}** is safe.")
                with st.form("form_bl_phone"):
                    reason = st.text_area("Reason")
                    if st.form_submit_button("Blacklist Phone", type="primary") and reason:
                        payload = {"phone_number": checked_phone, "reason": reason, "blacklisted_by": analyst["analyst_id"]}
                        confirm_blacklist_action("blacklist-phone", payload, f"Phone {checked_phone}")

    # --- EMAIL SECTION ---
    else:
        col_lookup, _ = st.columns([1, 1])
        with col_lookup:
            email = st.text_input("Email Lookup", placeholder="e.g. fraud@example.com", key="email_lookup")
            if st.button("🔍 Check Email", key="btn_check_email"):
                st.session_state.blacklist_checked_email = email.strip()

        checked_email = st.session_state.get("blacklist_checked_email")
        if checked_email:
            st.divider()
            with get_cursor() as (conn, cur):
                entry = get_active_email_blacklist_entry(cur, checked_email)

            if entry:
                st.error(f"🚫 **{checked_email}** is currently blacklisted.")
                st.write(f"**Reason:** {entry['reason']} | **By:** {entry['blacklisted_by_name'] or entry['blacklisted_by']} | **Date:** {str(entry['blacklisted_at']).split()[0]}")
                if st.button("Whitelist Email", type="primary", key="whitelist_email"):
                    payload = {"removed_by": analyst["analyst_id"], "removed_at": str(datetime.now()), "blacklist_id": entry["blacklist_id"]}
                    confirm_whitelist_action("whitelist-email", payload, f"Email {checked_email}")
            else:
                st.success(f"✅ **{checked_email}** is safe.")
                with st.form("form_bl_email"):
                    reason = st.text_area("Reason")
                    if st.form_submit_button("Blacklist Email", type="primary") and reason:
                        payload = {"email": checked_email, "reason": reason, "blacklisted_by": analyst["analyst_id"]}
                        confirm_blacklist_action("blacklist-email", payload, f"Email {checked_email}")


def _tab_permissions(analyst: dict):
    st.markdown("### 🔐 Analyst Page Permissions")
    st.caption("Grant or revoke access to each page. Admins always have full access and aren't listed here.")

    with get_cursor() as (conn, cur):
        analysts = get_permission_matrix(cur)

    if not analysts:
        st.info("No non-admin analysts exist yet.")
        return

    analyst_options = {
        f"{a['employee_name']} ({a['username']}, {a['role']})": a 
        for a in analysts
    }
    
    col_select, _ = st.columns([1, 1])
    with col_select:
        selected_label = st.selectbox("Select Analyst to Edit", options=list(analyst_options.keys()))
    
    selected_analyst = analyst_options[selected_label]
    target_id = selected_analyst["analyst_id"]

    with st.form("permissions_form"):
        st.markdown(f"**Managing Permissions for:** `{selected_label}`")
        selections = {}
        
        # Display checkboxes in a cleaner grid
        cols = st.columns(3)
        for i, page_key in enumerate(ALL_PAGES):
            col = cols[i % 3]
            selections[page_key] = col.checkbox(
                PAGE_LABELS[page_key],
                value=page_key in selected_analyst["granted_pages"],
                key=f"perm_{target_id}_{page_key}",
            )
            
        st.divider()
        confirm_perms = st.checkbox(f"⚠️ I confirm these permission changes for {selected_analyst['employee_name']}.")
        submitted = st.form_submit_button("Save Permissions", type="primary")

    if submitted:
        if not confirm_perms:
            st.warning("Please check the confirmation box to save these permissions.")
        else:
            with st.spinner(f"Updating permissions for {selected_analyst['employee_name']}..."):
                response = _send_api_request(
                    "put",
                    "permissions/bulk",
                    {
                        "analyst_id": target_id,
                        "permissions": selections,
                        "granted_by": analyst["analyst_id"],
                    },
                )

            if response is not None and response.status_code == 200:
                st.success(f"✅ Permissions successfully updated for {selected_analyst['employee_name']}.")
                time.sleep(1)
                st.rerun()
            elif response is not None:
                st.error(f"Failed to update: {response.text}")


def _tab_analytics():
    st.markdown("### Recent Orders")
    with get_cursor() as (conn, cur):
        kpis = get_kpis(cur)
        recent_df = get_recent_orders(cur)

    # Top KPI Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", f"{kpis['total_orders']:,}")
    col2.metric("Total Fraud Orders", f"{kpis['total_fraud']:,}")
    
    fraud_rate = (kpis['total_fraud'] / kpis['total_orders'] * 100) if kpis['total_orders'] > 0 else 0
    col3.metric("Fraud Rate", f"{fraud_rate:.2f}%")

    st.divider()
    
    # Charts layout
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        status_counts = kpis["status_counts"]
        if status_counts:
            fig = px.pie(
                names=list(status_counts.keys()),
                values=list(status_counts.values()),
                title="Order Status Distribution",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        with get_cursor() as (conn, cur):
            trend_df = get_orders_over_time(cur)
        if trend_df.empty:
            st.info("No orders placed yet this month.")
        else:
            trend_fig = px.line(
                trend_df,
                x="order_date",
                y="order_count",
                markers=True,
                title="Daily Order Volume — Current Month",
            )
            trend_fig.update_xaxes(title="Date")
            trend_fig.update_yaxes(title="Orders", rangemode="tozero")
            st.plotly_chart(trend_fig, use_container_width=True)

    st.markdown("#### 🕒 Recent Orders")
    st.caption("Live view of the latest system transactions.")
    
    if not recent_df.empty:
        # Define columns mapped exactly to the master.orders schema
        expected_cols = [
            'order_id', 
            'user_id', 
            'customer_name',
            'program_id',
            'category',
            'product_name',
            'quantity', 
            'amount', 
            'order_status', 
            'delay_minutes', 
            'order_timestamp',
            'is_fraud',
            'flagged_reason'
        ]
        
        display_cols = [col for col in expected_cols if col in recent_df.columns]
        
        st.dataframe(
            recent_df[display_cols] if display_cols else recent_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "order_id": st.column_config.TextColumn("Order ID"),
                "user_id": st.column_config.TextColumn("User ID"),
                "customer_name": st.column_config.TextColumn("Customer Name"),
                "program_id": st.column_config.TextColumn("Program"),
                "category": st.column_config.TextColumn("Category"),
                "product_name": st.column_config.TextColumn("Product"),
                "quantity": st.column_config.NumberColumn("Qty", help="Number of items purchased"),
                "amount": st.column_config.NumberColumn(
                    "Total Amount",
                    help="Transaction value",
                    format="₹ %.2f"
                ),
                "order_status": st.column_config.TextColumn("Status"),
                "delay_minutes": st.column_config.NumberColumn("Delay (mins)"),
                "order_timestamp": st.column_config.DatetimeColumn("Order Date", format="MMM DD, YYYY, h:mm a"),
                "is_fraud": st.column_config.CheckboxColumn("Fraud?", help="Indicates if the order was flagged as fraud"),
                "flagged_reason": st.column_config.TextColumn(
                    "Flagged Reason", 
                    help="The rule or reason that flagged the order",
                    width="large"
                ),
            }
        )
    else:
        st.info("No recent orders found.")


def _tab_rule_stats():
    """Displays visual analytics and a table for how often rules are firing."""
    st.markdown("### 📋 Rule Trigger Statistics")
    st.caption("Visibility into which automated fraud rules are firing most frequently.")
    
    with get_cursor() as (conn, cur):
        rule_df = get_rule_stats(cur)
        
    if not rule_df.empty:
        fig = px.bar(
            rule_df, 
            x="rule_id", 
            y="times_triggered", 
            title="Rule Trigger Counts",
            color="times_triggered",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(rule_df, use_container_width=True, hide_index=True)
    else:
        st.info("No rule trigger data available to display.")


@st.dialog("Confirm Rule Update")
def _confirm_rule_update(payload, rule_id):
    """Modal dialog to confirm changes before sending to the API."""
    st.warning(f"Are you sure you want to apply these changes to **{rule_id}**?")
    
    # Show the analyst exactly what they are submitting
    st.json(payload)
    
    # Layout the confirmation and cancel buttons side-by-side
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Update Rule", type="primary", use_container_width=True):
            with st.spinner("Updating..."):
                resp = _send_api_request("put", "update-rule", payload)

            if resp is not None and resp.status_code == 200:
                st.success("Rule updated successfully!")
                time.sleep(1.5)  # Brief pause so the user can read the success message
                st.rerun()
            elif resp is not None:
                st.error(f"Failed: {resp.status_code} - {resp.text}")
                
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun() # Closes the modal without doing anything


def _generate_rule_description(rule: dict) -> str:
    """Builds a human-readable description from the rule's live parameters.

    POC-friendly stand-in for a real editable description: instead of relying
    on the static `rule_description` column (which drifts out of sync once
    thresholds/intervals are changed), this composes the sentence fresh from
    whatever is currently configured, so it's always accurate.
    """
    rule_name = rule.get('rule_name', 'This rule')
    rule_type = rule.get('rule_type')
    action = rule.get('action', 'FLAG')
    threshold = rule.get('threshold_value')
    interval_val = rule.get('time_interval_value')
    interval_unit = rule.get('time_interval_unit')

    if rule.get('rule_id') == 'R001':
        return f"Flags P2 iPhone 16 orders for **{action}** based on configured velocity checks."

    if 'blacklist' in rule_name.lower():
        return f"Automatically applies **{action}** to any order matching a blacklisted entity."

    if rule_type in ('VELOCITY', 'BEHAVIORAL') and threshold is not None and interval_val is not None:
        unit_label = str(interval_unit).lower() if interval_unit else "interval"
        return (
            f"Triggers **{action}** when orders exceed **{threshold}** "
            f"within **{interval_val} {unit_label}(s)**."
        )

    if rule_type == 'LINKAGE' and threshold is not None:
        return f"Triggers **{action}** when **{threshold}** or more linked entities are detected on an order."

    return f"Triggers **{action}** based on the `{rule_type}` detection logic configured for this rule."


def _tab_rule_management():
    """Provides a dynamic form to update rule actions, thresholds, and time windows."""
    st.markdown("### ⚙️ Rule Configuration Management")
    st.caption("Adjust actions, thresholds, and time windows for e-commerce fraud detection rules.")
    
    # 1. Fetch current rules 
    with get_cursor() as (conn, cur):
        cur.execute("""
            SELECT rule_id, rule_name, rule_description, rule_type, 
                   action, threshold_value, time_interval_value, time_interval_unit 
            FROM master.rule_master 
            ORDER BY rule_id
        """)
        cols = [desc[0] for desc in cur.description]
        rules_data = [dict(zip(cols, row)) for row in cur.fetchall()]
        
    if not rules_data:
        st.info("No rules found in the database.")
        return
        
    # 2. UI: Select a rule
    rule_options = {f"{r['rule_id']} - {r['rule_name']}": r for r in rules_data}
    selected_rule_label = st.selectbox("Select Rule to Modify", options=list(rule_options.keys()))
    selected_rule = rule_options[selected_rule_label]
    
    st.divider()
    
    st.markdown(f"**Description:** {_generate_rule_description(selected_rule)}")
    st.markdown(f"**Detection Type:** `{selected_rule['rule_type']}`")
    
    is_r001 = selected_rule['rule_id'] == 'R001'
    is_blacklist = 'blacklist' in selected_rule['rule_name'].lower()
    
    # 3. Edit Form
    with st.form(f"edit_form_{selected_rule['rule_id']}"):
        st.subheader("Configuration Parameters")

        # 4. Handle Action Locking
        if is_r001:
            st.info("🔒 **Action is locked to HOLD** for the P2 iPhone 16 Rule.")
            new_action = 'HOLD'
        elif is_blacklist:
            st.error("🔒 **Action is strictly locked to REJECTED** for Blacklist entities.")
            new_action = 'REJECTED'
        else:
            col_action, _ = st.columns([1, 1])
            with col_action:
                actions = ['HOLD', 'REVIEW', 'REJECTED', 'PASS']
                current_action = selected_rule['action']
                action_idx = actions.index(current_action) if current_action in actions else 0
                new_action = st.selectbox("Rule Action", actions, index=action_idx)
        
        # 5. Handle Metrics (Split logic for Linkage vs Velocity/Behavioral)
        requires_interval = (selected_rule['rule_type'] in ['VELOCITY', 'BEHAVIORAL'] or is_r001) and not is_blacklist
        requires_threshold = (selected_rule['rule_type'] in ['VELOCITY', 'BEHAVIORAL', 'LINKAGE']) and not is_blacklist
        
        col_thresh, col_val, col_unit = st.columns(3)
        
        with col_thresh:
            if requires_threshold:
                current_threshold = float(selected_rule['threshold_value']) if selected_rule['threshold_value'] is not None else 0.0
                new_threshold = st.number_input("Threshold", min_value=0.0, value=current_threshold, step=1.0)
            else:
                st.info("Threshold N/A")
                new_threshold = None
                
        with col_val:
            if requires_interval:
                current_interval_val = int(selected_rule['time_interval_value']) if selected_rule['time_interval_value'] is not None else 1
                new_interval_val = st.number_input("Time Interval", min_value=1, value=current_interval_val, step=1)
            else:
                if not requires_threshold: 
                    st.info("Interval N/A")
                new_interval_val = None
                
        with col_unit:
            if requires_interval:
                units = ['MINUTE', 'HOUR', 'DAY', 'WEEK']
                current_unit = selected_rule['time_interval_unit'] if selected_rule['time_interval_unit'] else 'MINUTE'
                unit_idx = units.index(current_unit) if current_unit in units else 0
                new_unit = st.selectbox("Unit", units, index=unit_idx)
            else:
                new_unit = None
                
        submit = st.form_submit_button("Review Changes", type="primary")
        
        # 6. Trigger the Modal Confirmation
        if submit:
            payload = {
                "rule_id": selected_rule['rule_id'],
                "action": new_action,
                "threshold_value": new_threshold,
                "time_interval_value": new_interval_val,
                "time_interval_unit": new_unit
            }
            _confirm_rule_update(payload, selected_rule['rule_id'])


@st.cache_data(ttl=300)
def sync_database_holds():
    """Caches the database synchronization to prevent it from firing on every UI rerun."""
    with get_cursor(commit=True) as (conn, cur):
        sync_expired_holds(conn, cur)
        

def render():
    analyst = st.session_state.get("analyst")
    if not analyst:
        st.error("Access Denied. Please log in through the main portal.")
        return

    st.header(f"⚙️ Admin Control Panel")
    st.caption(f"Logged in as: **{analyst['employee_name']}** ({analyst['role']})")

    # Run the cached synchronization task
    sync_database_holds()

    _inject_tab_bar_css()

    TAB_LABELS = [
        "⚖️ Review Queue (Override)",
        "🛡️ Entity Blacklists",
        "🔐 Analyst Permissions",
        "👥 User Management",
        "📊 Analytics",
        "📋 Rule Management",
    ]

    if "admin_active_tab" not in st.session_state:
        st.session_state.admin_active_tab = TAB_LABELS[0]

    with st.container(key="admin_tab_bar"):
        active_tab = st.radio(
            "Section",
            TAB_LABELS,
            key="admin_active_tab",
            horizontal=True,
            label_visibility="collapsed",
        )

    st.divider()

    if active_tab == TAB_LABELS[0]:
        render_queue_and_review(analyst)

    elif active_tab == TAB_LABELS[1]:
        _tab_blacklists(analyst)

    elif active_tab == TAB_LABELS[2]:
        _tab_permissions(analyst)

    elif active_tab == TAB_LABELS[3]:
        _tab_user_management()

    elif active_tab == TAB_LABELS[4]:
        _tab_analytics()

    elif active_tab == TAB_LABELS[5]:
        _tab_rule_stats()
        st.divider()
        _tab_rule_management()