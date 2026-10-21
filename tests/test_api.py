import uuid
from pathlib import Path


def test_api_health_endpoint(client):
    """Healthcheck endpoint returns 200 and valid service metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data-automation-demo"
    assert "version" in data


def test_serve_index_html(client):
    """Serves the Single Page Application UI with correct headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Data Processing Tool" in response.text


def test_process_valid_csv(client, valid_csv_bytes):
    """Valid CSV is correctly parsed, cleaned, and audited."""
    response = client.post(
        "/api/process",
        files={"file": ("test_dataset.csv", valid_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()

    assert "file_id" in data
    assert data["original_filename"] == "test_dataset.csv"
    assert data["metrics"]["rows_initial"] == 5
    assert data["metrics"]["rows_final"] == 3
    assert data["metrics"]["duplicate_rows_removed"] == 1
    assert data["metrics"]["rows_removed_empty"] == 1
    assert data["metrics"]["invalid_emails_count"] == 1
    assert len(data["sample_preview"]) > 0
    assert data["csv_download_url"].startswith("/api/download/")
    assert data["xlsx_download_url"].startswith("/api/download/")


def test_process_valid_excel(client, valid_xlsx_bytes):
    """Valid Excel workbook is parsed and normalized correctly."""
    excel_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response = client.post(
        "/api/process",
        files={"file": ("test_workbook.xlsx", valid_xlsx_bytes, excel_mime)},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["original_filename"] == "test_workbook.xlsx"
    assert data["metrics"]["rows_initial"] == 4
    assert data["metrics"]["rows_final"] == 2
    assert data["metrics"]["duplicate_rows_removed"] == 1
    assert data["metrics"]["rows_removed_empty"] == 1


def test_process_semicolon_delimited_csv(client):
    """European-style semicolon delimited CSV is auto-detected and processed."""
    csv_content = (
        "Name;Email;Revenue\n"
        "Acme Corp;info@acme.com;€ 1.250,50\n"
        "Beta Ltd;contact@beta.co.uk;€ 3.400,00\n"
    ).encode()

    response = client.post(
        "/api/process",
        files={"file": ("european_data.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["rows_initial"] == 2
    assert data["metrics"]["rows_final"] == 2
    assert len(data["columns"]) == 3


def test_process_tab_delimited_csv(client):
    """Tab-delimited TSV/CSV format is detected and processed."""
    tsv_content = (
        b"Name\tEmail\tAmount\n"
        b"Delta Inc\tsupport@delta.io\t$500.00\n"
        b"Echo LLC\tsales@echo.com\t$750.00\n"
    )

    response = client.post(
        "/api/process",
        files={"file": ("tab_data.csv", tsv_content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["rows_initial"] == 2
    assert data["metrics"]["rows_final"] == 2


def test_process_empty_file_returns_400(client):
    """Zero-byte upload returns 400 Bad Request."""
    response = client.post(
        "/api/process",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_process_disallowed_extension_returns_400(client):
    """Disallowed extension returns 400 with permitted formats."""
    response = client.post(
        "/api/process",
        files={"file": ("data.json", b'{"key": "val"}', "application/json")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_process_corrupt_csv_returns_400(client):
    """Binary null bytes masquerading as CSV are rejected with 400."""
    corrupt_bytes = b"\x00\x00\x00\x00\xff\xfe\x00\x00"
    response = client.post(
        "/api/process",
        files={"file": ("bad.csv", corrupt_bytes, "text/csv")},
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert any(term in detail for term in ["csv", "null bytes", "binary", "could not parse"])


def test_process_corrupt_excel_returns_400(client):
    """Invalid ZIP archive sent as XLSX returns 400."""
    excel_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    corrupt_bytes = b"Not a zip file or valid openpyxl spreadsheet"
    response = client.post(
        "/api/process",
        files={"file": ("bad.xlsx", corrupt_bytes, excel_mime)},
    )
    assert response.status_code == 400
    assert "Could not parse Excel" in response.json()["detail"]


def test_process_oversized_file_returns_413(client, monkeypatch):
    """Files exceeding maximum configured payload return HTTP 413."""
    import app.main as main_module

    monkeypatch.setattr(main_module, "MAX_UPLOAD_SIZE_BYTES", 100)

    oversized_data = b"col1,col2\n" + (b"val1,val2\n" * 50)
    response = client.post(
        "/api/process",
        files={"file": ("oversized.csv", oversized_data, "text/csv")},
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_download_clean_csv_and_xlsx(client, valid_csv_bytes):
    """Successfully streams cleaned CSV and XLSX attachments."""
    process_resp = client.post(
        "/api/process",
        files={"file": ("dataset.csv", valid_csv_bytes, "text/csv")},
    )
    file_id = process_resp.json()["file_id"]

    # Download CSV
    csv_resp = client.get(f"/api/download/{file_id}/csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    assert b"Alpha Tech" in csv_resp.content

    # Download XLSX
    xlsx_resp = client.get(f"/api/download/{file_id}/xlsx")
    assert xlsx_resp.status_code == 200
    assert "openxmlformats" in xlsx_resp.headers.get("content-type", "")
    assert len(xlsx_resp.content) > 100


def test_download_invalid_uuid_returns_400(client):
    """Malformed UUID path parameter returns 400."""
    response = client.get("/api/download/not-a-valid-uuid/csv")
    assert response.status_code == 400
    assert "Invalid file identifier" in response.json()["detail"]


def test_download_nonexistent_uuid_returns_404(client):
    """Non-existent UUID session returns 404."""
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/download/{random_uuid}/csv")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_invalid_format_returns_400(client):
    """Unapproved export format returns 400."""
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/download/{random_uuid}/pdf")
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_demo_data_static_serving(client):
    """Static demo file endpoint serves raw demo files correctly."""
    response = client.get("/demo-data/customers_messy.csv")
    assert response.status_code == 200
    assert "CUST-1001" in response.text


def test_process_actual_demo_csv_file(client):
    """Full end-to-end integration test with real demo CSV dataset."""
    demo_path = Path("demo_data/customers_messy.csv")
    assert demo_path.exists(), "demo_data/customers_messy.csv must exist"

    with open(demo_path, "rb") as f:
        response = client.post(
            "/api/process",
            files={"file": (demo_path.name, f.read(), "text/csv")},
        )
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]
    assert metrics["rows_initial"] == 31
    assert metrics["rows_final"] == 25
    assert metrics["duplicate_rows_removed"] == 3
    assert metrics["rows_removed_empty"] == 3
    assert metrics["columns_removed_empty"] == 1


def test_process_actual_demo_xlsx_file(client):
    """Full end-to-end integration test with real demo Excel dataset."""
    excel_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    demo_path = Path("demo_data/customers_messy.xlsx")
    assert demo_path.exists(), "demo_data/customers_messy.xlsx must exist"

    with open(demo_path, "rb") as f:
        response = client.post(
            "/api/process",
            files={"file": (demo_path.name, f.read(), excel_mime)},
        )
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]
    assert metrics["rows_initial"] == 31
    assert metrics["rows_final"] == 25
    assert metrics["duplicate_rows_removed"] == 3
    assert metrics["rows_removed_empty"] == 3


def test_storage_isolation_no_artifacts_in_project_storage(client, valid_csv_bytes):
    """
    Verifies that API tests execute against isolated temporary storage
    without polluting the project's storage/processed directory.
    """
    from app.config import STORAGE_DIR

    entries_before = set(STORAGE_DIR.iterdir()) if STORAGE_DIR.exists() else set()

    response = client.post(
        "/api/process",
        files={"file": ("isolation_check.csv", valid_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200

    entries_after = set(STORAGE_DIR.iterdir()) if STORAGE_DIR.exists() else set()
    # Confirm no new files or folders were created in project storage/processed
    assert entries_after == entries_before


def test_cors_headers_do_not_expose_credentials(client):
    """Verifies that CORS allows cross-origin requests without allow_credentials=True."""
    response = client.options(
        "/api/process",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert response.headers.get("access-control-allow-credentials") is None


def test_process_ambiguous_numeric_dataset_via_api(client):
    """
    Verifies that ambiguous numeric strings (1,234 and 1.234) are
    preserved without data mutation and flagged with warnings via API.
    """
    csv_content = (
        b"Name,Revenue\n"
        b'Ambiguous US,"1,234"\n'
        b"Ambiguous EU,1.234\n"
        b'Unambiguous US,"1,234.56"\n'
        b'Unambiguous EU,"1.234,56"\n'
    )

    response = client.post(
        "/api/process",
        files={"file": ("mixed_numeric.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()

    # Preserved values in sample preview
    preview = data["sample_preview"]
    assert preview[0]["Revenue"] == "1,234"
    assert preview[1]["Revenue"] == "1.234"
    assert preview[2]["Revenue"] == 1234.56
    assert preview[3]["Revenue"] == 1234.56

    # Warnings for ambiguous rows
    warnings = data["warnings"]
    assert any("Ambiguous numeric format '1,234'" in w for w in warnings)
    assert any("Ambiguous numeric format '1.234'" in w for w in warnings)
    assert not any("1,234.56" in w for w in warnings)
    assert not any("1.234,56" in w for w in warnings)
