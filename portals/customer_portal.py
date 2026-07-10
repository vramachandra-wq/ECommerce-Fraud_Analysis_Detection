"""Customer Portal: login -> order form -> fraud evaluation -> confirmation."""
import sys
from datetime import datetime
from pathlib import Path
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


@st.dialog("Confirm Place Order")
def confirm_place_order(payload: dict, customer_session_key: str = "customer"):
    st.markdown("### Order Summary — Metro Cart")
    # Show a compact summary
    st.write(f"**Customer:** {payload.get('customer_name')} — **Email:** {payload.get('email')}")
    st.write(f"**Product:** {payload.get('product_name')} x{payload.get('quantity')} — **Amount:** ₹{payload.get('amount'):,.2f}")
    st.write(f"**Delivery Address:** {payload.get('address')}")
    st.write(f"**IP:** {payload.get('ip_address')} — **Device:** {payload.get('device_id')}")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Complete Purchase", type="primary", use_container_width=True):
            with st.spinner("Completing your purchase..."):
                resp = _send_api_request("post", "create-order", json=payload)
            if not resp:
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
            time.sleep(0.5)
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
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
    st.title("🛒 Metro Cart")
    st.subheader("Customer Login")
    
    with st.form("customer_login"):
        user_id = st.text_input("User ID", placeholder="e.g. U1001")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        with get_cursor() as (conn, cur):
            customer = authenticate_customer(cur, user_id, password)
        if customer:
            st.session_state.customer = customer
            st.rerun()
        else:
            st.error("Invalid user ID or password. Please try again.")


def _order_form():
    customer = st.session_state.customer
    
    col_header, col_logout = st.columns([0.85, 0.15])
    with col_header:
        st.title("🛒 Metro Cart")
        st.subheader(f"Welcome back, {customer['customer_name']}!")
    with col_logout:
        if st.button("Log Out", key="customer_logout", use_container_width=True):
            del st.session_state.customer
            st.rerun()

    # Load cached static options
    products, programs, devices = fetch_form_options()

    product_options = {f"{name} — ₹{price:,.2f}": (pid, name, cat, price) for pid, name, cat, price in products}
    program_options = {f"{pid} — {name}": pid for pid, name in programs}
    device_options = {f"{did} — {name}": did for did, name, dtype in devices}

    st.divider()
    st.markdown("#### 👤 Contact Details")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name", value=customer["customer_name"])
        email = st.text_input("Email", value=customer["email"])
    with col2:
        phone = st.text_input("Phone", value=customer["phone_number"] or "")

    st.divider()
    st.markdown("#### 📍 Delivery Address")
    
    col_addr1, col_addr2 = st.columns(2)
    with col_addr1:
        street = st.text_input("Street", value=customer.get("street") or "", placeholder="e.g. 21 MG Road")
        city = st.text_input("City", value=customer.get("city") or "", placeholder="e.g. Bengaluru")
    with col_addr2:
        state = st.text_input("State", value=customer.get("state") or "", placeholder="e.g. Karnataka")
        zip_code = st.text_input("ZIP Code", value=customer.get("zip_code") or "", placeholder="e.g. 560001")
        
    country = st.text_input("Country", value=customer.get("country") or "India")

    st.divider()
    st.markdown("#### ⚙️ E-Commerce Demo Simulation Fields")
    st.caption("IP address, program track, and device are entered manually for testing purposes.")
    col3, col4, col5 = st.columns(3)
    with col3:
        ip_address = st.text_input("IP Address", placeholder="e.g. 203.0.113.111")
    with col4:
        program_label = st.selectbox(
            "Program Track",
            list(program_options.keys()),
            index=list(program_options.values()).index(customer["program_id"])
            if customer["program_id"] in program_options.values()
            else 0,
        )
        program_id = program_options[program_label]
    with col5:
        device_label = st.selectbox("Device", list(device_options.keys()))
        device_id = device_options[device_label]

    st.divider()
    st.markdown("#### 🛍️ Product Selection")
    product_label = st.selectbox("Product", list(product_options.keys()))
    product_id, product_name, category, price = product_options[product_label]
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    total = calculate_total(price, quantity)
    with st.container(border=True):
        st.metric("Total Price", f"₹{total:,.2f}")

    if st.button("Complete Purchase", type="primary", use_container_width=True):
        errors = []
        if not name.strip():
            errors.append("Name is required.")
        if not email.strip() or "@" not in email:
            errors.append("A valid email is required.")
        
        if not street.strip() or not city.strip() or not state.strip() or not zip_code.strip():
            errors.append("Complete delivery address (Street, City, State, and ZIP Code) is required.")
            
        if not ip_address.strip():
            errors.append("Please enter an IP address.")
            
        if errors:
            for err in errors:
                st.error(err)
            return

        with st.spinner("Processing your Metro Cart purchase..."):
            order_timestamp = datetime.now()
            
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
                        "email": email.strip(),
                        "address": formatted_address,
                        "order_timestamp": order_timestamp,
                    }

                    # Evaluate using both the cursor and the context
                    disposition = evaluate_order(cur, ctx)
                
                # Calculate approval and rejection timestamps based on fraud status
                order_approved_at = None if disposition["is_fraud"] else order_timestamp
                order_rejected_at = order_timestamp if disposition["is_fraud"] else None

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
                confirm_place_order(payload)
                
                # Update local session state so the UI remembers the user's updated information
                st.session_state.customer["customer_name"] = name.strip()
                st.session_state.customer["email"] = email.strip()
                st.session_state.customer["phone_number"] = phone.strip()
                st.session_state.customer["street"] = street.strip()
                st.session_state.customer["city"] = city.strip()
                st.session_state.customer["state"] = state.strip()
                st.session_state.customer["zip_code"] = zip_code.strip()
                st.session_state.customer["country"] = country.strip()

                st.session_state.last_order_id = order_id
                time.sleep(0.5)  # Slight pause for UX polish
                st.rerun()

            except requests.exceptions.RequestException:
                st.error("API connection failed or timed out. Please ensure the backend server is running and try again.")


def render():
    if "customer" not in st.session_state:
        _login_form()
        return

    if "last_order_id" in st.session_state:
        st.title("🛒 Metro Cart")
        with st.container(border=True):
            st.success("🎉 Order placed successfully. Thank you for shopping at Metro Cart!")
            st.metric("Your Order ID", st.session_state.last_order_id)
        if st.button("Place Another Order", type="primary", use_container_width=True):
            del st.session_state.last_order_id
            st.rerun()
        return

    _order_form()