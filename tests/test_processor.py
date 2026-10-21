import numpy as np
import pandas as pd
import pytest

from app.processor import (
    DataProcessingError,
    DataProcessor,
    clean_currency_or_numeric_string,
    load_dataframe_from_bytes,
)


def test_empty_rows_elimination():
    """Confirms completely empty or whitespace-only rows are removed."""
    df = pd.DataFrame(
        [
            {"id": 1, "name": "Alice"},
            {"id": None, "name": None},
            {"id": " ", "name": "   "},
            {"id": 2, "name": "Bob"},
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, changes, _warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 4
    assert metrics.rows_final == 2
    assert metrics.rows_removed_empty == 2
    assert list(cleaned_df["name"]) == ["Alice", "Bob"]
    assert any("Removed 2 completely empty row(s)" in c for c in changes)


def test_empty_columns_elimination():
    """Confirms columns with all-NaN or all-whitespace are dropped."""
    df = pd.DataFrame(
        [
            {"id": 1, "name": "Alice", "blank_col": None, "space_col": "   "},
            {"id": 2, "name": "Bob", "blank_col": None, "space_col": ""},
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, _changes, _warnings = processor.process(df, "test.csv")

    assert metrics.columns_removed_empty == 2
    assert "blank_col" not in cleaned_df.columns
    assert "space_col" not in cleaned_df.columns
    assert list(cleaned_df.columns) == ["id", "name"]


def test_whitespace_normalization():
    """Confirms trimming and internal multi-space collapsing."""
    df = pd.DataFrame(
        [
            {"name": "  ACME   CORPORATION  ", "city": " New   York "},
            {"name": "Beta  Industries", "city": "Chicago"},
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, _changes, _warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "name"] == "Acme Corporation"
    assert cleaned_df.at[0, "city"] == "New York"
    assert metrics.fields_normalized > 0


def test_exact_duplicates_removal():
    """Confirms exact duplicate records are detected and pruned."""
    df = pd.DataFrame(
        [
            {"id": "100", "client": "Global Logistics"},
            {"id": "100", "client": "Global Logistics"},  # Duplicate
            {"id": "101", "client": "Delta Corp"},
            {"id": "100", "client": "Global Logistics"},  # Another duplicate
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, _changes, _warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 4
    assert metrics.rows_final == 2
    assert metrics.duplicate_rows_removed == 2
    assert len(cleaned_df) == 2


def test_email_normalization_and_validation():
    """Confirms lowercasing and RFC-regex issue flagging for invalid emails."""
    df = pd.DataFrame(
        [
            {"email": "  USER@EXAMPLE.COM  "},
            {"email": "valid.address@domain.co.uk"},
            {"email": "not_an_email_at_all"},
            {"email": "missing_domain@"},
            {"email": None},
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, _changes, warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "email"] == "user@example.com"
    assert metrics.invalid_emails_count == 2
    assert len(warnings) == 2
    assert any("not_an_email_at_all" in w for w in warnings)
    assert any("missing_domain@" in w for w in warnings)


def test_currency_and_numeric_cleaning():
    """Confirms currency parsing across US, EU, and accounting negative formats."""
    # US format
    val_us, norm_us, inv_us, amb_us = clean_currency_or_numeric_string("$1,450.75")
    assert val_us == 1450.75
    assert norm_us is True
    assert inv_us is False
    assert amb_us is False

    # EU format
    val_eu, norm_eu, inv_eu, amb_eu = clean_currency_or_numeric_string("€ 2.300,50")
    assert val_eu == 2300.50
    assert norm_eu is True
    assert inv_eu is False
    assert amb_eu is False

    # Negative accounting parentheses format
    val_neg_paren, norm_neg_paren, inv_neg_paren, amb_neg_paren = clean_currency_or_numeric_string(
        "($1,250.00)"
    )
    assert val_neg_paren == -1250.00
    assert norm_neg_paren is True
    assert inv_neg_paren is False
    assert amb_neg_paren is False

    # Negative minus format
    val_neg_minus, norm_neg_minus, inv_neg_minus, amb_neg_minus = clean_currency_or_numeric_string(
        "-$450.25"
    )
    assert val_neg_minus == -450.25
    assert norm_neg_minus is True
    assert inv_neg_minus is False
    assert amb_neg_minus is False

    # Plain integer string with whitespace
    val_int, norm_int, inv_int, amb_int = clean_currency_or_numeric_string(" 950 ")
    assert val_int == 950.0
    assert norm_int is True
    assert inv_int is False
    assert amb_int is False

    # Invalid string representation preserved without destruction
    val_inv, norm_inv, inv_flag, amb_inv = clean_currency_or_numeric_string("PENDING_PAYMENT")
    assert val_inv == "PENDING_PAYMENT"
    assert norm_inv is False
    assert inv_flag is True
    assert amb_inv is False


def test_numeric_ambiguous_formats():
    """
    Confirms that genuinely ambiguous numeric representations (such as '1,234'
    and '1.234' where single separator groups exactly 3 digits) are identified
    as ambiguous and preserved without mutation.
    """
    # Plain 1,234 (US thousands or EU decimal)
    val, norm, inv, amb = clean_currency_or_numeric_string("1,234")
    assert val == "1,234"
    assert norm is False
    assert inv is False
    assert amb is True

    # Plain 1.234 (US decimal or EU thousands)
    val, norm, inv, amb = clean_currency_or_numeric_string("1.234")
    assert val == "1.234"
    assert norm is False
    assert inv is False
    assert amb is True

    # Ambiguous with currency
    val_curr_us, norm_c_us, inv_c_us, amb_c_us = clean_currency_or_numeric_string("$1,234")
    assert val_curr_us == "$1,234"
    assert norm_c_us is False
    assert amb_c_us is True

    val_curr_eu, norm_c_eu, inv_c_eu, amb_c_eu = clean_currency_or_numeric_string("€ 1.234")
    assert val_curr_eu == "€ 1.234"
    assert norm_c_eu is False
    assert amb_c_eu is True

    # Ambiguous with negative accounting or minus
    val_neg_paren, _, _, amb_neg_p = clean_currency_or_numeric_string("(1,234)")
    assert val_neg_paren == "(1,234)"
    assert amb_neg_p is True

    val_neg_m, _, _, amb_neg_m = clean_currency_or_numeric_string("-1.234")
    assert val_neg_m == "-1.234"
    assert amb_neg_m is True


def test_numeric_unambiguous_formats():
    """
    Confirms that unambiguous numeric formats across US and European styles
    are correctly parsed into floats.
    """
    # US format with decimal dot: 1,234.56
    val, norm, inv, amb = clean_currency_or_numeric_string("1,234.56")
    assert val == 1234.56
    assert norm is True
    assert inv is False
    assert amb is False

    # EU format with decimal comma: 1.234,56
    val, norm, inv, amb = clean_currency_or_numeric_string("1.234,56")
    assert val == 1234.56
    assert norm is True
    assert inv is False
    assert amb is False

    # Multiple thousands separators: 1,234,567 and 1.234.567
    val_mus, norm_mus, _, _ = clean_currency_or_numeric_string("1,234,567")
    assert val_mus == 1234567.0
    assert norm_mus is True

    val_meu, norm_meu, _, _ = clean_currency_or_numeric_string("1.234.567")
    assert val_meu == 1234567.0
    assert norm_meu is True

    # Unambiguous decimal comma without thousands (not 3 trailing digits)
    val_dec_c, norm_dec_c, _, _ = clean_currency_or_numeric_string("1234,56")
    assert val_dec_c == 1234.56
    assert norm_dec_c is True

    # Unambiguous decimal dot without thousands (not 3 trailing digits)
    val_dec_d, norm_dec_d, _, _ = clean_currency_or_numeric_string("1234.56")
    assert val_dec_d == 1234.56
    assert norm_dec_d is True

    # Leading zero with 3 decimals: 0.123 and 0,123 are unambiguous decimals (never thousands)
    val_zd, norm_zd, inv_zd, amb_zd = clean_currency_or_numeric_string("0.123")
    assert val_zd == 0.123
    assert norm_zd is True
    assert inv_zd is False
    assert amb_zd is False

    val_zc, norm_zc, inv_zc, amb_zc = clean_currency_or_numeric_string("0,123")
    assert val_zc == 0.123
    assert norm_zc is True
    assert inv_zc is False
    assert amb_zc is False

    # Decimal forms accepted by Python's numeric syntax
    val_leading_dot, norm_leading_dot, inv_leading_dot, amb_leading_dot = (
        clean_currency_or_numeric_string(".5")
    )
    assert val_leading_dot == 0.5
    assert norm_leading_dot is True
    assert inv_leading_dot is False
    assert amb_leading_dot is False

    val_trailing_dot, norm_trailing_dot, inv_trailing_dot, amb_trailing_dot = (
        clean_currency_or_numeric_string("1.")
    )
    assert val_trailing_dot == 1.0
    assert norm_trailing_dot is True
    assert inv_trailing_dot is False
    assert amb_trailing_dot is False


def test_processor_leading_zero_decimals():
    """
    Confirms that numbers with a leading zero and three decimal digits (0.123 and 0,123)
    are parsed as legitimate decimals without being falsely classified as ambiguous.
    """
    df = pd.DataFrame(
        [
            {"customer": "Customer A", "revenue": "0.123"},
            {"customer": "Customer B", "revenue": "0,123"},
            {"customer": "Customer C", "revenue": "$0.123"},
            {"customer": "Customer D", "revenue": "€ 0,123"},
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test_zero_decimals.csv")

    assert cleaned_df.at[0, "revenue"] == 0.123
    assert cleaned_df.at[1, "revenue"] == 0.123
    assert cleaned_df.at[2, "revenue"] == 0.123
    assert cleaned_df.at[3, "revenue"] == 0.123

    assert metrics.invalid_values_detected == 0
    assert metrics.fields_normalized == 4
    assert len(warnings) == 0


def test_processor_ambiguous_and_unambiguous_pipeline():
    """
    Verifies DataProcessor pipeline behavior on a mixed column with both ambiguous
    (1,234, 1.234) and unambiguous (1,234.56, 1.234,56) values, checking resulting
    values, metrics, and warnings.
    """
    df = pd.DataFrame(
        [
            {"customer": "Customer A", "revenue": "1,234"},  # Ambiguous
            {"customer": "Customer B", "revenue": "1.234"},  # Ambiguous
            {"customer": "Customer C", "revenue": "1,234.56"},  # Unambiguous US
            {"customer": "Customer D", "revenue": "1.234,56"},  # Unambiguous EU
            {"customer": "Customer E", "revenue": "PENDING"},  # Unrecognized format
            {"customer": "Customer F", "revenue": None},  # Null value
        ]
    )
    processor = DataProcessor()
    cleaned_df, metrics, changes, warnings = processor.process(df, "test_numeric.csv")

    # Ambiguous values are preserved as original strings without mutation
    assert cleaned_df.at[0, "revenue"] == "1,234"
    assert cleaned_df.at[1, "revenue"] == "1.234"

    # Unambiguous values are parsed into floats
    assert cleaned_df.at[2, "revenue"] == 1234.56
    assert cleaned_df.at[3, "revenue"] == 1234.56

    # Unrecognized values are preserved as original strings
    assert cleaned_df.at[4, "revenue"] == "PENDING"
    assert pd.isna(cleaned_df.at[5, "revenue"])

    # Metrics
    assert metrics.invalid_values_detected == 3  # 2 ambiguous + 1 unrecognized
    assert metrics.fields_normalized == 2  # 2 unambiguous values normalized

    # Warnings verification
    assert len(warnings) == 3
    assert any("Ambiguous numeric format '1,234'" in w for w in warnings)
    assert any("Ambiguous numeric format '1.234'" in w for w in warnings)
    assert any("Unrecognized numeric format 'PENDING'" in w for w in warnings)
    assert not any("1,234.56" in w for w in warnings)
    assert not any("1.234,56" in w for w in warnings)


def test_name_casing_normalization():
    """Confirms proper casing while respecting mixed-case names."""
    df = pd.DataFrame(
        [
            {"customer_name": "JOHNATHAN DOE"},
            {"customer_name": "sarah connor"},
            {"customer_name": "McDonald"},  # Mixed case: preserved intentionally
            {"customer_name": "van der Waals"},  # Mixed case: preserved
            {"customer_name": "O'Connor"},  # Mixed case: preserved
        ]
    )
    processor = DataProcessor()
    cleaned_df, _metrics, _changes, _warnings = processor.process(df, "test.csv")

    assert cleaned_df.at[0, "customer_name"] == "Johnathan Doe"
    assert cleaned_df.at[1, "customer_name"] == "Sarah Connor"
    assert cleaned_df.at[2, "customer_name"] == "McDonald"
    assert cleaned_df.at[3, "customer_name"] == "van der Waals"
    assert cleaned_df.at[4, "customer_name"] == "O'Connor"


def test_null_value_counting():
    """Metrics accurately count remaining NaN/null cells."""
    df = pd.DataFrame(
        [
            {"col1": "A", "col2": None, "col3": np.nan},
            {"col1": None, "col2": "B", "col3": "C"},
        ]
    )
    processor = DataProcessor()
    _cleaned_df, metrics, _changes, _warnings = processor.process(df, "test.csv")

    assert metrics.null_values_count == 3


def test_empty_dataframe():
    """Empty input DataFrame is handled gracefully without crash."""
    df = pd.DataFrame()
    processor = DataProcessor()
    _cleaned_df, metrics, changes, _warnings = processor.process(df, "test.csv")

    assert metrics.rows_initial == 0
    assert metrics.rows_final == 0
    assert len(changes) == 1


def test_load_dataframe_empty_bytes():
    """Zero-length bytes raise DataProcessingError."""
    with pytest.raises(DataProcessingError, match="File contains no data"):
        load_dataframe_from_bytes(b"", "empty.csv")


def test_load_dataframe_corrupt_csv():
    """Binary null bytes in CSV raise DataProcessingError."""
    with pytest.raises(DataProcessingError):
        load_dataframe_from_bytes(b"\x00\x01\x02\x03\x04\xff\xfe", "corrupt.csv")


def test_load_dataframe_corrupt_excel():
    """Non-zip binary in XLSX raises DataProcessingError."""
    with pytest.raises(DataProcessingError, match="Could not parse Excel"):
        load_dataframe_from_bytes(b"This is not a zip or xlsx file", "corrupt.xlsx")


def test_load_dataframe_utf8_sig_bom():
    """Handles UTF-8 with Byte Order Mark (BOM) properly."""
    bom_content = b"\xef\xbb\xbfid,name,city\n1,Alice,Madrid\n2,Bob,Barcelona\n"
    df = load_dataframe_from_bytes(bom_content, "bom.csv")
    assert len(df) == 2
    assert "id" in df.columns
    assert df.at[0, "name"] == "Alice"


def test_load_dataframe_latin1_encoding():
    """Handles Latin-1 / ISO-8859-1 encoded characters (e.g. accented letters)."""
    # ñ in Latin-1 is 0xF1, é is 0xE9
    latin1_content = "id,nombre,país\n1,Iñaki,España\n2,José,México\n".encode("latin-1")
    df = load_dataframe_from_bytes(latin1_content, "latin1.csv")
    assert len(df) == 2
    assert "nombre" in df.columns
    assert df.at[0, "nombre"] == "Iñaki"


def test_load_dataframe_semicolon_delimited():
    """Automatic fallback or sniffing handles semicolon delimiters."""
    semicolon_content = b"id;name;amount\n1;Alpha;100\n2;Beta;200\n"
    df = load_dataframe_from_bytes(semicolon_content, "semi.csv")
    assert len(df) == 2
    assert len(df.columns) == 3
    assert list(df.columns) == ["id", "name", "amount"]


def test_load_dataframe_tab_delimited():
    """Tab-delimited files are properly parsed."""
    tab_content = b"id\tname\tamount\n1\tAlpha\t100\n2\tBeta\t200\n"
    df = load_dataframe_from_bytes(tab_content, "tab.csv")
    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "amount"]
