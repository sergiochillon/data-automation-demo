import re
import uuid
from pathlib import Path

from app.config import ALLOWED_EXTENSIONS

SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-. ]+$")
UUID_PATTERN = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-[4][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$", re.IGNORECASE
)

# Characters commonly exploited for CSV / Excel Formula Injection (DDE / OWASP)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def is_valid_uuid(uuid_str: str) -> bool:
    """
    Validates whether the provided string is a syntactically valid UUID (v4).

    Returns:
        True if valid UUID v4, False otherwise.
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False
    try:
        parsed = uuid.UUID(uuid_str, version=4)
        return str(parsed).lower() == uuid_str.lower()
    except (ValueError, AttributeError):
        return False


def validate_file_metadata(filename: str, file_size: int, max_bytes: int) -> tuple[bool, str]:
    """
    Validates upload safety constraints:
    - Non-empty filename
    - Null-byte avoidance
    - Path traversal defense
    - Extension whitelisting
    - Positive size within maximum byte ceiling

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not filename or not filename.strip():
        return False, "File name cannot be empty."

    if "\x00" in filename:
        return False, "File name contains invalid null bytes."

    # Prevent absolute paths or directory traversal sequences
    clean_name = Path(filename).name
    if clean_name != filename or "/" in filename or "\\" in filename or ".." in filename:
        return False, "Path traversal sequences detected in filename."

    ext = Path(clean_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"Unsupported file extension '{ext}'. Only {allowed_list} are permitted."

    if file_size <= 0:
        return False, "File is completely empty (0 bytes)."

    if file_size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        return False, f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."

    return True, ""


def sanitize_cell_value(val: object) -> object:
    """
    Neutralizes CSV / Excel formula injection (DDE attacks) in string cells.

    If a text value begins with an execution trigger (=, +, -, @, \\t, \\r)
    and does not evaluate to a legitimate scalar number or phone number,
    prepends a single quote (') to force spreadsheet processors to interpret
    the cell as literal text rather than executable syntax.
    """
    if val is None or not isinstance(val, str):
        return val

    s = val.strip()
    if not s:
        return val

    if s.startswith(FORMULA_PREFIXES):
        # 1. Allow legitimate signed numbers (e.g., -45.50, +123, -1,250.00)
        cleaned_num = s.replace(",", "")
        try:
            float(cleaned_num)
            return val
        except ValueError:
            pass

        # 2. Allow international telephone numbers (e.g., +1-555-0199, +44 20 7946 0912)
        if s.startswith("+") and re.match(r"^\+[\d\s().-]{6,25}$", s):
            return val

        # 3. Prepend single quote to neutralize formula execution in Excel/Calc
        return "'" + val

    return val
