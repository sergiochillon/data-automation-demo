# Data Processing Tool (`data-automation-demo`)

> A deterministic Python pipeline and REST API for automated cleaning, validation, and normalization of business CSV and Excel (`.xlsx`) datasets.

[![CI Pipeline](https://github.com/your-username/data-automation-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/data-automation-demo/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![pandas](https://img.shields.io/badge/pandas-2.2+-150458.svg)](https://pandas.pydata.org)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. What is this project?

In real-world business environments, spreadsheets exported from CRM platforms, ERPs, accounting software, and web scrapers often arrive corrupted with data-quality issues:

- Inconsistent uppercase/lowercase names and email addresses.
- Redundant spaces, trailing tabs, and blank lines.
- International currency and decimal notation clashes (e.g., European `1.250,50` vs. US `1,250.50`).
- Completely blank rows and columns created by human data-entry or system exports.
- Exact duplicate records skewing reporting and downstream automations.
- CSV Formula Injection vulnerabilities (DDE attacks) that execute code when opened in Excel.

**Data Processing Tool** is a lightweight, auditable data engineering tool designed to ingest messy CSV and Excel files, execute deterministic cleaning operations, flag unrecoverable issues without silent data corruption, and export sanitized production-ready files alongside a complete audit log.

---

## 2. Visual Architecture & Pipeline Flow

The transformation engine operates sequentially with strict synchronization barriers:

```
┌─────────────────────────┐
│     RAW INPUT DATA      │
│  - Messy CSV / .xlsx    │
│  - Varying encodings    │
│  - Semicolon/Tab/Comma  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                   PYTHON CLEANING ENGINE                    │
│                                                             │
│  1. Format & Encoding Sniffing (UTF-8, UTF-8-SIG, Latin-1)  │
│  2. Structural Pruning (Drop blank rows & blank columns)    │
│  3. Text Normalization (Strip/collapse internal whitespace) │
│  4. Formula Injection Neutralization (OWASP single-quote)   │
│  5. Domain Validation:                                      │
│     - Email lowercasing & RFC 5322 regex validation         │
│     - Proper name title-casing (preserves mixed-case)       │
│     - Financial currency standardizing (US, EU, accounting) │
│  6. Exact Deduplication (First-occurrence retention)        │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│    CLEAN DELIVERABLE    │
│  - Cleaned CSV (.csv)   │
│  - Cleaned Excel (.xlsx)│
│  - Quantitative Metrics │
│  - Itemized Audit Trail │
└─────────────────────────┘
```

---

## 3. Portfolio Visuals

The project includes pre-built presentation materials for portfolio demonstration and client previews:

| Pipeline Architecture (`pipeline.png`) | Transformation Before & After (`before-after.png`) |
| :---: | :---: |
| ![Pipeline Architecture](pipeline.png) | ![Before After Transformation](before-after.png) |
| *Visual overview of Input, Python Processing Engine, and Clean Outputs.* | *Side-by-side record comparison from the real demo dataset.* |

---

## 4. Real Example from Demo Data

The repository includes a synthetic yet realistic business dataset (`demo_data/customers_messy.csv`) containing 31 rows with deliberate quality defects.

### Input Sample (`customers_messy.csv`)
```csv
customer_id,name,email,city,country,phone,revenue,status,notes_internal
CUST-1002,Helios Solar Solutions,info@heliossolar.de,Munich,Germany,+49-89-555-0199,€ 8.920,00,Active,
,,,,,,,,
CUST-1003,  Apex   Industrial Supplies  ,   orders@apexsupplies.co.uk  ,Manchester,United Kingdom,+44-161-555-0177, 18,200.50 ,Pending,
CUST-1004,NORDIC DATA LABS,SUPPORT@NORDICDATALABS.SE,Stockholm,Sweden,+46-8-555-0182,45000,Active,
CUST-1004,NORDIC DATA LABS,SUPPORT@NORDICDATALABS.SE,Stockholm,Sweden,+46-8-555-0182,45000,Active,
CUST-1005,Meridian Maritime Inc,maritime_sales_at_meridian.com,Rotterdam,Netherlands,+31-10-555-0124,€ 24.150,00,Active,
CUST-1012,=SUM(A1:A50),finance@riskycorp.com,Dublin,Ireland,+353-1-555-0189,$15,000.00,Review,
CUST-1020,Beacon Pharma Labs,procurement@beaconpharma.com,Boston,United States,+1-617-555-0193,UNKNOWN_PENDING,Under Review,
```

### Result After Processing
- **Empty Rows**: 3 completely blank rows dropped.
- **Empty Columns**: 1 completely blank column (`notes_internal`) dropped.
- **Deduplication**: 3 exact duplicates dropped (e.g., redundant row for `CUST-1004`).
- **Whitespace Collapsed**: `"  Apex   Industrial Supplies  "` &rarr; `"Apex Industrial Supplies"`.
- **Casing Normalized**: `"NORDIC DATA LABS"` &rarr; `"Nordic Data Labs"`; `"SUPPORT@NORDICDATALABS.SE"` &rarr; `"support@nordicdatalabs.se"`.
- **Currency Standardized**: `"€ 8.920,00"` &rarr; `8920.0`; `" 18,200.50 "` &rarr; `18200.5`.
- **Formula Injection Sanitized**: `"=SUM(A1:A50)"` &rarr; `'=SUM(A1:A50)`.
- **Quality Warning Logged**: Row 7 (`maritime_sales_at_meridian.com`) flagged as invalid email; Row 20 (`UNKNOWN_PENDING`) flagged as non-numeric while preserving the original string.
- **Final Output**: Exactly 25 clean rows ready for production database import or BI reporting.

---

## 5. Key Capabilities & Technical Features

### 1. Robust File Ingestion
- Ingests delimited files (`.csv`) and modern Excel spreadsheets (`.xlsx`).
- Automatic text encoding detection with fallbacks: `UTF-8`, `UTF-8 with BOM` (`utf-8-sig`), `Latin-1` (`ISO-8859-1`), and `Windows CP1252`.
- Delimiter sniffing handling comma (`,`), semicolon (`;`), tab (`\t`), and pipe (`|`).
- Binary file detection (rejects null-byte payload injections).

### 2. Structural Pruning & Deduplication
- Drops rows that contain only NaN values or whitespace strings.
- Detects and prunes columns containing no informational value.
- Cleans whitespace from header column names.
- Executes deterministic exact row deduplication (retaining first occurrence).

### 3. Smart Domain Cleaning
- **Emails**: Strips spaces, normalizes to lowercase, and validates against RFC 5322 regex.
- **Names**: Normalizes all-caps or all-lowercase entries to Title Case while respecting mixed-case names (e.g., `McDonald`, `van der Waals`, `O'Connor`).
- **Currency & Numbers**: Parses currency symbols (`$`, `€`, `£`, `¥`), US notation (`1,250.50`), European notation (`1.250,50`), and negative accounting notation (`($1,250.00)` or `-$1,250.00`).
- **Conservative Mutation Strategy**: If a value cannot be parsed unambiguously (e.g., `PENDING_PAYMENT` in a revenue column), it is retained and flagged in the audit warnings rather than silently deleted or replaced with zero.

### 4. Enterprise Security Guardrails
- **CSV Formula Injection (DDE)**: Cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are neutralized with a leading single quote (`'`), excluding legitimate numbers and international phone numbers.
- **Path Traversal Defense**: Filenames are sanitized, and all disk retrievals verify that the resolved path stays within the base storage directory.
- **Streaming Upload Guard**: Uploads are read in bounded 1 MB chunks to prevent memory exhaustion (DoS), enforcing a 15 MB maximum payload.
- **Session Isolation**: Download artifacts are addressed via non-sequential UUID4 tokens.

---

## 6. Technical Stack & Rationale

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Runtime** | Python 3.12+ | Modern typing (`list[T]`, `X \| Y`), high performance, robust standard library. |
| **API Framework** | FastAPI + Uvicorn | High-throughput asynchronous routing, automatic OpenAPI/Swagger documentation, strict request validation via Pydantic v2. |
| **Data Engine** | pandas + openpyxl | Industry-standard vectorized processing, reliable CSV parsing, full `.xlsx` workbook manipulation. |
| **Validation** | Pydantic v2 | Strict serialization and typing for quantitative metrics, audit results, and health checks. |
| **Frontend** | Vanilla JS, HTML5, CSS3 | Zero build step, no npm/node dependency overhead, fast browser rendering, clean B2B layout. |
| **Quality & Linting** | Ruff + Pytest | Blazing-fast linting and code formatting; 40+ unit and integration tests covering edge cases. |
| **Containerization** | Docker + Compose | Multi-stage, non-root user (`appuser`), internal Python healthcheck, reproducible deployment. |

---

## 7. Project Structure

```text
data-automation-demo/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow (Ruff + Pytest)
├── app/
│   ├── __init__.py
│   ├── config.py                # Environment settings, limits, and logging
│   ├── main.py                  # FastAPI application, routing, and lifecycle
│   ├── models.py                # Pydantic schemas (metrics, processing results)
│   ├── processor.py             # Deterministic data cleaning and validation engine
│   ├── security.py              # Formula injection escaping, UUID, filename validation
│   ├── storage.py               # Temporary artifact persistence and session cleanup
│   └── static/
│       ├── css/
│       │   └── style.css        # Clean B2B interface styling
│       ├── js/
│       │   └── app.js           # Vanilla JavaScript UI controller
│       └── index.html           # Single-page application interface
├── demo_data/
│   ├── generate_demo_data.py    # Reproducible dataset generator script
│   ├── customers_messy.csv      # Sample messy CSV dataset
│   └── customers_messy.xlsx     # Sample messy Excel dataset
├── storage/
│   └── processed/               # Local artifact directory (gitignored)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and mock file generators
│   ├── test_api.py              # End-to-end API integration tests
│   ├── test_processor.py        # Transformation and encoding unit tests
│   ├── test_security.py         # Security sanitization and boundary tests
│   └── test_storage.py          # Storage manager and expiration cleanup tests
├── Dockerfile                   # Hardened non-root production container
├── docker-compose.yml           # Compose configuration
├── pyproject.toml               # Project metadata, Ruff rules, and dependencies
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Pinned production dependencies
├── LICENSE                      # MIT License
├── pipeline.png                 # Portfolio architecture visual
├── before-after.png             # Portfolio data comparison visual
└── README.md
```

---

## 8. Local Setup & Execution

### Prerequisites
- Python 3.12 or higher
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/data-automation-demo.git
cd data-automation-demo

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser:
- Web Interface: [http://localhost:8000/](http://localhost:8000/)
- OpenAPI Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 9. Running with Docker

### Using Docker Compose (Recommended)
```bash
docker compose up --build -d
```

### Using Docker CLI Directly
```bash
# Build image
docker build -t data-automation-demo:latest .

# Run container
docker run -d \
  --name data_automation_demo \
  -p 8000:8000 \
  -e MAX_UPLOAD_SIZE_MB=15 \
  -e STORAGE_RETENTION_SECONDS=3600 \
  data-automation-demo:latest
```

Verify container status:
```bash
docker ps
docker inspect --format='{{json .State.Health}}' data_automation_demo
```

---

## 10. Automated Testing & Code Quality

The project enforces strict code quality and testing standards:

```bash
# 1. Check linting and formatting with Ruff
ruff check .
ruff format --check .

# 2. Run automated test suite
pytest -v
```

Expected output:
```text
============================== 41 passed in ~0.55s ==============================
```

Test coverage includes:
- Delimiter sniffing (comma, semicolon, tab, pipe).
- Multi-encoding ingestion (UTF-8, UTF-8-SIG BOM, Latin-1/ISO-8859-1).
- Empty row and column elimination.
- Exact deduplication.
- Email hygiene and RFC 5322 validation.
- International currency and negative accounting notation parsing.
- Proper name casing while preserving mixed-case identifiers.
- CSV Formula Injection (DDE) sanitization.
- Upload size limits (HTTP 413) and invalid extension rejection (HTTP 400).
- Path traversal prevention and UUID validation.
- Storage lifecycle expiration pruning.

---

## 11. API Reference

### `GET /api/health`
Checks service health and availability.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "data-automation-demo"
}
```

### `POST /api/process`
Uploads and processes a `.csv` or `.xlsx` file (max 15 MB).
- **Request**: `multipart/form-data` with `file` field.
- **Response `200 OK`**:
```json
{
  "file_id": "4b6c3182-1a22-4fe1-9257-8df7d9b93be9",
  "original_filename": "customers_messy.csv",
  "processed_at": "2026-10-04T20:25:00.000000Z",
  "metrics": {
    "rows_initial": 31,
    "rows_final": 25,
    "rows_removed_empty": 3,
    "columns_removed_empty": 1,
    "duplicate_rows_removed": 3,
    "invalid_emails_count": 2,
    "invalid_values_detected": 3,
    "fields_normalized": 42,
    "null_values_count": 5,
    "processing_time_ms": 12.4
  },
  "changes_summary": [
    "Trimmed whitespace from column headers",
    "Removed 1 completely empty column(s): notes_internal",
    "Removed 3 completely empty row(s)",
    "Cleaned whitespace across 18 text cell(s)",
    "Sanitized 2 cell(s) starting with formula characters",
    "Normalized 8 email address(es) to lowercase in 'email'",
    "Normalized casing for 7 name(s) in 'name'",
    "Normalized 14 currency/numeric value(s) in 'revenue'",
    "Removed 3 exact duplicate row(s)"
  ],
  "warnings": [
    "Row 7: Potentially invalid email 'maritime_sales_at_meridian.com' in column 'email'",
    "Row 20: Unrecognized numeric format 'UNKNOWN_PENDING' in column 'revenue'"
  ],
  "columns": ["customer_id", "name", "email", "city", "country", "phone", "revenue", "status"],
  "sample_preview": [...],
  "csv_download_url": "/api/download/4b6c3182-1a22-4fe1-9257-8df7d9b93be9/csv",
  "xlsx_download_url": "/api/download/4b6c3182-1a22-4fe1-9257-8df7d9b93be9/xlsx"
}
```

### `GET /api/download/{file_id}/{format}`
Streams the sanitized dataset in `csv` or `xlsx` format.
- **Parameters**: `file_id` (UUID), `format` (`csv` | `xlsx`).
- **Response `200 OK`**: File attachment with appropriate MIME type.

---

## 12. Design Decisions & Trade-offs

1. **Stateless Local Cache over Database**:
   - Files are stored in a dedicated UUID-partitioned directory with a 1-hour expiration TTL. This eliminates external database dependencies (PostgreSQL/Redis), making the application completely self-contained and zero-maintenance while ensuring data privacy.
2. **Conservative Transformation Strategy**:
   - Malformed data that cannot be parsed unambiguously (e.g. `UNKNOWN_PENDING` in a revenue column) is never discarded or replaced with dummy defaults. It is preserved and reported in the `warnings` audit list so domain experts can make informed decisions.
3. **Vanilla Frontend**:
   - Built with semantic HTML, modern CSS flexbox/grid, and vanilla JavaScript. Eliminating frontend build frameworks (React, Webpack, npm) simplifies continuous deployment and eliminates JavaScript supply-chain vulnerabilities.

---

## 13. Limitations & Roadmap

- **Single-Sheet Processing**: Current Excel processing targets the active (first) sheet. Multi-tab consolidation can be added as a custom requirement.
- **Large Dataset Threshold**: Because files are processed in-memory via pandas DataFrames, the tool is optimized for files up to ~100 MB. For multi-gigabyte files, chunked streaming via Polars or Dask would be recommended.
- **Rule Customization**: Normalization rules (e.g., specific currency formats or date patterns) are currently applied based on standard business heuristics. Future versions could expose configurable rule profiles via JSON configuration.

---

## 14. License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
