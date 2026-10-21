import io
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import StorageManager


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """FastAPI TestClient fixture with isolated temporary storage."""
    test_storage = StorageManager(base_dir=tmp_path / "storage", retention_seconds=3600)
    monkeypatch.setattr("app.main.default_storage", test_storage)
    monkeypatch.setattr("app.storage.default_storage", test_storage)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_csv_bytes():
    """Generates bytes for a valid small CSV with known data-quality issues."""
    content = (
        "name,email,revenue\n"
        '  Alpha Tech  ,ALPHA@CORP.COM,"$1,500.00"\n'
        "Alpha Tech,alpha@corp.com,1500.0\n"  # Exact duplicate of row 1 after normalization
        'Beta LLC,invalid_email_at_beta.com,"€ 2.300,50"\n'
        ",,\n"  # Completely empty row
        "Gamma Global,contact@gamma.org,850\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def valid_xlsx_bytes():
    """Generates bytes for a valid Excel workbook with known data-quality issues."""
    df = pd.DataFrame(
        [
            {"id": 1, "name": "Company A", "email": "SALES@COMPA.COM", "amount": "$5,000.00"},
            {"id": 2, "name": "Company B", "email": "info@compb.org", "amount": "1200"},
            {"id": None, "name": None, "email": None, "amount": None},  # Empty row
            # Exact duplicate of company B
            {"id": 2, "name": "Company B", "email": "info@compb.org", "amount": "1200"},
        ]
    )
    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()
