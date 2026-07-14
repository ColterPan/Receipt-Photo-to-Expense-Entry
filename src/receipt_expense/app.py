"""FastAPI application: serves the capture page and processes receipt uploads."""

import logging
import socket
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import extractor, image_prep, storage, validator
from .config import get_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app = FastAPI(title="Receipt Photo to Expense Entry")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/info")
def info() -> dict:
    """Connection info shown on the page (LAN URL for the phone)."""
    settings = get_settings()
    return {
        "lan_url": f"http://{_lan_ip()}:{settings.port}",
        "categories": settings.category_list,
        "expense_file": str(settings.expense_file),
        "api_key_configured": bool(settings.anthropic_api_key),
    }


@app.post("/api/receipts")
async def process_receipt(file: UploadFile) -> dict:
    """Full pipeline: normalize photo -> extract -> validate -> archive -> Excel row."""
    settings = get_settings()
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 20 MB).")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        jpeg_bytes = image_prep.normalize_to_jpeg(raw)
    except image_prep.InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        extraction = extractor.extract_receipt(jpeg_bytes, settings.category_list)
    except extractor.ExtractionError as exc:
        status = 503 if exc.retryable else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    # Archive first so a flagged/failed row can always be traced back to its photo.
    image_path = storage.archive_image(
        jpeg_bytes,
        settings.archive_dir,
        extraction.date or "",
        extraction.vendor or "receipt",
    )

    row = validator.build_expense_row(
        extraction, settings.category_list, image_path=str(image_path)
    )

    try:
        row_number = storage.append_expense_row(row, settings.expense_file)
    except storage.ExpenseFileLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "row_number": row_number,
        "date": row.date,
        "vendor": row.vendor,
        "amount": row.amount,
        "currency": row.currency,
        "category": row.category,
        "status": row.status,
        "notes": row.notes,
        "image_path": row.image_path,
    }


def _lan_ip() -> str:
    """Best-effort LAN IP so the page can show a URL for the phone."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # no packets sent; just selects an interface
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> None:
    """Entry point for `python -m receipt_expense.app` and the launcher scripts."""
    import webbrowser

    import uvicorn

    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning(
            "ANTHROPIC_API_KEY is not set — receipt processing will fail. "
            "Copy .env.example to .env and add your key."
        )
    logger.info("Desktop: http://localhost:%d  |  Phone: http://%s:%d",
                settings.port, _lan_ip(), settings.port)
    webbrowser.open(f"http://localhost:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
