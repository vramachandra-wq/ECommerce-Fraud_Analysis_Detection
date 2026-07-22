"""Fraud Analyst Dashboard: queue of ON_HOLD / PENDING_REVIEW orders + backlog management."""
import sys
from datetime import datetime
from pathlib import Path
import requests
import time

from config import API_BASE_URL, API_TIMEOUT
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from database.connection import get_cursor
from portals.hold_sync import sync_database_holds
from fraud_engine.backlog import detect_backlog_orders, fetch_review_queue_with_delay, get_backlog_stats
from utils.queries import (
    get_active_blacklist_entry,
    get_active_phone_blacklist_entry,
    get_active_email_blacklist_entry,
    get_order_detail,
)
from utils.pii import display_pii
from ui.i18n import t, cur_sym, format_duration_minutes

STATUS_ICONS = {
    "ON_HOLD": "⏳",
    "PENDING_REVIEW": "🕵️",
    "APPROVED": "✅",
    "REJECTED": "🚫",
}


def _build_api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _send_api_request(method: str, path: str, **kwargs):
    """Centralized request helper with timeout and error handling."""
    url = _build_api_url(path)
    try:
        func = getattr(requests, method.lower())
    except AttributeError:
        st.error(t("err_invalid_http_method", method=method))
        return None

    try:
        resp = func(url, timeout=API_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        st.error(t("err_api_timeout", exc=exc))
        return None

    if not resp.ok:
        body = resp.text if resp.text else f"HTTP {resp.status_code}"
        st.error(body)
    return resp


def inject_dashboard_css():
    """Dashboard-only accents; global theme lives in ui/style.py."""
    st.markdown(
        """
        <style>
        .dashboard-card h3 {
          margin: 0;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 0.55rem;
          font-size: 1.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- CONFIRMATION DIALOGS (single set used by queue + backlog) ---

@st.dialog("Confirm Approval")
def confirm_approve_order(analyst_id, order_id, comments, *, backlog_bulk_wording=False):
    st.write(t("confirm_approve_one"))
    if st.button(t("confirm_approve_btn"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_approving")):
            response = _send_api_request(
                "put",
                "approve-order",
                json={
                    "approved_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments or "Approved by analyst",
                    "order_id": order_id,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_order_approved", order_id=order_id))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Rejection")
def confirm_reject_order(analyst_id, order_id, comments, is_fraud=False):
    st.write(t("confirm_fraud_one") if is_fraud else t("confirm_reject_one"))
    if st.button(t("confirm"), type="primary", use_container_width=True):
        with st.spinner(t("processing")):
            response = _send_api_request(
                "put",
                "reject-order",
                json={
                    "is_fraud": is_fraud,
                    "rejected_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments or (
                        "Marked as fraud" if is_fraud else "Rejected by analyst"
                    ),
                    "order_id": order_id,
                },
            )
        if not response or response.status_code != 200:
            return
        if is_fraud:
            st.success(t("success_order_fraud", order_id=order_id))
        else:
            st.success(t("success_order_rejected", order_id=order_id))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Batch Approval")
def confirm_batch_approve(analyst_id, order_ids, comments, *, for_backlog=False):
    if for_backlog:
        st.write(t("confirm_approve_all_backlog"))
    else:
        st.write(t("confirm_approve_selected", n=len(order_ids)))
    if st.button(t("confirm_approve_all_btn"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_approving_n", n=len(order_ids))):
            response = _send_api_request(
                "put",
                "batch-approve",
                json={
                    "approved_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments or "Batch approved by analyst",
                    "order_ids": order_ids,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_orders_approved", n=len(order_ids)))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Batch Rejection")
def confirm_batch_reject(analyst_id, order_ids, comments, is_fraud=False, *, for_backlog=False):
    if for_backlog:
        st.write(t("confirm_fraud_all_backlog") if is_fraud else t("confirm_reject_all_backlog"))
    else:
        st.write(
            t("confirm_fraud_selected", n=len(order_ids))
            if is_fraud
            else t("confirm_reject_selected", n=len(order_ids))
        )
    if st.button(t("confirm"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_processing_n", n=len(order_ids))):
            response = _send_api_request(
                "put",
                "batch-reject",
                json={
                    "is_fraud": is_fraud,
                    "rejected_at": str(datetime.now()),
                    "reviewed_by": analyst_id,
                    "review_comments": comments or (
                        "Batch marked as fraud" if is_fraud else "Batch rejected by analyst"
                    ),
                    "order_ids": order_ids,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_orders_processed", n=len(order_ids)))
        time.sleep(1)
        st.rerun()


@st.dialog("No Backlog Orders")
def show_no_backlog_dialog():
    st.write(t("no_backlog_message"))
    if st.button(t("ok"), use_container_width=True):
        st.rerun()


@st.dialog("Confirm Blacklist")
def confirm_blacklist_ip(analyst_id, ip_address, reason):
    st.write(t("confirm_blacklist_ip", value=ip_address))
    st.error(t("blacklist_ip_warning"))
    if st.button(t("confirm_blacklist_btn"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_blacklist_ip")):
            response = _send_api_request(
                "post",
                "blacklist-ip",
                json={
                    "ip_address": ip_address,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_ip_blacklisted", value=ip_address))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Blacklist")
def confirm_blacklist_phone(analyst_id, phone_number, reason):
    st.write(t("confirm_blacklist_phone", value=phone_number))
    st.error(t("blacklist_phone_warning"))
    if st.button(t("confirm_blacklist_btn"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_blacklist_phone")):
            response = _send_api_request(
                "post",
                "blacklist-phone",
                json={
                    "phone_number": phone_number,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_phone_blacklisted", value=phone_number))
        time.sleep(1)
        st.rerun()


@st.dialog("Confirm Blacklist")
def confirm_blacklist_email(analyst_id, email, reason):
    st.write(t("confirm_blacklist_email", value=email))
    st.error(t("blacklist_email_warning"))
    if st.button(t("confirm_blacklist_btn"), type="primary", use_container_width=True):
        with st.spinner(t("spinner_blacklist_email")):
            response = _send_api_request(
                "post",
                "blacklist-email",
                json={
                    "email": email,
                    "reason": reason,
                    "blacklisted_by": analyst_id,
                },
            )
        if not response or response.status_code != 200:
            return
        st.success(t("success_email_blacklisted", value=email))
        time.sleep(1)
        st.rerun()


def _format_minutes(minutes) -> str:
    return format_duration_minutes(minutes)


def _render_backlog_section(analyst: dict):
    """Dedicated Backlog dashboard using the shared detection service."""
    st.markdown(f"#### {t('backlog_section')}")

    btn_col1, btn_col2, _ = st.columns([1.4, 1, 2])
    with btn_col1:
        find_clicked = st.button(
            t("find_backlog_orders"),
            type="primary",
            use_container_width=True,
            key="find_backlog_btn",
        )
    with btn_col2:
        refresh_clicked = st.button(
            t("refresh_backlog"),
            use_container_width=True,
            key="refresh_backlog_btn",
        )

    if find_clicked or refresh_clicked or "backlog_df" not in st.session_state:
        with st.spinner(t("loading_backlog")):
            with get_cursor() as (conn, cur):
                backlog_df = detect_backlog_orders(cur)
                stats = get_backlog_stats(cur)
        st.session_state["backlog_df"] = backlog_df
        st.session_state["backlog_stats"] = stats

        if find_clicked and backlog_df.empty:
            show_no_backlog_dialog()
            return

    backlog_df = st.session_state.get("backlog_df", pd.DataFrame())
    stats = st.session_state.get(
        "backlog_stats",
        {"total_backlog": 0, "oldest_order_id": None, "max_minutes_overdue": 0},
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("total_backlog"), stats.get("total_backlog", 0))
    with c2:
        st.metric(t("oldest_backlog"), stats.get("oldest_order_id") or "—")
    with c3:
        st.metric(t("max_overdue"), _format_minutes(stats.get("max_minutes_overdue", 0)))

    if backlog_df is None or backlog_df.empty:
        st.info(t("backlog_empty_hint"))
        return

    display = backlog_df.copy()
    display["remaining_review"] = display["minutes_remaining_display"].apply(_format_minutes)
    display["time_overdue"] = display["minutes_overdue"].apply(_format_minutes)
    display["Highlight"] = display["is_overdue"].map(
        lambda x: t("overdue_flag") if x else ""
    )

    st.dataframe(
        display[
            [
                "order_id", "customer_name", "rule_name", "delay_minutes",
                "tagged_timestamp", "remaining_review", "time_overdue",
                "order_status", "Highlight",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "order_id": t("col_order_id"),
            "customer_name": t("col_customer"),
            "rule_name": t("col_rule_name"),
            "delay_minutes": t("col_delay_minutes"),
            "tagged_timestamp": st.column_config.DatetimeColumn(
                t("col_tagged_at"), format="D MMM YYYY, h:mm a"
            ),
            "remaining_review": t("remaining_review"),
            "time_overdue": t("col_time_overdue"),
            "order_status": t("col_status"),
            "Highlight": t("col_flag"),
        },
    )

    backlog_ids = backlog_df["order_id"].tolist()
    st.markdown(f"#### {t('backlog_bulk_actions')}")
    with st.container(border=True):
        bulk_comments = st.text_area(t("batch_comments"), key="backlog_bulk_comments")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(t("approve_all_backlog"), type="primary", use_container_width=True):
                confirm_batch_approve(
                    analyst["analyst_id"], backlog_ids, bulk_comments, for_backlog=True
                )
        with b2:
            if st.button(t("reject_all_backlog"), use_container_width=True):
                confirm_batch_reject(
                    analyst["analyst_id"], backlog_ids, bulk_comments,
                    is_fraud=False, for_backlog=True,
                )
        with b3:
            if st.button(t("fraud_all_backlog"), use_container_width=True):
                confirm_batch_reject(
                    analyst["analyst_id"], backlog_ids, bulk_comments,
                    is_fraud=True, for_backlog=True,
                )

    st.markdown(f"#### {t('backlog_individual_actions')}")
    selected_bl = st.selectbox(
        t("select_backlog_order"), backlog_ids, key="backlog_order_select",
    )
    if selected_bl:
        with st.container(border=True):
            comments = st.text_area(
                t("review_comments"), key=f"backlog_comments_{selected_bl}",
            )
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button(
                    t("approve_order"), type="primary",
                    key=f"bl_approve_{selected_bl}", use_container_width=True,
                ):
                    confirm_approve_order(analyst["analyst_id"], selected_bl, comments)
            with a2:
                if st.button(
                    t("reject_order"), key=f"bl_reject_{selected_bl}",
                    use_container_width=True,
                ):
                    confirm_reject_order(
                        analyst["analyst_id"], selected_bl, comments, is_fraud=False
                    )
            with a3:
                if st.button(
                    t("reject_order_fraud"), key=f"bl_fraud_{selected_bl}",
                    use_container_width=True,
                ):
                    confirm_reject_order(
                        analyst["analyst_id"], selected_bl, comments, is_fraud=True
                    )


def render_queue_and_review(analyst: dict):
    """Shared queue + review UI for Analyst Dashboard and Admin overrides."""
    inject_dashboard_css()

    # Lightweight UI fallback; primary path is api/scheduler.py
    auto_approved = sync_database_holds()
    if auto_approved:
        st.info(t("auto_approved_info", n=auto_approved))

    # Single enriched query (no duplicate get_queue_orders round-trip)
    with get_cursor() as (conn, cur):
        queue_df = fetch_review_queue_with_delay(cur)
        backlog_stats = get_backlog_stats(cur)

    st.markdown(f"#### {t('queue_overview')}")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    total_pending = (
        len(queue_df[queue_df["order_status"] == "PENDING_REVIEW"]) if not queue_df.empty else 0
    )
    total_hold = (
        len(queue_df[queue_df["order_status"] == "ON_HOLD"]) if not queue_df.empty else 0
    )

    with metric_col1:
        st.metric(t("total_in_queue"), len(queue_df))
    with metric_col2:
        st.metric(t("pending_review"), total_pending)
    with metric_col3:
        st.metric(t("on_hold"), total_hold)
    with metric_col4:
        st.metric(t("total_backlog"), backlog_stats.get("total_backlog", 0))

    st.divider()
    _render_backlog_section(analyst)
    st.divider()

    st.markdown(f"#### {t('review_queue')}")
    if queue_df.empty:
        st.success(t("queue_clear"))
        return

    queue_display = queue_df.copy()
    queue_display["Remaining"] = queue_display["minutes_remaining_display"].apply(_format_minutes)
    queue_display["Overdue"] = queue_display.apply(
        lambda r: _format_minutes(r["minutes_overdue"]) if r.get("is_overdue") else "—",
        axis=1,
    )
    queue_display["Flag"] = queue_display["is_overdue"].map(
        lambda x: t("overdue_flag") if x else ""
    )
    # Alias for data editor column label compatibility
    if "tagged_timestamp" in queue_display.columns:
        queue_display["order_timestamp"] = queue_display["tagged_timestamp"]

    select_all = st.checkbox(t("select_all_queue"))
    queue_display.insert(0, "Select", select_all)

    edited_df = st.data_editor(
        queue_display[
            [
                "Select", "order_id", "customer_name", "product_name", "amount",
                "order_status", "delay_minutes", "Remaining", "Overdue", "Flag",
                "order_timestamp",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(t("col_select"), default=False),
            "order_id": t("col_order_id"),
            "customer_name": t("col_customer"),
            "product_name": t("col_product"),
            "amount": st.column_config.NumberColumn(t("col_amount"), format=f"{cur_sym()} %.2f"),
            "order_status": t("col_status"),
            "delay_minutes": t("col_delay_min"),
            "Remaining": t("col_remaining"),
            "Overdue": t("col_overdue"),
            "Flag": t("col_flag"),
            "order_timestamp": st.column_config.DatetimeColumn(
                t("col_placed_at"), format="D MMM YYYY, h:mm a"
            ),
        },
        disabled=[
            "order_id", "customer_name", "product_name", "amount", "order_status",
            "delay_minutes", "Remaining", "Overdue", "Flag", "order_timestamp",
        ],
    )

    selected_order_ids = edited_df[edited_df["Select"]]["order_id"].tolist()

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
                        confirm_batch_approve(
                            analyst["analyst_id"], selected_order_ids, batch_comments
                        )
            with col_batch_rej:
                if st.button(t("reject_selected"), use_container_width=True):
                    if not batch_comments.strip():
                        st.warning(t("warn_comment_reject"))
                    else:
                        confirm_batch_reject(
                            analyst["analyst_id"], selected_order_ids,
                            batch_comments, is_fraud=False,
                        )
            with col_batch_fraud:
                if st.button(t("reject_selected_fraud"), use_container_width=True):
                    if not batch_comments.strip():
                        st.warning(t("warn_comment_reject"))
                    else:
                        confirm_batch_reject(
                            analyst["analyst_id"], selected_order_ids,
                            batch_comments, is_fraud=True,
                        )

    st.divider()
    st.markdown(f"#### {t('single_order_investigation')}")
    order_id = st.selectbox(t("select_order_review"), queue_df["order_id"].tolist())
    if not order_id:
        return

    with get_cursor() as (conn, cur):
        order = get_order_detail(cur, order_id)
        blacklist_entry = (
            get_active_blacklist_entry(cur, order["ip_address"]) if order else None
        )
        phone_blacklist_entry = (
            get_active_phone_blacklist_entry(cur, order["phone_number"]) if order else None
        )
        email_blacklist_entry = (
            get_active_email_blacklist_entry(cur, order["email"]) if order else None
        )

    if not order:
        st.warning(t("order_not_found"))
        return

    status_class = f"status-{order['order_status']}"
    st.markdown(
        f"""
        <div class="dashboard-card">
            <h3 style="margin-top: 0;">Order {order['order_id']}
            <span class="status-badge {status_class}">{STATUS_ICONS.get(order['order_status'], '')} {order['order_status']}</span>
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row_timer = queue_df[queue_df["order_id"] == order_id]
    if not row_timer.empty:
        tr = row_timer.iloc[0]
        t1, t2, t3 = st.columns(3)
        with t1:
            st.metric(t("delay_minutes"), int(tr["delay_minutes"]))
        with t2:
            st.metric(t("remaining_review"), _format_minutes(tr["minutes_remaining_display"]))
        with t3:
            overdue_label = _format_minutes(tr["minutes_overdue"]) if tr["is_overdue"] else "—"
            st.metric(t("time_overdue"), overdue_label)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(t("customer_details"))
        st.write(f"**{t('label_name')}:** {order['customer_name']} ({order['user_id']})")
        st.write(
            f"**{t('email')}:** {display_pii(order['email'], field='email', analyst=analyst)}"
            + (" " + t("blacklisted_suffix") if email_blacklist_entry else "")
        )
        st.write(
            f"**{t('phone')}:** {display_pii(order['phone_number'], field='phone', analyst=analyst)}"
            + (" " + t("blacklisted_suffix") if phone_blacklist_entry else "")
        )
        st.write(f"**{t('label_address')}:** {display_pii(order['address'], field='address', analyst=analyst)}")
    with col2:
        st.markdown(t("order_details"))
        st.write(f"**{t('label_product')}:** {order['product_name']} x{order['quantity']}")
        st.write(f"**{t('label_amount')}:** {cur_sym()}{order['amount']:,.2f}")
        st.write(
            f"**{t('ip_address')}:** {display_pii(order['ip_address'], field='ip', analyst=analyst)}"
            + (" " + t("blacklisted_suffix") if blacklist_entry else "")
        )
        st.write(f"**{t('label_device')}:** {order['device_id']}")
        st.write(f"**{t('label_placed_at')}:** {order['order_timestamp']}")

    st.error(t("flagged_reason", reason=order["flagged_reason"]))

    _blacklist_ip_action(analyst, order["ip_address"], blacklist_entry, key_suffix=order_id)
    _blacklist_phone_action(
        analyst, order["phone_number"], phone_blacklist_entry, key_suffix=order_id
    )
    _blacklist_email_action(
        analyst, order["email"], email_blacklist_entry, key_suffix=order_id
    )

    st.markdown(f"#### {t('analyst_decision')}")
    with st.container(border=True):
        comments = st.text_area(t("review_comments"), key=f"comments_{order_id}")
        col_approve, col_reject, col_fraud = st.columns(3)
        with col_approve:
            if st.button(
                t("approve_order"), type="primary",
                key=f"approve_{order_id}", use_container_width=True,
            ):
                if not comments.strip():
                    st.warning(t("warn_comment_approve"))
                else:
                    confirm_approve_order(analyst["analyst_id"], order_id, comments)
        with col_reject:
            if st.button(t("reject_order"), key=f"reject_{order_id}", use_container_width=True):
                if not comments.strip():
                    st.warning(t("warn_comment_reject"))
                else:
                    confirm_reject_order(
                        analyst["analyst_id"], order_id, comments, is_fraud=False
                    )
        with col_fraud:
            if st.button(
                t("reject_order_fraud"),
                key=f"reject_fraud_{order_id}", use_container_width=True,
            ):
                if not comments.strip():
                    st.warning(t("warn_comment_reject"))
                else:
                    confirm_reject_order(
                        analyst["analyst_id"], order_id, comments, is_fraud=True
                    )


def _blacklist_ip_action(analyst: dict, ip_address: str, blacklist_entry: dict, key_suffix: str):
    if blacklist_entry:
        st.info(
            t(
                "already_blacklisted_ip",
                value=ip_address,
                reason=blacklist_entry["reason"],
                by=blacklist_entry["blacklisted_by_name"] or blacklist_entry["blacklisted_by"],
                at=blacklist_entry["blacklisted_at"],
            )
        )
        return
    with st.expander(t("security_blacklist_ip", value=ip_address)):
        with st.form(f"blacklist_ip_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_ip_reason_{key_suffix}")
            if st.form_submit_button(t("lock_ip")):
                if not reason.strip():
                    st.error(t("err_blacklist_reason_required"))
                else:
                    confirm_blacklist_ip(analyst["analyst_id"], ip_address, reason.strip())


def _blacklist_phone_action(analyst: dict, phone_number: str, blacklist_entry: dict, key_suffix: str):
    if not phone_number:
        return
    if blacklist_entry:
        st.info(
            t(
                "already_blacklisted_phone",
                value=phone_number,
                reason=blacklist_entry["reason"],
                by=blacklist_entry["blacklisted_by_name"] or blacklist_entry["blacklisted_by"],
                at=blacklist_entry["blacklisted_at"],
            )
        )
        return
    with st.expander(t("security_blacklist_phone", value=phone_number)):
        with st.form(f"blacklist_phone_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_phone_reason_{key_suffix}")
            if st.form_submit_button(t("lock_phone")):
                if not reason.strip():
                    st.error(t("err_blacklist_reason_required"))
                else:
                    confirm_blacklist_phone(analyst["analyst_id"], phone_number, reason.strip())


def _blacklist_email_action(analyst: dict, email: str, blacklist_entry: dict, key_suffix: str):
    if not email:
        return
    if blacklist_entry:
        st.info(
            t(
                "already_blacklisted_email",
                value=email,
                reason=blacklist_entry["reason"],
                by=blacklist_entry["blacklisted_by_name"] or blacklist_entry["blacklisted_by"],
                at=blacklist_entry["blacklisted_at"],
            )
        )
        return
    with st.expander(t("security_blacklist_email", value=email)):
        with st.form(f"blacklist_email_form_{key_suffix}"):
            reason = st.text_area(t("blacklist_reason"), key=f"blacklist_email_reason_{key_suffix}")
            if st.form_submit_button(t("lock_email")):
                if not reason.strip():
                    st.error(t("err_blacklist_reason_required"))
                else:
                    confirm_blacklist_email(analyst["analyst_id"], email, reason.strip())


def render():
    analyst = st.session_state.get("analyst")
    if not analyst:
        st.error(t("access_denied"))
        return
    st.header(t("fraud_analyst_workspace"))
    st.caption(t("logged_in_as", name=analyst["employee_name"]))
    render_queue_and_review(analyst)
