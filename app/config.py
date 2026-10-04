import logging
import os
import sys
from pathlib import Path

# Base Paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage" / "processed")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Upload Constraints
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS: set[str] = {".csv", ".xlsx"}

# Storage & Cleanup Settings
STORAGE_RETENTION_SECONDS: int = int(os.getenv("STORAGE_RETENTION_SECONDS", "3600"))  # 1 hour
MAX_PREVIEW_ROWS: int = int(os.getenv("MAX_PREVIEW_ROWS", "10"))

# Logging Settings
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()


def configure_logging() -> None:
    """Configures structured application logging using standard library."""
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
