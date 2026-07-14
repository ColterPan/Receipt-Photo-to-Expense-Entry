"""Data models for extraction results and expense rows."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class ReceiptExtraction(BaseModel):
    """What the vision model extracts from a receipt photo.

    Fields are optional (None) rather than guessed: if the model cannot read a
    value from the image it must leave it null and explain in `notes`.
    """

    vendor: str | None = Field(None, description="Merchant/store name as printed on the receipt")
    amount: float | None = Field(
        None, description="Grand total actually paid, including tax. Null if not clearly visible."
    )
    currency: str | None = Field(
        None, description="ISO 4217 currency code, e.g. USD, SGD, EUR. Null if not determinable."
    )
    date: str | None = Field(
        None, description="Transaction date in ISO format YYYY-MM-DD. Null if not clearly visible."
    )
    category: str = Field(
        "Uncategorized",
        description="One category from the allowed list, or 'Uncategorized' if none fits.",
    )
    confidence: Confidence = Field(
        "low", description="Overall confidence that all extracted fields are correct."
    )
    notes: str = Field(
        "", description="Anything unclear, missing, or worth a human's attention. Empty if none."
    )


class ExpenseRow(BaseModel):
    """A validated row ready to be written to the expense sheet."""

    date: str
    vendor: str
    amount: float | None
    currency: str
    category: str
    status: Literal["OK", "NEEDS REVIEW"]
    notes: str
    image_path: str
    processed_at: datetime
