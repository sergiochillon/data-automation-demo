import re
import uuid
from pathlib import Path
from typing import Tuple

from app.config import ALLOWED_EXTENSIONS

SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-. ]+$")
UUID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE)

# Characters commonly exploited for CSV Formula Injection
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if the provided string is a valid UUID4 representation."""
    if not uuid_str or not isinstance(uuid_str, str):
        return False
    return bool(UUID_PATTERN.match(uuid_str))


def validate_file_metadata(filename: str, file_size: int, max_bytes: int) -> Tuple[bool, str]:
    """
    Validates file extension, path safety, and byte size.
    Returns (is_valid, error_message).
    """
    if not filename or not filename.strip():
        return False, "File name cannot be empty."

    # Extract clean filename without path traversal segments
    clean_name = Path(filename).name
    if clean_name != filename and ("/" in filename or "\\" in filename):
        return False, "Path traversal sequences detected in filename."

    ext = Path(clean_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(ALLOWED_EXTENSIONS)
        return False, f"Unsupported file extension '{ext}'. Only {allowed_list} are permitted."

    if file_size <= 0:
        return False, "File is completely empty (0 bytes)."

    if file_size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        return False, f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."

    return True, ""


def sanitize_cell_value(val: object) -> object:
    """
    Neutralize CSV / Excel formula injection risks in string cells.
    If a string starts with formula triggers (=, +, -, @, tab, cr) and is not
    a legitimate scalar number, prepend a single quote prefix to prevent automatic execution.
    """
    if val is None or not isinstance(val, str):
        return val

    s = val.strip()
    if not s:
        return val

    # If it starts with any formula prefix
    if s.startswith(FORMULA_PREFIXES):
        # Allow benign signed numbers, e.g. -45.50 or +123
        # Test if string represents a genuine float/int
        cleaned_num = s.replace(",", "")
        try:
            float(cleaned_num)
            return val
        except ValueError:
            pass

        # Also check international phone numbers starting with + followed only by digits, spaces, hyphens, parentheses
        if s.startswith("+") and re.match(r"^\+[\d\s().-]{6,25}$", s):
            return val

        # Otherwise prepend single quote to neutralize spreadsheet execution
        return "'" + val

    return val
