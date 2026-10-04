import io
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.models import ProcessingMetrics
from app.security import sanitize_cell_value

# Email RFC 5322 pragmatic validation pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Candidate column names for specific logic
EMAIL_COL_KEYWORDS = ("email", "e-mail", "correo", "mail")
NAME_COL_KEYWORDS = ("name", "first_name", "last_name", "full_name", "nombre", "customer_name", "client_name")
NUMERIC_COL_KEYWORDS = ("revenue", "amount", "price", "total", "balance", "sales", "cost", "income", "ingresos")


class DataProcessingError(Exception):
    """Raised when input data cannot be parsed or is unrecoverably invalid."""
    pass


def load_dataframe_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Parses CSV or Excel bytes into a pandas DataFrame with sensible encoding fallbacks.
    """
    if not file_bytes or len(file_bytes.strip()) == 0:
        raise DataProcessingError("File contains no data.")

    filename_lower = filename.lower()

    if filename_lower.endswith(".csv"):
        # Check for binary files masquerading as CSV (presence of null bytes)
        if b"\x00" in file_bytes:
            raise DataProcessingError("File contains null bytes or binary characters; not a valid CSV text document.")

        # Attempt common text encodings
        encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        last_error: Optional[Exception] = None

        for enc in encodings:
            try:
                # Use python engine with sep=None to detect delimiter, and index_col=False to prevent treating col 0 as index
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=None, engine="python", index_col=False)
                return df
            except Exception as e:
                last_error = e
                continue

        raise DataProcessingError(f"Could not parse CSV file. Error details: {str(last_error)}")

    elif filename_lower.endswith(".xlsx"):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            return df
        except Exception as e:
            raise DataProcessingError(f"Could not parse Excel (.xlsx) file. Error details: {str(e)}")

    else:
        raise DataProcessingError(f"Unsupported file format for '{filename}'. Expected .csv or .xlsx.")


def is_email_column(col_name: str, sample_series: pd.Series) -> bool:
    """Determines whether a column likely contains email addresses."""
    col_clean = str(col_name).strip().lower()
    if any(keyword in col_clean for keyword in EMAIL_COL_KEYWORDS):
        return True

    # Check non-null values for '@' symbol presence
    non_null = sample_series.dropna().astype(str)
    if len(non_null) >= 3:
        at_ratio = non_null.str.contains("@").mean()
        if at_ratio > 0.6:
            return True
    return False


def is_name_column(col_name: str) -> bool:
    """Determines whether a column likely contains person or business names."""
    col_clean = str(col_name).strip().lower()
    return any(keyword in col_clean for keyword in NAME_COL_KEYWORDS)


def is_numeric_candidate_column(col_name: str) -> bool:
    """Determines whether a column should be treated as numeric/financial."""
    col_clean = str(col_name).strip().lower()
    return any(keyword in col_clean for keyword in NUMERIC_COL_KEYWORDS)


def clean_currency_or_numeric_string(val: Any) -> Tuple[Any, bool, bool]:
    """
    Attempts to clean and normalize a numeric/currency string.
    Returns: (cleaned_val, was_normalized, is_invalid)
    """
    if val is None or pd.isna(val):
        return np.nan, False, False

    if isinstance(val, (int, float, np.integer, np.floating)):
        return val, False, False

    s = str(val).strip()
    if not s:
        return np.nan, True, False

    # Check if string matches typical currency or formatted numbers: e.g. "$1,250.50", "€ 1.250,50", "950"
    cleaned = re.sub(r"[$\€\£\¥\s]", "", s)

    # US format: 1,234.56
    if re.match(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$", cleaned):
        try:
            num = float(cleaned.replace(",", ""))
            return num, (s != str(num)), False
        except ValueError:
            pass

    # EU format: 1.234,56
    if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", cleaned):
        try:
            standardized = cleaned.replace(".", "").replace(",", ".")
            num = float(standardized)
            return num, True, False
        except ValueError:
            pass

    # Simple decimal or integer string
    try:
        num = float(cleaned)
        return num, (s != str(num)), False
    except ValueError:
        # Not a valid numeric representation
        return val, False, True


class DataProcessor:
    """
    Conservative, deterministic data cleaning and validation engine.
    Produces auditable metrics and a clean DataFrame.
    """

    def process(self, df_raw: pd.DataFrame, filename: str) -> Tuple[pd.DataFrame, ProcessingMetrics, List[str], List[str]]:
        start_time = time.perf_counter()

        changes_summary: List[str] = []
        warnings: List[str] = []

        rows_initial = len(df_raw)
        if rows_initial == 0:
            metrics = ProcessingMetrics(
                rows_initial=0,
                rows_final=0,
                rows_removed_empty=0,
                columns_removed_empty=0,
                duplicate_rows_removed=0,
                invalid_emails_count=0,
                invalid_values_detected=0,
                fields_normalized=0,
                null_values_count=0,
                processing_time_ms=0.0,
            )
            return df_raw.copy(), metrics, ["No data rows found in input file."], []

        fields_normalized_count = 0
        invalid_values_count = 0
        invalid_emails_count = 0

        df = df_raw.copy()

        # Step 1: Strip whitespace from column headers
        original_cols = list(df.columns)
        clean_cols = [str(c).strip() for c in original_cols]
        if clean_cols != original_cols:
            df.columns = clean_cols
            changes_summary.append("Trimmed whitespace from column headers")

        # Step 2: Drop completely empty columns
        empty_cols = [c for c in df.columns if df[c].isna().all() or (df[c].astype(str).str.strip() == "").all()]
        columns_removed_empty = len(empty_cols)
        if columns_removed_empty > 0:
            df = df.drop(columns=empty_cols)
            changes_summary.append(f"Removed {columns_removed_empty} completely empty column(s): {', '.join(empty_cols)}")

        # Step 3: Drop completely empty rows
        # A row is completely empty if all values are NaN or only whitespace strings
        is_empty_row = df.apply(
            lambda row: row.isna().all() or all(pd.isna(v) or str(v).strip() == "" for v in row),
            axis=1
        )
        rows_removed_empty = int(is_empty_row.sum())
        if rows_removed_empty > 0:
            df = df[~is_empty_row].reset_index(drop=True)
            changes_summary.append(f"Removed {rows_removed_empty} completely empty row(s)")

        # Step 4: String whitespace normalization & CSV injection escaping
        # Normalize repeated internal whitespace and strip leading/trailing spaces
        whitespace_trimmed_count = 0
        sanitized_formulas_count = 0

        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                new_col_vals = []
                for val in df[col]:
                    if pd.isna(val) or val is None:
                        new_col_vals.append(val)
                        continue

                    val_str = str(val)
                    # Strip leading/trailing and collapse multi-space
                    stripped = val_str.strip()
                    collapsed = re.sub(r"[ \t]+", " ", stripped)

                    if collapsed != val_str:
                        whitespace_trimmed_count += 1

                    # Neutralize potential CSV injection formulas
                    sanitized = sanitize_cell_value(collapsed)
                    if sanitized != collapsed:
                        sanitized_formulas_count += 1

                    new_col_vals.append(sanitized)
                df[col] = new_col_vals

        if whitespace_trimmed_count > 0:
            fields_normalized_count += whitespace_trimmed_count
            changes_summary.append(f"Cleaned whitespace across {whitespace_trimmed_count} text cell(s)")

        if sanitized_formulas_count > 0:
            changes_summary.append(f"Sanitized {sanitized_formulas_count} cell(s) starting with formula characters")

        # Step 5: Column-specific intelligent normalization & validation
        for col in df.columns:
            # Email columns
            if is_email_column(col, df[col]):
                normalized_emails = 0
                new_emails = []
                for idx, val in enumerate(df[col]):
                    if pd.isna(val) or val is None:
                        new_emails.append(val)
                        continue
                    val_s = str(val).strip()
                    if not val_s:
                        new_emails.append(val)
                        continue

                    # Lowercase normalization
                    lowered = val_s.lower()
                    if lowered != val_s:
                        normalized_emails += 1
                        fields_normalized_count += 1
                        new_emails.append(lowered)
                    else:
                        new_emails.append(val_s)

                    # Validation
                    if not EMAIL_REGEX.match(lowered):
                        invalid_emails_count += 1
                        invalid_values_count += 1
                        warnings.append(
                            f"Row {idx + 1}: Potentially invalid email '{val_s}' in column '{col}'"
                        )

                df[col] = new_emails
                if normalized_emails > 0:
                    changes_summary.append(f"Normalized {normalized_emails} email address(es) to lowercase in '{col}'")

            # Name columns (Title Case if all-upper or all-lower)
            elif is_name_column(col):
                names_formatted = 0
                new_names = []
                for idx, val in enumerate(df[col]):
                    if pd.isna(val) or val is None:
                        new_names.append(val)
                        continue
                    val_s = str(val).strip()
                    if not val_s:
                        new_names.append(val)
                        continue

                    # If string is entirely uppercase or lowercase and has letters, normalize to Title Case
                    if (val_s.isupper() or val_s.islower()) and re.search(r"[a-zA-Z]", val_s):
                        title_case = val_s.title()
                        if title_case != val_s:
                            new_names.append(title_case)
                            names_formatted += 1
                            fields_normalized_count += 1
                        else:
                            new_names.append(val_s)
                    else:
                        new_names.append(val_s)

                df[col] = new_names
                if names_formatted > 0:
                    changes_summary.append(f"Normalized casing for {names_formatted} name(s) in '{col}'")

            # Financial / Numeric columns
            elif is_numeric_candidate_column(col):
                numeric_converted = 0
                new_nums = []
                for idx, val in enumerate(df[col]):
                    if pd.isna(val) or val is None:
                        new_nums.append(np.nan)
                        continue

                    cleaned_num, was_normalized, is_invalid = clean_currency_or_numeric_string(val)
                    if was_normalized:
                        numeric_converted += 1
                        fields_normalized_count += 1
                    if is_invalid:
                        invalid_values_count += 1
                        warnings.append(f"Row {idx + 1}: Unrecognized numeric format '{val}' in column '{col}'")

                    new_nums.append(cleaned_num)

                # Assign converted values
                df[col] = new_nums
                # Attempt conversion to numeric type if possible
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

                if numeric_converted > 0:
                    changes_summary.append(f"Normalized {numeric_converted} currency/numeric value(s) in '{col}'")

        # Step 6: Deduplication (Exact duplicate rows on normalized dataset)
        duplicate_mask = df.duplicated(keep="first")
        duplicate_rows_removed = int(duplicate_mask.sum())
        if duplicate_rows_removed > 0:
            df = df.drop_duplicates(keep="first").reset_index(drop=True)
            changes_summary.append(f"Removed {duplicate_rows_removed} exact duplicate row(s)")

        # Step 7: Calculate final counts & metrics
        rows_final = len(df)
        null_values_count = int(df.isna().sum().sum())

        if invalid_emails_count > 0:
            changes_summary.append(f"Flagged {invalid_emails_count} potentially invalid email address(es)")

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        metrics = ProcessingMetrics(
            rows_initial=rows_initial,
            rows_final=rows_final,
            rows_removed_empty=rows_removed_empty,
            columns_removed_empty=columns_removed_empty,
            duplicate_rows_removed=duplicate_rows_removed,
            invalid_emails_count=invalid_emails_count,
            invalid_values_detected=invalid_values_count,
            fields_normalized=fields_normalized_count,
            null_values_count=null_values_count,
            processing_time_ms=execution_time_ms,
        )

        return df, metrics, changes_summary, warnings


default_processor = DataProcessor()
