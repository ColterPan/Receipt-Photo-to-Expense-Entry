"""Extract structured receipt data from a photo using Claude vision."""

import logging

import anthropic

from .image_prep import MEDIA_TYPE, encode_base64
from .models import ReceiptExtraction

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
You extract expense data from photos of receipts for a finance team.

Rules:
- Extract only what is actually visible on the receipt. Never invent or estimate values.
- amount is the grand total actually paid (including tax). If it is not clearly \
readable, leave it null and say why in notes.
- date must be the transaction date in YYYY-MM-DD. If ambiguous (e.g. 03/04/2026 \
could be March or April), pick the most likely reading, use confidence "low", and \
explain the ambiguity in notes.
- category must be exactly one of the allowed categories, or "Uncategorized" if \
none fits.
- If the photo is blurry, cropped, or otherwise partly unreadable, set confidence \
"low" and describe the problem in notes.

Allowed categories: {categories}
"""


class ExtractionError(RuntimeError):
    """The API call failed or returned nothing usable."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def extract_receipt(
    jpeg_bytes: bytes,
    categories: list[str],
    client: anthropic.Anthropic | None = None,
) -> ReceiptExtraction:
    """Send the receipt photo to Claude and return validated structured data.

    `client` is injectable for testing; by default credentials come from the
    environment (ANTHROPIC_API_KEY).
    """
    client = client or anthropic.Anthropic()

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT.format(categories=", ".join(categories)),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": MEDIA_TYPE,
                                "data": encode_base64(jpeg_bytes),
                            },
                        },
                        {"type": "text", "text": "Extract the expense data from this receipt."},
                    ],
                }
            ],
            output_format=ReceiptExtraction,
        )
    except anthropic.AuthenticationError as exc:
        raise ExtractionError(
            "Anthropic API key is missing or invalid. Set ANTHROPIC_API_KEY in .env."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise ExtractionError(
            "Rate limited by the Anthropic API. Wait a moment and retry.", retryable=True
        ) from exc
    except anthropic.APIStatusError as exc:
        retryable = exc.status_code >= 500
        raise ExtractionError(f"Anthropic API error ({exc.status_code}): {exc.message}",
                              retryable=retryable) from exc
    except anthropic.APIConnectionError as exc:
        raise ExtractionError(
            "Could not reach the Anthropic API. Check your internet connection.", retryable=True
        ) from exc

    if response.stop_reason == "refusal":
        raise ExtractionError("The model declined to process this image.")

    extraction = response.parsed_output
    if extraction is None:
        raise ExtractionError("The model did not return parseable receipt data.")

    logger.info(
        "Extracted receipt: vendor=%r amount=%s date=%s category=%s confidence=%s",
        extraction.vendor, extraction.amount, extraction.date,
        extraction.category, extraction.confidence,
    )
    return extraction
