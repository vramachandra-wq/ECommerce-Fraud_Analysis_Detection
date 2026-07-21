"""PII display masking for analyst-facing UI."""
from typing import Any, Dict, Optional


def can_view_full_pii(analyst: Optional[Dict[str, Any]]) -> bool:
    """Admin and Senior Fraud Analyst see full customer PII."""
    role = (analyst or {}).get("role", "")
    return role in ("Admin", "Senior Fraud Analyst")


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    masked_local = local[0] + "***" if local else "***"
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = phone.strip()
    if len(digits) <= 4:
        return "***"
    return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]


def mask_address(address: str) -> str:
    if not address:
        return ""
    if len(address) <= 12:
        return "***"
    return address[:8] + "***"


def mask_ip(ip_address: str) -> str:
    if not ip_address:
        return ""
    parts = ip_address.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return "***"


def display_pii(value: str, *, field: str, analyst: Optional[Dict[str, Any]]) -> str:
    if can_view_full_pii(analyst) or not value:
        return value or ""
    maskers = {
        "email": mask_email,
        "phone": mask_phone,
        "address": mask_address,
        "ip": mask_ip,
    }
    mask_fn = maskers.get(field)
    return mask_fn(value) if mask_fn else value
