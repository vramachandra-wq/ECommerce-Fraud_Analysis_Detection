"""PII display masking for UI surfaces (analyst, customer, chatbot)."""
from typing import Any, Dict, Optional


def can_view_full_pii(analyst: Optional[Dict[str, Any]]) -> bool:
    """Only Admin may see full customer PII in the analyst portal."""
    role = (analyst or {}).get("role", "")
    return role == "Admin"


def mask_email(email: str) -> str:
    """Mask local part after the first two characters: er*******@gmail.com."""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Keep first and last two characters: 91******52."""
    if not phone:
        return ""
    digits = str(phone).strip()
    if len(digits) <= 4:
        return "***"
    return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]


def mask_street(street: str) -> str:
    """Mask street like email local part: keep first two chars, star the rest."""
    if not street:
        return ""
    value = street.strip()
    if len(value) <= 2:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 2)


def mask_address(address: str) -> str:
    """Mask the street portion of an address; leave city/state/zip visible."""
    if not address:
        return ""
    value = address.strip()
    if "," in value:
        street, rest = value.split(",", 1)
        return f"{mask_street(street)},{rest}"
    return mask_street(value)


def mask_ip(ip_address: str) -> str:
    if not ip_address:
        return ""
    parts = ip_address.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return "***"


def display_pii(
    value: str,
    *,
    field: str,
    analyst: Optional[Dict[str, Any]] = None,
) -> str:
    """Show full PII for Admin; mask for all other analyst roles."""
    if not value:
        return ""
    if can_view_full_pii(analyst):
        return str(value)
    maskers = {
        "email": mask_email,
        "phone": mask_phone,
        "address": mask_address,
        "street": mask_street,
        "ip": mask_ip,
    }
    mask_fn = maskers.get(field)
    return mask_fn(value) if mask_fn else value
