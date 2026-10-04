# Data Processing Tool (`data-automation-demo`)

A solid, deterministic Python web application and data pipeline designed for automated cleaning, validation, and normalization of business CSV and Excel (`.xlsx`) datasets.

Built as an empirical demonstration of Python automation, data processing, and backend engineering capabilities for enterprise and freelance engagements.

---

## Capabilities & Architecture

The application adheres to conservative, auditable data engineering principles: it never modifies data without verifiable rules and provides an audit log detailing all applied transformations.

### Core Processing Operations

1. **Format-Aware Ingestion**: Handles both delimited text (`.csv` with automatic encoding and separator detection) and Excel workbooks (`.xlsx` via openpyxl).
2. **Structure Cleanup**:
   - Removes completely empty rows (including rows containing only whitespace characters).
   - Detects and drops completely empty columns.
   - Cleans leading and trailing whitespace from column headers.
3. **Text Normalization**:
   - Strips leading and trailing whitespace across all string cells.
   - Collapses repeated internal whitespace tabs and spaces.
   - Pragmatically normalizes proper names (Title Case for all-caps or all-lowercase entries while preserving mixed-case identifiers).
4. **Email Address Hygiene**:
   - Automatically detects email columns based on naming convention or content heuristic.
   - Normalizes email addresses to lowercase.
   - Validates syntax using standard RFC 5322 regex pattern; invalid emails are flagged with row numbers for review without data loss.
5. **Financial & Numeric Normalization**:
   - Parses currency symbols (`$`, `€`, `£`, `¥`), thousand separators, and decimal notation (both US format `1,250.50` and European format `1.250,50`).
   - Standardizes numeric strings into clean float/integer representations.
   - Flags unparseable strings as warnings.
6. **Deduplication**:
   - Executes exact row deduplication across normalized datasets, safely discarding redundant records while retaining the first occurrence.
7. **Security & CSV Injection Neutralization**:
   - Guards against CSV Formula Injection (DDE attacks): prepends a single quote `'` to string cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` unless they are legitimate scalar numbers or international phone numbers.
   - Enforces upload file size constraints (15 MB maximum).
   - Enforces strict file extension whitelisting (`.csv`, `.xlsx`).
   - Uses UUID4-scoped storage tokens for secure file retrieval, preventing path traversal attacks.

---

## Project Structure

```text
data-automation-demo/
├── app/
│   ├── __init__.py
│   ├── config.py             # System paths, upload limits, retention TTL
│   ├── main.py               # FastAPI router, middleware, and static mounting
│   ├── models.py             # Pydantic data contracts (metrics, results, status)
│   ├── processor.py          # Deterministic data transformation engine
│   ├── security.py           # Filename verification, UUID validation, formula escaping
│   ├── storage.py            # Temporary artifact persistence and session cleanup
│   └── static/
│       ├── css/
│       │   └── style.css     # Clean B2B internal interface stylesheet
│       ├── js/
│       │   └── app.js        # Vanilla JS client (drag & drop, upload, audit rendering)
│       └── index.html        # Semantic single-page application UI
├── demo_data/
│   ├── generate_demo_data.py # Reproducible messy dataset generator
│   ├── customers_messy.csv   # Generated sample CSV dataset
│   └── customers_messy.xlsx  # Generated sample Excel dataset
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures and binary dataset buffers
│   ├── test_api.py           # Integration tests for FastAPI endpoints & HTTP error codes
│   ├── test_processor.py     # Unit tests for data cleaning logic and edge cases
│   └── test_security.py      # Unit tests for security sanitization and limits
├── Dockerfile                # Multi-stage/non-root production container
├── docker-compose.yml        # Docker compose definition
├── pytest.ini                # Pytest configuration
├── requirements.txt          # Python dependencies
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Local Setup & Execution

### 1. Requirements
- Python 3.12+
- `pip` or virtualenv

### 2. Installation
```bash
# Navigate to the project root
cd /home/ubuntu/fiverr_demo/data-automation-demo

# Create and activate virtual environment (if not already active)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Generate Demo Data
Generate the sample datasets (`customers_messy.csv` and `customers_messy.xlsx`):
```bash
python demo_data/generate_demo_data.py
```

### 4. Run the Application
Start the Uvicorn server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access the application:
- Web Interface: [http://localhost:8000/](http://localhost:8000/)
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## Running with Docker

### 1. Build and Run via Docker Compose
```bash
docker compose up --build -d
```

### 2. Build and Run via Docker CLI directly
```bash
docker build -t data-automation-demo:latest .
docker run -d --name data_automation_demo -p 8000:8000 data-automation-demo:latest
```

Check logs and health status:
```bash
docker logs data_automation_demo
docker inspect --format='{{json .State.Health}}' data_automation_demo
```

Stop container:
```bash
docker stop data_automation_demo
```

---

## Running the Automated Test Suite

The test suite validates data transformation accuracy, edge cases (empty files, corrupt headers, null bytes), security safeguards, and HTTP API response codes:

```bash
pytest -v
```

Expected output:
```text
31 passed in ~0.45s
```

Test coverage includes:
- Valid CSV and Excel processing end-to-end
- Actual generated demo data verification
- Empty row and column elimination
- Exact duplicate removal
- Email lowercasing and invalid format warnings
- Currency symbol parsing and international number formats
- CSV formula injection escaping
- File size boundary enforcement (HTTP 413)
- Unsupported format rejection (HTTP 400)
- Corrupt binary / null byte file handling (HTTP 400)
- UUID verification and path traversal prevention (HTTP 400 / HTTP 404)

---

## API Reference

### `GET /api/health`
Health and service availability check.
- **Response**: `200 OK`
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
- **Response**: `200 OK` with JSON payload containing:
  - `file_id`: Session UUID for file downloads
  - `metrics`: Row counts, removed items, normalized cells, and execution time
  - `changes_summary`: Audit list of all transformations applied
  - `warnings`: Detailed list of flagged records (row number, field, issue)
  - `columns`: Array of output column names
  - `sample_preview`: First 10 cleaned rows
  - `csv_download_url`: `/api/download/{file_id}/csv`
  - `xlsx_download_url`: `/api/download/{file_id}/xlsx`
- **Error Codes**:
  - `400 Bad Request`: Empty file, corrupt structure, unsupported extension.
  - `413 Content Too Large`: File exceeds 15 MB limit.
  - `500 Internal Server Error`: Unexpected runtime failure.

### `GET /api/download/{file_id}/{format}`
Downloads the processed dataset in the requested format (`csv` or `xlsx`).
- **Path Parameters**:
  - `file_id`: Valid UUID generated during processing.
  - `format`: `csv` or `xlsx`.
- **Response**: Streamed attachment with appropriate `Content-Disposition`.
- **Error Codes**:
  - `400 Bad Request`: Invalid UUID or unapproved format.
  - `404 Not Found`: Expired or non-existent file.

---

## Known Limitations & Design Decisions

1. **Stateless In-Memory & Local Temporary Storage**: Processed datasets are cached in a temporary directory with a default TTL of 1 hour. This design avoids external database dependencies while remaining fully deterministic and isolated.
2. **Conservative Data Mutability**: When an email or numeric string is malformed beyond safe interpretation, the system preserves the original value and raises an auditable warning rather than silently discarding or fabricating data.
3. **Single Sheet Excel Processing**: By design, Excel processing targets the active (first) worksheet. Multi-sheet consolidation can be added as a custom extension for client-specific requirements.
