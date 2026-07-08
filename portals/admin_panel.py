"""Admin Control Panel: user management, analytics, rule stats, overrides."""
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

import plotly.express as px
import streamlit as st

from auth.analyst_auth import ALL_PAGES, PAGE_LABELS
from database.connection import get_cursor
from fraud_engine.auto_approval import sync_expired_holds
from portals.analyst_dashboard import render_queue_and_review
from utils.queries import (
    get_active_blacklist_entry,
    get_analyst_performance,
    get_kpis,
    get_orders_over_time,
    get_permission_matrix,
    get_recent_orders,
    get_rule_stats,
)


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
            try:

                response = requests.post(
                    "http://127.0.0.1:8000/create-analyst",
                    json={
                        "analyst_id": analyst_id,
                        "employee_name": employee_name,
                        "username": username,
                        "password": password,
                        "role": role,
                    },
                )

                if response.status_code == 200:
                    st.success(f"✅ Analyst **{employee_name}** ({analyst_id}) created successfully.")
                else:
                    st.error(response.text)

            except Exception as e:
                st.error(f"Could not create analyst: {e}")


    st.markdown("#### 📈 Analyst Performance")
    with get_cursor() as (conn, cur):
        perf_df = get_analyst_performance(cur)
    st.dataframe(perf_df, use_container_width=True, hide_index=True)


def _tab_ip_blacklist(analyst: dict):
    st.markdown("### 🛡️ IP Blacklist Management")
    st.caption("Check, blacklist, or whitelist suspicious IP addresses.")
    
    col_lookup, _ = st.columns([1, 1])
    with col_lookup:
        ip_address = st.text_input("IP Address Lookup", placeholder="e.g. 203.0.113.111", key="blacklist_lookup_ip")
        if st.button("🔍 Check Status", key="blacklist_check_btn"):
            st.session_state.blacklist_checked_ip = ip_address.strip()

    st.divider()

    checked_ip = st.session_state.get("blacklist_checked_ip")
    if not checked_ip:
        st.info("Enter an IP address above and click **Check Status** to see if it's blacklisted.")
        return

    with get_cursor() as (conn, cur):
        entry = get_active_blacklist_entry(cur, checked_ip)

    if entry:
        st.error(f"🚫 **{checked_ip}** is currently blacklisted.")
        
        info_col1, info_col2, info_col3 = st.columns(3)
        info_col1.metric("Reason", entry['reason'])
        info_col2.metric("Blacklisted By", entry['blacklisted_by_name'] or entry['blacklisted_by'])
        info_col3.metric("Blacklisted Date", str(entry['blacklisted_at']).split()[0])

        st.markdown("#### Remove from Blacklist")
        confirm_whitelist = st.checkbox(f"⚠️ I confirm I want to whitelist **{checked_ip}**.")
        if st.button("Whitelist IP Address", type="primary", key="whitelist_btn"):
            if not confirm_whitelist:
                st.warning("Please check the confirmation box to proceed with whitelisting.")
            else:
                response = requests.put(
                    "http://127.0.0.1:8000/whitelist-ip",
                    json={
                        "removed_by": analyst["analyst_id"],
                        "removed_at": str(datetime.now()),
                        "blacklist_id": entry["blacklist_id"],
                    },
                )

                if response.status_code != 200:
                    st.error(response.text)

                st.success(f"✅ {checked_ip} has been successfully removed from the blacklist.")
                st.rerun()
    else:
        st.success(f"✅ **{checked_ip}** is not currently blacklisted.")
        
        with st.form("blacklist_ip_form"):
            st.markdown("#### Add to Blacklist")
            reason = st.text_area("Blacklist Reason (required)", placeholder="e.g. Repeated chargeback attempts...")
            confirm_blacklist = st.checkbox(f"⚠️ I confirm I want to blacklist **{checked_ip}**.")
            submitted = st.form_submit_button("Blacklist This IP", type="primary")
            
        if submitted:
            if not reason.strip():
                st.error("A reason is required to blacklist an IP address.")
            elif not confirm_blacklist:
                st.warning("Please check the confirmation box to proceed with blacklisting.")
            else:
                response = requests.post(
                    "http://127.0.0.1:8000/blacklist-ip",
                    json={
                        "ip_address": checked_ip,
                        "reason": reason.strip(),
                        "blacklisted_by": analyst["analyst_id"],
                    },
                )

                if response.status_code != 200:
                    st.error(response.text)
                st.success(f"🚫 {checked_ip} has been blacklisted.")
                st.rerun()


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
            for page_key, granted in selections.items():
                response = requests.put(
                    "http://127.0.0.1:8000/permissions",
                    json={
                        "analyst_id": target_id,
                        "page_key": page_key,
                        "granted": granted,
                        "granted_by": analyst["analyst_id"],
                        "granted_at": str(datetime.now())
                    },
                )

                if response.status_code != 200:
                    st.error(response.text)
                    return
            st.success(f"✅ Permissions successfully updated for {selected_analyst['employee_name']}.")
            st.rerun()


def _tab_analytics():
    st.markdown("### 📊 Platform Analytics")
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
                    format="$ %.2f"
                ),
                "order_status": st.column_config.TextColumn("Status"),
                "delay_minutes": st.column_config.NumberColumn("Delay (mins)"),
                "order_timestamp": st.column_config.DatetimeColumn("Order Date", format="MMM DD, YYYY, h:mm a"),
                "is_fraud": st.column_config.CheckboxColumn("Fraud?", help="Indicates if the order was flagged as fraud"),
                "flagged_reason": st.column_config.TextColumn(
                    "Flagged Reason", 
                    help="The rule or reason that flagged the order",
                    width="large"  # Expands the column width for lengthier text
                ),
            }
        )
    else:
        st.info("No recent orders found.")


def _tab_rule_stats():
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


def render():
    analyst = st.session_state.get("analyst")
    if not analyst:
        st.error("Access Denied. Please log in through the main portal.")
        return

    st.header(f"⚙️ Admin Control Panel")
    st.caption(f"Logged in as: **{analyst['employee_name']}** ({analyst['role']})")

    with get_cursor(commit=True) as (conn, cur):
        sync_expired_holds(conn, cur)

    tab_overrides, tab_blacklist, tab_permissions, tab_users, tab_analytics, tab_rules = st.tabs(
        ["⚖️ Review Queue (Override)", "🛡️ IP Blacklist", "🔐 Analyst Permissions", "👥 User Management", "📊 Analytics", "📋 Rule Stats"]
    )
    
    with tab_overrides:
        render_queue_and_review(analyst)
    with tab_blacklist:
        _tab_ip_blacklist(analyst)
    with tab_permissions:
        _tab_permissions(analyst)
    with tab_users:
        _tab_user_management()
    with tab_analytics:
        _tab_analytics()
    with tab_rules:
        _tab_rule_stats()