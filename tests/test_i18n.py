"""Tests for Thai/English i18n reliability."""
from unittest.mock import patch

from ui.i18n import TRANSLATIONS, format_duration_minutes, t, _validate_catalog


def test_every_key_has_en_and_th():
    _validate_catalog()
    # Labels that may legitimately lack Thai script (technical abbreviations)
    allow_no_thai_script = {"label_ip"}
    for key, entry in TRANSLATIONS.items():
        assert entry.get("en", "").strip(), f"{key} missing English"
        assert entry.get("th", "").strip(), f"{key} missing Thai"
        if key in allow_no_thai_script:
            continue
        th = entry["th"]
        has_thai = any("\u0e00" <= ch <= "\u0e7f" for ch in th)
        assert has_thai, f"{key} Thai text has no Thai characters: {th!r}"


def test_t_falls_back_to_english():
    with patch("ui.i18n._lang", return_value="th"):
        assert "ค้างตรวจสอบ" in t("backlog_section") or "ค้าง" in t("backlog_section")
    with patch("ui.i18n._lang", return_value="en"):
        assert "Backlog" in t("backlog_section")


def test_t_unknown_key_returns_key():
    assert t("this_key_does_not_exist_xyz") == "this_key_does_not_exist_xyz"


def test_t_format_kwargs():
    with patch("ui.i18n._lang", return_value="th"):
        text = t("confirm_approve_selected", n=3)
        assert "3" in text
    with patch("ui.i18n._lang", return_value="en"):
        text = t("confirm_approve_selected", n=3)
        assert "3" in text


def test_format_duration_minutes_localized():
    with patch("ui.i18n._lang", return_value="th"):
        assert "นาที" in format_duration_minutes(180)
        assert "วินาที" in format_duration_minutes(0.5)
    with patch("ui.i18n._lang", return_value="en"):
        assert "min" in format_duration_minutes(180)


def test_critical_dialog_keys_present():
    required = [
        "confirm_approve_one",
        "confirm_reject_one",
        "confirm_fraud_one",
        "confirm_approve_all_backlog",
        "confirm_reject_all_backlog",
        "confirm_fraud_all_backlog",
        "no_backlog_message",
        "auto_approved_info",
        "remaining_review",
        "delay_minutes",
    ]
    for key in required:
        assert key in TRANSLATIONS
        with patch("ui.i18n._lang", return_value="th"):
            assert t(key)
