import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage" / "processed")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Upload Constraints
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

# Storage & Cleanup Settings
STORAGE_RETENTION_SECONDS = int(os.getenv("STORAGE_RETENTION_SECONDS", "3600"))  # 1 hour
MAX_PREVIEW_ROWS = 10
