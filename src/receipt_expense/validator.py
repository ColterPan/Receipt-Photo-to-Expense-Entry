"""Validate an extraction and decide whether it needs human review."""

import logging
from datetime import date, datetime, timedelta

from .models import ExpenseRow, ReceiptExtraction

logger = logging.getLogger(__name__)

MAX_FUTURE_DAYS = 1  # a receipt dated tomorrow (timezone skew) is fine; next month is not
MAX_AGE_YEARS = 10


def build_expense_row(
    extraction: ReceiptExtraction,
    categories: list[str],
    image_path: str,
    now: datetime | None = None,
) -> ExpenseRow:
    """Turn a raw extraction into a row, flagging anything suspect as NEEDS REVIEW.

    The row is always written — a flagged row with the archived photo beats a
    silently dropped expense — but amounts are never guessed or defaulted.
    """
    now = now or datetime.now()
    problems: list[str] = []

    vendor = (extraction.vendor or "").strip()
    if not vendor:
        vendor = "UNKNOWN"
        problems.append("vendor not readable")

    if extraction.amount is None:
        problems.append("amount not readable")
    elif extraction.amount <= 0:
        problems.append(f"amount is not positive ({extraction.amount})")

    currency = (extraction.currency or "").strip().upper()
    if not currency:
        currency = "?"
        problems.append("currency not determinable")

    parsed_date = _parse_iso_date(extraction.date)
    if parsed_date is None:
        row_date = ""
        problems.append("date missing or not a valid YYYY-MM-DD")
    else:
        row_date = parsed_date.isoformat()
        if parsed_date > now.date() + timedelta(days=MAX_FUTURE_DAYS):
            problems.append(f"date {row_date} is in the future")
        elif parsed_date < now.date() - timedelta(days=365 * MAX_AGE_YEARS):
            problems.append(f"date {row_date} is implausibly old")

    category = extraction.category.strip()
    if category not in categories and category != "Uncategorized":
        problems.append(f"category {category!r} is not in the allowed list")
        category = "Uncategorized"

    if extraction.confidence == "low":
        problems.append("model confidence is low")

    needs_review = bool(problems)
    notes = "; ".join(problems)
    if extraction.notes:
        notes = f"{notes}; {extraction.notes}" if notes else extraction.notes

    if needs_review:
        logger.warning("Receipt flagged for review: %s", notes)

    return ExpenseRow(
        date=row_date,
        vendor=vendor,
        amount=extraction.amount,
        currency=currency,
        category=category,
        status="NEEDS REVIEW" if needs_review else "OK",
        notes=notes,
        image_path=image_path,
        processed_at=now,
    )


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
