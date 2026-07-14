# Architecture

## Overview

A single FastAPI process serves one static page and one processing endpoint.
All domain logic lives in plain Python modules with no web dependencies, so a
CLI or watched-folder frontend could be added without touching the pipeline.

## Request flow

```
Browser (PC webcam / phone camera / file picker)
    │  POST /api/receipts (multipart image)
    ▼
app.py ──► image_prep.normalize_to_jpeg()     EXIF rotate, ≤2000px, JPEG re-encode
    │
    ├────► extractor.extract_receipt()        Claude vision (claude-opus-4-8),
    │                                         structured outputs → ReceiptExtraction
    │
    ├────► storage.archive_image()            data/archive/YYYY/MM/<date>-<vendor>-<id>.jpg
    │
    ├────► validator.build_expense_row()      required fields, date/amount sanity,
    │                                         category whitelist → OK / NEEDS REVIEW
    │
    └────► storage.append_expense_row()       openpyxl append to data/expenses.xlsx
    │
    ▼
JSON response → page shows the row, resets for the next receipt
```

## Module responsibilities

| Module | Responsibility | Knows about |
|---|---|---|
| `config.py` | Settings from `.env` (pydantic-settings) | nothing else |
| `models.py` | `ReceiptExtraction` (model output schema), `ExpenseRow` | nothing else |
| `image_prep.py` | Photo normalization (Pillow) | models: none |
| `extractor.py` | Anthropic API call, prompt, error mapping | models, image_prep |
| `validator.py` | Business rules, NEEDS REVIEW decision | models |
| `storage.py` | Excel append, image archiving | models |
| `app.py` | HTTP wiring, error → status-code mapping | everything above |

## Key decisions

- **Structured outputs, not prompt-and-parse.** `client.messages.parse()` with a
  Pydantic schema guarantees valid JSON; no regex parsing of model text.
- **Extraction fields are nullable.** The system prompt forbids inventing values;
  validation converts nulls into a `NEEDS REVIEW` flag rather than fake data.
- **Archive before validate.** Even a hopeless extraction leaves an archived
  photo referenced from the flagged row, so nothing is lost.
- **Errors are typed at every boundary.** SDK exceptions → `ExtractionError`
  (with `retryable`) → HTTP 502/503; Excel `PermissionError` (file open in
  Excel) → HTTP 409 with a human-readable message.

## Testing strategy

Pure logic (validator, storage, image_prep) is tested directly with `tmp_path`
fixtures and generated PIL images. The API is tested with FastAPI's
`TestClient` and the extractor monkeypatched — the suite needs no network and
no API key. The extractor itself is a thin, injectable wrapper around the SDK.
