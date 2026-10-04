import uuid

from app.security import (
    is_valid_uuid,
    sanitize_cell_value,
    validate_file_metadata,
)


def test_is_valid_uuid():
    """Confirms strict UUID v4 validation."""
    valid = str(uuid.uuid4())
    assert is_valid_uuid(valid) is True
    assert is_valid_uuid("not-a-uuid") is False
    assert is_valid_uuid("../etc/passwd") is False
    assert is_valid_uuid("") is False
    assert is_valid_uuid(None) is False
    assert is_valid_uuid("12345678-1234-1234-1234-1234567890ab") is False  # Not v4


def test_validate_file_metadata():
    """Confirms upload security constraints and checks."""
    max_bytes = 15 * 1024 * 1024

    # Valid files
    ok, _ = validate_file_metadata("test.csv", 1024, max_bytes)
    assert ok is True
    ok, _ = validate_file_metadata("data.XLSX", 2048, max_bytes)
    assert ok is True

    # Empty filename
    ok, msg = validate_file_metadata("", 1024, max_bytes)
    assert ok is False
    assert "empty" in msg

    # Whitespace-only filename
    ok, msg = validate_file_metadata("   ", 1024, max_bytes)
    assert ok is False
    assert "empty" in msg

    # Null bytes in filename
    ok, msg = validate_file_metadata("test\x00.csv", 1024, max_bytes)
    assert ok is False
    assert "null bytes" in msg

    # Path traversal in filename
    ok, msg = validate_file_metadata("../../etc/shadow.csv", 1024, max_bytes)
    assert ok is False
    assert "Path traversal" in msg

    ok, msg = validate_file_metadata("/var/log/data.csv", 1024, max_bytes)
    assert ok is False
    assert "Path traversal" in msg

    # Disallowed extensions
    ok, msg = validate_file_metadata("malicious.exe", 1024, max_bytes)
    assert ok is False
    assert "Unsupported file extension" in msg

    ok, msg = validate_file_metadata("document.pdf", 1024, max_bytes)
    assert ok is False

    # Zero bytes
    ok, msg = validate_file_metadata("test.csv", 0, max_bytes)
    assert ok is False
    assert "0 bytes" in msg

    # Oversized file
    ok, msg = validate_file_metadata("huge.csv", max_bytes + 1, max_bytes)
    assert ok is False
    assert "exceeds" in msg


def test_csv_injection_sanitization():
    """Confirms neutralization of spreadsheet formula injection vectors."""
    # Formulas that must be escaped
    assert sanitize_cell_value("=1+2") == "'=1+2"
    assert sanitize_cell_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_cell_value("@calc") == "'@calc"
    assert sanitize_cell_value("-cmd|' /C calc'!A0") == "'-cmd|' /C calc'!A0"
    assert sanitize_cell_value("\t=1+2") == "'\t=1+2"
    assert sanitize_cell_value("\r+calc") == "'\r+calc"

    # Legitimate scalar numbers should NOT be prepended with quote
    assert sanitize_cell_value("-45.50") == "-45.50"
    assert sanitize_cell_value("+123") == "+123"
    assert sanitize_cell_value("-1,250.00") == "-1,250.00"

    # Legitimate phone numbers should NOT be prepended
    assert sanitize_cell_value("+1-555-0199") == "+1-555-0199"
    assert sanitize_cell_value("+44 20 7946 0912") == "+44 20 7946 0912"

    # Normal strings
    assert sanitize_cell_value("Regular Company Name") == "Regular Company Name"
    assert sanitize_cell_value(12345) == 12345
    assert sanitize_cell_value(None) is None
    assert sanitize_cell_value("") == ""
