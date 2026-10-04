import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_csv_bytes():
    """Generates bytes for a valid small CSV with known issues."""
    content = (
        "name,email,revenue\n"
        "  Alpha Tech  ,ALPHA@CORP.COM,\"$1,500.00\"\n"
        "Alpha Tech,alpha@corp.com,1500.0\n"  # Duplicate of row 1 after cleaning
        "Beta LLC,invalid_email_at_beta.com,\"€ 2.300,50\"\n"
        ",,\n"  # Empty row
        "Gamma Global,contact@gamma.org,850\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def valid_xlsx_bytes():
    """Generates bytes for a valid Excel workbook with known issues."""
    df = pd.DataFrame([
        {"id": 1, "name": "Company A", "email": "SALES@COMPA.COM", "amount": "$5,000.00"},
        {"id": 2, "name": "Company B", "email": "info@compb.org", "amount": "1200"},
        {"id": None, "name": None, "email": None, "amount": None},  # Empty row
        {"id": 2, "name": "Company B", "email": "info@compb.org", "amount": "1200"},  # Duplicate
    ])
    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()
