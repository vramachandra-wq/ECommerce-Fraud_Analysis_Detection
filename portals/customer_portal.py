"""Customer Portal: login -> order form -> fraud evaluation -> confirmation."""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import time

from config import API_BASE_URL, API_TIMEOUT

# Defensive: ensure the project root (parent of this portals/ folder) is on
# sys.path, so imports below resolve even if Streamlit is launched directly
# on this file instead of on app.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from auth.customer_auth import authenticate_customer
from database.connection import get_cursor
from fraud_engine.engine import evaluate_order
from utils.order_utils import calculate_total, generate_order_id
from utils.queries import (
    list_devices, 
    list_products, 
    list_programs
)
from ui.i18n import t, cur_sym, language_toggle
from ui.customer_login import (
    render_login_header,
    render_login_close,
    render_login_illustration,
    render_customer_shell,
)

_CHECKOUT_ADDRESS_KEYS = (
    "checkout_street",
    "checkout_city",
    "checkout_state",
    "checkout_zip_code",
    "checkout_country",
)


def _clear_checkout_address_fields() -> None:
    for key in _CHECKOUT_ADDRESS_KEYS:
        st.session_state.pop(key, None)


def _parse_default_address(default_address: str) -> dict:
    """Best-effort parse of 'street, city, state zip' into structured fields."""
    raw = (default_address or "").strip()
    if not raw:
        return {}

    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if len(parts) < 2:
        return {"street": raw}

    street = parts[0]
    city = parts[1] if len(parts) > 1 else ""
    state = ""
    zip_code = ""
    if len(parts) >= 3:
        tail = parts[2].rsplit(" ", 1)
        if len(tail) == 2 and tail[1].replace("-", "").isalnum():
            state, zip_code = tail[0].strip(), tail[1].strip()
        else:
            state = parts[2]
    return {
        "street": street,
        "city": city,
        "state": state,
        "zip_code": zip_code,
    }


def _resolve_address_defaults(customer: dict) -> dict:
    """Prefer structured master.customers columns; fall back to default_address."""
    street = (customer.get("street") or "").strip()
    city = (customer.get("city") or "").strip()
    state = (customer.get("state") or "").strip()
    zip_code = str(customer.get("zip_code") or "").strip()
    country = (customer.get("country") or "").strip() or "India"

    if not street or not city:
        parsed = _parse_default_address(customer.get("default_address") or "")
        street = street or parsed.get("street", "")
        city = city or parsed.get("city", "")
        state = state or parsed.get("state", "")
        zip_code = zip_code or parsed.get("zip_code", "")

    return {
        "street": street,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": country,
    }


def _ensure_customer_address(customer: dict) -> dict:
    """Backfill address fields from DB when an older session is missing them."""
    if (customer.get("street") or "").strip() and (customer.get("city") or "").strip():
        return customer

    user_id = customer.get("user_id")
    if not user_id:
        return customer

    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT street, city, state, country, zip_code, default_address
            FROM master.customers
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        return customer

    street, city, state, country, zip_code, default_address = row
    customer = dict(customer)
    customer["street"] = street
    customer["city"] = city
    customer["state"] = state
    customer["country"] = country
    customer["zip_code"] = zip_code
    customer["default_address"] = default_address
    return customer


def _seed_checkout_address_fields(customer: dict) -> None:
    """Initialize editable address widgets once from master.customers defaults."""
    defaults = _resolve_address_defaults(customer)
    mapping = {
        "checkout_street": defaults["street"],
        "checkout_city": defaults["city"],
        "checkout_state": defaults["state"],
        "checkout_zip_code": defaults["zip_code"],
        "checkout_country": defaults["country"],
    }
    for key, value in mapping.items():
        if key not in st.session_state:
            st.session_state[key] = value



