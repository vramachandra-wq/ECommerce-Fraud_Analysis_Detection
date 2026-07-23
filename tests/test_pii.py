from utils.pii import (
    can_view_full_pii,
    mask_email,
    mask_phone,
    mask_address,
    mask_street,
    mask_ip,
    display_pii,
)


def test_can_view_full_pii_roles():
    assert can_view_full_pii({"role": "Admin"}) is True
    assert can_view_full_pii({"role": "Senior Fraud Analyst"}) is False
    assert can_view_full_pii({"role": "Fraud Analyst"}) is False
    assert can_view_full_pii(None) is False
    assert can_view_full_pii({}) is False


def test_mask_email():
    assert mask_email("ermani12@gmail.com") == "er******@gmail.com"
    assert mask_email("john@example.com") == "jo**@example.com"
    assert mask_email("rahul.mehta@example.com") == "ra*********@example.com"
    assert mask_email("er@x.com") == "e*@x.com"
    assert mask_email("a@x.com") == "*@x.com"
    assert mask_email("not-an-email") == "not-an-email"
    assert mask_email("") == ""


def test_mask_phone():
    assert mask_phone("9198765452") == "91******52"
    assert mask_phone("9876543210") == "98******10"
    assert mask_phone("1234") == "***"
    assert mask_phone("") == ""


def test_mask_street():
    assert mask_street("21 MG Road") == "21********"
    assert mask_street("AB") == "**"
    assert mask_street("A") == "*"
    assert mask_street("") == ""


def test_mask_address():
    assert (
        mask_address("21 MG Road, Bengaluru, Karnataka 560001")
        == "21********, Bengaluru, Karnataka 560001"
    )
    assert mask_address("12 Main Street Chennai") == "12********************"
    assert mask_address("Short") == "Sh***"
    assert mask_address("") == ""


def test_mask_ip():
    assert mask_ip("192.168.1.100") == "192.168.***.***"
    assert mask_ip("bad") == "***"
    assert mask_ip("") == ""


def test_display_pii_full_for_admin():
    analyst = {"role": "Admin"}
    assert display_pii("rahul.mehta@example.com", field="email", analyst=analyst) == (
        "rahul.mehta@example.com"
    )
    assert display_pii("9876543210", field="phone", analyst=analyst) == "9876543210"
    assert (
        display_pii(
            "21 MG Road, Bengaluru, Karnataka 560001",
            field="address",
            analyst=analyst,
        )
        == "21 MG Road, Bengaluru, Karnataka 560001"
    )
    assert display_pii("192.168.1.100", field="ip", analyst=analyst) == "192.168.1.100"


def test_display_pii_masked_for_non_admin():
    for role in ("Senior Fraud Analyst", "Fraud Analyst"):
        analyst = {"role": role}
        assert display_pii("rahul.mehta@example.com", field="email", analyst=analyst) == (
            "ra*********@example.com"
        )
        assert display_pii("9876543210", field="phone", analyst=analyst) == "98******10"
        assert (
            display_pii(
                "21 MG Road, Bengaluru, Karnataka 560001",
                field="address",
                analyst=analyst,
            )
            == "21********, Bengaluru, Karnataka 560001"
        )
        assert display_pii("21 MG Road", field="street", analyst=analyst) == "21********"
        assert display_pii("192.168.1.100", field="ip", analyst=analyst) == "192.168.***.***"


def test_display_pii_unknown_field_passthrough():
    analyst = {"role": "Fraud Analyst"}
    assert display_pii("raw-value", field="other", analyst=analyst) == "raw-value"


def test_display_pii_empty_value():
    assert display_pii("", field="email", analyst={"role": "Fraud Analyst"}) == ""
    assert display_pii(None, field="email", analyst={"role": "Fraud Analyst"}) == ""
