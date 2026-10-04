import io
import uuid
import pytest
from app.config import MAX_UPLOAD_SIZE_BYTES


def test_api_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data-automation-demo"
    assert "version" in data


def test_serve_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Data Processing Tool" in response.text


def test_process_valid_csv(client, valid_csv_bytes):
    response = client.post(
        "/api/process",
        files={"file": ("test_dataset.csv", valid_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()

    assert "file_id" in data
    assert data["original_filename"] == "test_dataset.csv"
    assert data["metrics"]["rows_initial"] == 5  # 5 rows parsed
    assert data["metrics"]["rows_final"] == 3    # 1 empty row dropped, 1 duplicate dropped
    assert data["metrics"]["duplicate_rows_removed"] == 1
    assert data["metrics"]["rows_removed_empty"] == 1
    assert data["metrics"]["invalid_emails_count"] == 1
    assert len(data["sample_preview"]) > 0
    assert data["csv_download_url"].startswith("/api/download/")
    assert data["xlsx_download_url"].startswith("/api/download/")


def test_process_valid_excel(client, valid_xlsx_bytes):
    response = client.post(
        "/api/process",
        files={"file": ("test_workbook.xlsx", valid_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["original_filename"] == "test_workbook.xlsx"
    assert data["metrics"]["rows_initial"] == 4
    assert data["metrics"]["rows_final"] == 2  # 1 empty dropped, 1 duplicate dropped
    assert data["metrics"]["duplicate_rows_removed"] == 1
    assert data["metrics"]["rows_removed_empty"] == 1


def test_process_empty_file_returns_400(client):
    response = client.post(
        "/api/process",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_process_disallowed_extension_returns_400(client):
    response = client.post(
        "/api/process",
        files={"file": ("data.json", b'{"key": "val"}', "application/json")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_process_corrupt_csv_returns_400(client):
    # Null byte sequences that fail standard text processing
    corrupt_bytes = b"\x00\x00\x00\x00\xff\xfe\x00\x00"
    response = client.post(
        "/api/process",
        files={"file": ("bad.csv", corrupt_bytes, "text/csv")},
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert any(term in detail for term in ["csv", "null bytes", "binary", "could not parse"])


def test_process_corrupt_excel_returns_400(client):
    corrupt_bytes = b"Not a zip file or valid openpyxl spreadsheet"
    response = client.post(
        "/api/process",
        files={"file": ("bad.xlsx", corrupt_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "Could not parse Excel" in response.json()["detail"]


def test_process_oversized_file_returns_413(client, monkeypatch):
    # Temporarily set max size to 100 bytes to test 413 payload limit deterministically
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
    # First, process a file to obtain a valid file_id
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
    response = client.get("/api/download/not-a-valid-uuid/csv")
    assert response.status_code == 400
    assert "Invalid file identifier" in response.json()["detail"]


def test_download_nonexistent_uuid_returns_404(client):
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/download/{random_uuid}/csv")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_invalid_format_returns_400(client):
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/download/{random_uuid}/pdf")
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_demo_data_static_serving(client):
    response = client.get("/demo-data/customers_messy.csv")
    assert response.status_code == 200
    assert "CUST-1001" in response.text


def test_process_actual_demo_csv_file(client):
    from pathlib import Path
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
    from pathlib import Path
    demo_path = Path("demo_data/customers_messy.xlsx")
    assert demo_path.exists(), "demo_data/customers_messy.xlsx must exist"
    
    with open(demo_path, "rb") as f:
        response = client.post(
            "/api/process",
            files={"file": (demo_path.name, f.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]
    assert metrics["rows_initial"] == 31
    assert metrics["rows_final"] == 25
    assert metrics["duplicate_rows_removed"] == 3
    assert metrics["rows_removed_empty"] == 3