def _build_api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _send_api_request(method: str, path: str, **kwargs):
    """Helper to call backend APIs with consistent timeout and error handling.

    Returns the `requests.Response` on success or `None` on failure.
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
        st.error(resp.text if resp.text else f"HTTP {resp.status_code}")
    return resp


@st.dialog(t("confirm_place_order"))
def confirm_place_order(payload: dict, customer_session_key: str = "customer"):
    st.markdown(t("order_summary"))
    # Show a compact summary (full PII visible on customer portal)
    st.write(
        f"**{t('label_customer')}:** {payload.get('customer_name')} — "
        f"**{t('email')}:** {payload.get('email')}"
    )
    st.write(
        f"**{t('label_product')}:** {payload.get('product_name')} x{payload.get('quantity')} — "
        f"**{t('label_amount')}:** {cur_sym()}{payload.get('amount'):,.2f}"
    )
    st.write(f"**{t('label_delivery_address')}:** {payload.get('address')}")
    st.write(
        f"**{t('label_ip')}:** {payload.get('ip_address')} — "
        f"**{t('label_device')}:** {payload.get('device_id')}"
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        # Use a distinct key and label to avoid widget collisions with the
        # order form's "Complete Purchase" button which opens this dialog.
        if st.button(t("confirm_purchase"), type="primary", use_container_width=True, key="confirm_purchase"):
            try:
                with st.spinner(t("completing_purchase")):
                    resp = _send_api_request("post", "create-order", json=payload)
                if not resp:
                    st.error(t("err_order_api_failed"))
                    return

                # Update session state after success
                st.session_state[customer_session_key]["customer_name"] = payload.get("customer_name")
                st.session_state[customer_session_key]["email"] = payload.get("email")
                st.session_state[customer_session_key]["phone_number"] = payload.get("phone_number")
                st.session_state[customer_session_key]["street"] = payload.get("street")
                st.session_state[customer_session_key]["city"] = payload.get("city")
                st.session_state[customer_session_key]["state"] = payload.get("state")
                st.session_state[customer_session_key]["zip_code"] = payload.get("zip_code")
                st.session_state[customer_session_key]["country"] = payload.get("country")
                st.session_state["last_order_id"] = payload.get("order_id")
                _clear_checkout_address_fields()

                time.sleep(0.25)
                st.rerun()
            except Exception as exc:
                st.error(t("err_completing_order", exc=exc))
                return
    with col2:
        if st.button(t("cancel"), use_container_width=True):
            st.rerun()


# --- CACHED DATABASE QUERIES ---

@st.cache_data(ttl=300)
def fetch_form_options():
    """Caches the static catalog data to prevent database spam on every Streamlit rerun."""
    with get_cursor() as (conn, cur):
        products = list_products(cur)
        programs = list_programs(cur)
        devices = list_devices(cur)
    return products, programs, devices


def _login_form():
    st.markdown('<div class="customer-login-marker"></div>', unsafe_allow_html=True)

    _, row, _ = st.columns([0.04, 0.92, 0.04])
    with row:
        st.markdown('<div class="customer-login-row"></div>', unsafe_allow_html=True)
        left, right = st.columns([1.15, 0.85], gap="small")

        with left:
            render_login_header(
                logo=t("customer_app_title"),
                welcome=t("login_welcome_back"),
                title=t("sign_in"),
            )
            with st.form("customer_login"):
                user_id = st.text_input(t("user_id"), placeholder="e.g. U1001")
                password = st.text_input(t("password"), type="password")
                submitted = st.form_submit_button(
                    t("sign_in_cta"),
                    type="primary",
                    use_container_width=True,
                )
            render_login_close()

            if submitted:
                with get_cursor(commit=True) as (conn, cur):
                    customer = authenticate_customer(cur, user_id, password, conn=conn)
                if customer:
                    _clear_checkout_address_fields()
                    st.session_state.customer = customer
                    st.rerun()
                else:
                    st.error(t("invalid_login"))

        with right:
            render_login_illustration("images/login_hero.png")


def _order_form():

    customer = _ensure_customer_address(st.session_state.customer)
    st.session_state.customer = customer
    _seed_checkout_address_fields(customer)

    col_header, col_lang, col_logout = st.columns([0.62, 0.22, 0.16], gap="small")
    with col_header:
        render_customer_shell(
            logo=t("customer_app_title"),
            welcome=t("welcome_back", name=customer["customer_name"]),
            title=t("customer_app_subtitle"),
        )
    with col_lang:
        language_toggle(inline=True)
    with col_logout:
        if st.button(t("log_out"), key="customer_logout", use_container_width=True, type="secondary"):
            _clear_checkout_address_fields()
            del st.session_state.customer
            st.rerun()

    st.image("images/banner_2.png", use_container_width=True)
    st.markdown('<div class="mc-spacer-sm" aria-hidden="true"></div>', unsafe_allow_html=True)

    # Load cached static options
    products, programs, devices = fetch_form_options()

    product_options = {f"{name} — {cur_sym()}{price:,.2f}": (pid, name, cat, price) for pid, name, cat, price in products}
    program_options = {f"{pid} — {name}": pid for pid, name in programs}
    device_options = {f"{did} — {name}": did for did, name, dtype in devices}

    name = customer["customer_name"]
    email = customer["email"]
    phone = customer["phone_number"] or ""

    with st.container(border=True):
        st.markdown(
            f'<p class="customer-section-title">{t("contact_details")}</p>',
            unsafe_allow_html=True,
        )
        # Email and phone come from master.customers and stay read-only so
        # blacklist checks (R011/R012) cannot be bypassed at checkout.
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(t("name"), value=name, disabled=True)
            st.text_input(t("email"), value=email, disabled=True)
        with col2:
            st.text_input(t("phone"), value=phone, disabled=True)
        if not phone:
            st.warning(t("no_phone_warning"))

    with st.container(border=True):
        st.markdown(
            f'<p class="customer-section-title">{t("delivery_address")}</p>',
            unsafe_allow_html=True,
        )
        col_addr1, col_addr2 = st.columns(2)
        with col_addr1:
            street = st.text_input(t("street"), key="checkout_street", placeholder="e.g. 21 MG Road")
            city = st.text_input(t("city"), key="checkout_city", placeholder="e.g. Bengaluru")
        with col_addr2:
            state = st.text_input(t("state"), key="checkout_state", placeholder="e.g. Karnataka")
            zip_code = st.text_input(t("zip_code"), key="checkout_zip_code", placeholder="e.g. 560001")
        country = st.text_input(t("country"), key="checkout_country")

    with st.container(border=True):
        st.markdown(
            f'<p class="customer-section-title">{t("sim_fields")}</p>',
            unsafe_allow_html=True,
        )
        st.caption(t("sim_caption"))
        col3, col4, col5 = st.columns(3)
        with col3:
            ip_address = st.text_input(t("ip_address"), placeholder="e.g. 203.0.113.111")
        with col4:
            program_label = st.selectbox(
                t("program_track"),
                list(program_options.keys()),
                index=list(program_options.values()).index(customer["program_id"])
                if customer["program_id"] in program_options.values()
                else 0,
            )
            program_id = program_options[program_label]
        with col5:
            device_label = st.selectbox(t("device"), list(device_options.keys()))
            device_id = device_options[device_label]

    with st.container(border=True):
        st.markdown(
            f'<p class="customer-section-title">{t("product_selection")}</p>',
            unsafe_allow_html=True,
        )
        product_label = st.selectbox(t("product"), list(product_options.keys()))
        product_id, product_name, category, price = product_options[product_label]
        quantity = st.number_input(t("quantity"), min_value=1, value=1, step=1)
        total = calculate_total(price, quantity)
        st.metric(t("total_price"), f"{cur_sym()}{total:,.2f}")

    if st.button(t("complete_purchase"), type="primary", use_container_width=True, key="open_confirm"):
        errors = []
        if not name.strip():
            errors.append(t("err_name_required"))
        if not email.strip() or "@" not in email:
            errors.append(t("err_email_required"))
        if not phone.strip():
            errors.append(t("err_phone_required"))
        
        if not street.strip() or not city.strip() or not state.strip() or not zip_code.strip():
            errors.append(t("err_address_required"))
            
        if not ip_address.strip():
            errors.append(t("err_ip_required"))
            
        if errors:
            for err in errors:
                st.error(err)
            return

        with st.spinner(t("processing_purchase")):
            # Wall-clock Asia/Kolkata (matches DB session timezone)
            order_timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
            
            # FORMAT ADDRESS: "street, city, state zip_code"
            formatted_address = f"{street.strip()}, {city.strip()}, {state.strip()} {zip_code.strip()}"
            
            try:
                # Open ONE connection for the ID generation & fraud evaluation
                with get_cursor() as (conn, cur):
                    
                    order_id = generate_order_id(cur)
                    
                    ctx = {
                        "user_id": customer["user_id"],
                        "program_id": program_id,
                        "product_id": product_id,
                        "product_name": product_name,
                        "category": category,
                        "quantity": int(quantity),
                        "amount": total,
                        "ip_address": ip_address.strip(),
                        "device_id": device_id,
                        "email": email,
                        "phone_number": phone,
                        "address": formatted_address,
                        "order_timestamp": order_timestamp,
                    }

                    # Evaluate using both the cursor and the context
                    disposition = evaluate_order(cur, ctx)
                
                # Only stamp approval/rejection times for terminal statuses
                status = disposition["order_status"]
                order_approved_at = order_timestamp if status == "APPROVED" else None
                order_rejected_at = order_timestamp if status == "REJECTED" else None

                # Send ALL detailed fields to the updated FastAPI backend
                payload = {
                    "order_id": order_id,
                    "user_id": ctx["user_id"],
                    "program_id": ctx["program_id"],
                    "product_id": ctx["product_id"],
                    "category": ctx["category"],
                    "product_name": ctx["product_name"],
                    "quantity": ctx["quantity"],
                    "amount": ctx["amount"],
                    "ip_address": ctx["ip_address"],
                    "device_id": ctx["device_id"],
                    "customer_name": name.strip(),
                    "email": ctx["email"],
                    "address": ctx["address"],

                    # Individual Address Fields
                    "street": street.strip(),
                    "city": city.strip(),
                    "state": state.strip(),
                    "zip_code": zip_code.strip(),
                    "country": country.strip(),

                    "phone_number": phone.strip(),
                    "order_timestamp": str(ctx["order_timestamp"]),
                    "delay_minutes": disposition["delay_minutes"],
                    "is_fraud": disposition["is_fraud"],
                    "flagged_reason": disposition["flagged_reason"],
                    "order_status": disposition["order_status"],
                    "order_approved_at": str(order_approved_at) if order_approved_at else None,
                    "order_rejected_at": str(order_rejected_at) if order_rejected_at else None,
                    "triggered_rules": disposition["triggered_rules"],
                }
                # Open confirmation dialog; let the dialog set session state
                # after the user confirms the purchase (or cancels).
                confirm_place_order(payload)

            except requests.exceptions.RequestException:
                st.error(t("err_api_connection"))


def render():
    if "customer" not in st.session_state:
        _login_form()
        return

    if "last_order_id" in st.session_state:
        col_header, col_lang, col_logout = st.columns([0.62, 0.22, 0.16], gap="small")
        with col_header:
            render_customer_shell(
                logo=t("customer_app_title"),
                welcome=t("order_success"),
            )
        with col_lang:
            language_toggle(inline=True)
        with col_logout:
            if st.button(t("log_out"), key="customer_logout_success", use_container_width=True, type="secondary"):
                _clear_checkout_address_fields()
                st.session_state.pop("customer", None)
                st.session_state.pop("last_order_id", None)
                st.rerun()
        with st.container(border=True):
            st.metric(t("your_order_id"), st.session_state.last_order_id)
        if st.button(t("place_another_order"), type="primary", use_container_width=True):
            del st.session_state.last_order_id
            st.rerun()
        return

    _order_form()