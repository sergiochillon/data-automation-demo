import numpy as np
import pandas as pd
import pytest

from app.processor import (
    DataProcessor,
    clean_currency_or_numeric_string,
    load_dataframe_from_bytes,
    DataProcessingError,
)


def test_empty_rows_elimination():
    df = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": None, "name": None},
        {"id": " ", "name": "   "},
        {"id": 2, "name": "Bob"},
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 4
    assert metrics.rows_final == 2
    assert metrics.rows_removed_empty == 2
    assert list(cleaned_df["name"]) == ["Alice", "Bob"]
    assert any("Removed 2 completely empty row(s)" in c for c in changes)


def test_empty_columns_elimination():
    df = pd.DataFrame([
        {"id": 1, "name": "Alice", "blank_col": None, "space_col": "   "},
        {"id": 2, "name": "Bob", "blank_col": None, "space_col": ""},
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert metrics.columns_removed_empty == 2
    assert "blank_col" not in cleaned_df.columns
    assert "space_col" not in cleaned_df.columns
    assert list(cleaned_df.columns) == ["id", "name"]


def test_whitespace_normalization():
    df = pd.DataFrame([
        {"name": "  ACME   CORPORATION  ", "city": " New   York "},
        {"name": "Beta  Industries", "city": "Chicago"},
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "name"] == "Acme Corporation"
    assert cleaned_df.at[0, "city"] == "New York"
    assert metrics.fields_normalized > 0


def test_exact_duplicates_removal():
    df = pd.DataFrame([
        {"id": "100", "client": "Global Logistics"},
        {"id": "100", "client": "Global Logistics"},  # Duplicate
        {"id": "101", "client": "Delta Corp"},
        {"id": "100", "client": "Global Logistics"},  # Another duplicate
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 4
    assert metrics.rows_final == 2
    assert metrics.duplicate_rows_removed == 2
    assert len(cleaned_df) == 2


def test_email_normalization_and_validation():
    df = pd.DataFrame([
        {"email": "  USER@EXAMPLE.COM  "},
        {"email": "valid.address@domain.co.uk"},
        {"email": "not_an_email_at_all"},
        {"email": "missing_domain@"},
        {"email": None},
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "email"] == "user@example.com"
    assert metrics.invalid_emails_count == 2
    assert len(warnings) == 2
    assert any("not_an_email_at_all" in w for w in warnings)
    assert any("missing_domain@" in w for w in warnings)


def test_currency_and_numeric_cleaning():
    # US format
    val_us, norm_us, inv_us = clean_currency_or_numeric_string("$1,450.75")
    assert val_us == 1450.75
    assert norm_us is True
    assert inv_us is False

    # EU format
    val_eu, norm_eu, inv_eu = clean_currency_or_numeric_string("€ 2.300,50")
    assert val_eu == 2300.50
    assert norm_eu is True
    assert inv_eu is False

    # Plain integer string
    val_int, norm_int, inv_int = clean_currency_or_numeric_string(" 950 ")
    assert val_int == 950.0
    assert norm_int is True

    # Invalid representation
    val_inv, norm_inv, inv_flag = clean_currency_or_numeric_string("PENDING_PAYMENT")
    assert val_inv == "PENDING_PAYMENT"
    assert inv_flag is True


def test_name_casing_normalization():
    df = pd.DataFrame([
        {"customer_name": "JOHNATHAN DOE"},
        {"customer_name": "sarah connor"},
        {"customer_name": "McDonald"},  # Mixed case: preserved intentionally
        {"customer_name": "van der Waals"},  # Mixed case: preserved
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "customer_name"] == "Johnathan Doe"
    assert cleaned_df.at[1, "customer_name"] == "Sarah Connor"
    assert cleaned_df.at[2, "customer_name"] == "McDonald"
    assert cleaned_df.at[3, "customer_name"] == "van der Waals"


def test_null_value_counting():
    df = pd.DataFrame([
        {"col1": "A", "col2": None, "col3": np.nan},
        {"col1": None, "col2": "B", "col3": "C"},
    ])
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert metrics.null_values_count == 3


def test_empty_dataframe():
    df = pd.DataFrame()
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 0
    assert metrics.rows_final == 0
    assert len(changes) == 1


def test_load_dataframe_empty_bytes():
    with pytest.raises(DataProcessingError, match="File contains no data"):
        load_dataframe_from_bytes(b"", "empty.csv")


def test_load_dataframe_corrupt_csv():
    with pytest.raises(DataProcessingError):
        # Null bytes causing parsing issues
        load_dataframe_from_bytes(b"\x00\x01\x02\x03\x04\xff\xfe", "corrupt.csv")


def test_load_dataframe_corrupt_excel():
    with pytest.raises(DataProcessingError, match="Could not parse Excel"):
        load_dataframe_from_bytes(b"This is not a zip or xlsx file", "corrupt.xlsx")
