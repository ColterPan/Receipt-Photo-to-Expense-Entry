# Receipt Photo → Expense Entry

Snap a photo of a receipt — on your PC or phone — and it lands as a row in your
Excel expense sheet, with the original photo archived. A Claude vision model
extracts the vendor, amount, date, and category; anything it can't read
confidently is flagged **NEEDS REVIEW** instead of guessed.

## How it works

```
photo (PC webcam / phone camera / file)
   │
   ▼
Pillow: rotate, downscale, re-encode          src/receipt_expense/image_prep.py
   │
   ▼
Claude vision → structured JSON               src/receipt_expense/extractor.py
   │
   ▼
validation → OK / NEEDS REVIEW                src/receipt_expense/validator.py
   │
   ▼
Excel row + archived photo                    src/receipt_expense/storage.py
```

## Requirements

- Python 3.11+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

## Install & run

**Windows:** double-click `run.bat`.
**macOS/Linux:** `./run.sh`.

The first run creates a virtual environment and installs dependencies. The app
then opens in your browser automatically.

Manual setup, if you prefer:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate elsewhere)
pip install -e ".[dev]"
copy .env.example .env          # then put your ANTHROPIC_API_KEY in .env
python -m receipt_expense.app
```

## Using it

- **On your PC:** click **Use camera** (webcam) or **Choose photo**, snap the
  receipt, then **Process receipt**. The extracted row is shown and the page
  resets for the next receipt — you can work through a whole stack.
- **On your phone:** the page header shows a LAN URL like `http://192.168.x.x:8000`.
  Open it in your phone's browser (same Wi-Fi network) and tap **Choose photo** —
  it opens your camera app directly.
  - Note: the *live webcam* button only works on `http://localhost` (browsers
    require a secure context for camera streams). The phone flow uses the native
    camera app instead, which works fine over plain HTTP. This is a browser
    security rule, not a bug.
- **Output:** rows are appended to `data/expenses.xlsx` (configurable via
  `EXPENSE_FILE` in `.env` — pointing it at an existing workbook is supported;
  an `Expenses` sheet is added if missing). Photos are archived under
  `data/archive/YYYY/MM/` with the path recorded in the row.

Columns: Date, Vendor, Amount, Currency, Category, Status, Notes, Receipt Image, Processed At.

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `EXPENSE_FILE` | `data/expenses.xlsx` | Workbook to append rows to. |
| `ARCHIVE_DIR` | `data/archive` | Where receipt photos are stored. |
| `CATEGORIES` | Meals, Travel, … | Comma-separated allowed categories. |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Server bind address and port. |

## Design notes & limitations

- **Never guesses money.** A missing or unreadable total stays blank and the row
  is flagged `NEEDS REVIEW` — check the archived photo and fill it in by hand.
- **Close the workbook before processing.** Excel locks the file while it's open;
  the app will tell you if it can't save.
- **Single user.** This is a local tool; concurrent writers to the same workbook
  are not supported.
- **Your data stays local.** `data/` and `.env` are gitignored — receipts and
  keys never go to GitHub. Receipt images are sent to the Anthropic API for
  extraction.

## Development

```bash
pip install -e ".[dev]"
pytest          # no API key or network needed — the model call is mocked
ruff check .
```

See [docs/architecture.md](docs/architecture.md) for module responsibilities.

## License

[MIT](LICENSE)
