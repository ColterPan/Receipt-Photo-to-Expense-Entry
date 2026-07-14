from datetime import datetime

from receipt_expense.models import ReceiptExtraction
from receipt_expense.validator import build_expense_row

CATEGORIES = ["Meals", "Travel", "Other"]
NOW = datetime(2026, 7, 14, 12, 0, 0)


def good_extraction(**overrides) -> ReceiptExtraction:
    data = dict(
        vendor="Coffee House",
        amount=12.50,
        currency="USD",
        date="2026-07-10",
        category="Meals",
        confidence="high",
        notes="",
    )
    data.update(overrides)
    return ReceiptExtraction(**data)


def test_clean_extraction_is_ok():
    row = build_expense_row(good_extraction(), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "OK"
    assert row.vendor == "Coffee House"
    assert row.amount == 12.50
    assert row.date == "2026-07-10"
    assert row.notes == ""


def test_missing_amount_flags_review_and_never_defaults():
    row = build_expense_row(good_extraction(amount=None), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "NEEDS REVIEW"
    assert row.amount is None
    assert "amount" in row.notes


def test_negative_amount_flags_review():
    row = build_expense_row(good_extraction(amount=-5), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "NEEDS REVIEW"


def test_missing_vendor_flags_review():
    row = build_expense_row(good_extraction(vendor=None), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "NEEDS REVIEW"
    assert row.vendor == "UNKNOWN"


def test_bad_date_flags_review():
    row = build_expense_row(good_extraction(date="10/07/2026"), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "NEEDS REVIEW"
    assert row.date == ""


def test_future_date_flags_review():
    row = build_expense_row(good_extraction(date="2026-09-01"), CATEGORIES, "img.jpg", now=NOW)
    assert row.status == "NEEDS REVIEW"
    assert "future" in row.notes


def test_unknown_category_becomes_uncategorized_and_flags():
    row = build_expense_row(good_extraction(category="Snacks"), CATEGORIES, "img.jpg", now=NOW)
    assert row.category == "Uncategorized"
    assert row.status == "NEEDS REVIEW"


def test_uncategorized_alone_is_allowed_without_flag():
    extraction = good_extraction(category="Uncategorized")
    row = build_expense_row(extraction, CATEGORIES, "img.jpg", now=NOW)
    assert row.category == "Uncategorized"
    assert row.status == "OK"


def test_low_confidence_flags_review_and_keeps_model_notes():
    row = build_expense_row(
        good_extraction(confidence="low", notes="total partially cut off"),
        CATEGORIES, "img.jpg", now=NOW,
    )
    assert row.status == "NEEDS REVIEW"
    assert "confidence" in row.notes
    assert "cut off" in row.notes
