import time
import shutil
from pathlib import Path
from typing import Optional
import pandas as pd

from app.config import STORAGE_DIR, STORAGE_RETENTION_SECONDS
from app.security import is_valid_uuid

TuplePath = tuple[Path, Path]


class StorageManager:
    def __init__(self, base_dir: Path = STORAGE_DIR, retention_seconds: int = STORAGE_RETENTION_SECONDS):
        self.base_dir = base_dir
        self.retention_seconds = retention_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_processed_dataset(self, file_id: str, df: pd.DataFrame) -> TuplePath:
        """
        Saves the processed pandas DataFrame in both CSV and XLSX formats
        under a dedicated UUID directory.
        """
        if not is_valid_uuid(file_id):
            raise ValueError("Invalid file identifier.")

        target_dir = self.base_dir / file_id
        target_dir.mkdir(parents=True, exist_ok=True)

        csv_path = target_dir / "cleaned_data.csv"
        xlsx_path = target_dir / "cleaned_data.xlsx"

        # Export CSV (utf-8 with BOM or plain utf-8; index=False)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Export Excel via openpyxl
        df.to_excel(xlsx_path, index=False, engine="openpyxl")

        return csv_path, xlsx_path

    def get_file_path(self, file_id: str, file_format: str) -> Optional[Path]:
        """
        Safely resolves the path to an exported file.
        Returns None if the ID is invalid or the file is not found.
        """
        if not is_valid_uuid(file_id):
            return None

        format_clean = file_format.lower().lstrip(".")
        if format_clean not in ("csv", "xlsx"):
            return None

        target_file = self.base_dir / file_id / f"cleaned_data.{format_clean}"

        # Resolve to prevent any symlink traversal outside base_dir
        try:
            resolved = target_file.resolve()
            if not resolved.is_file() or not str(resolved).startswith(str(self.base_dir.resolve())):
                return None
            return resolved
        except (ValueError, OSError):
            return None

    def cleanup_expired_files(self) -> int:
        """
        Removes temporary directories older than the retention threshold.
        Returns the number of removed session directories.
        """
        now = time.time()
        removed_count = 0

        if not self.base_dir.exists():
            return 0

        for item in self.base_dir.iterdir():
            if item.is_dir() and is_valid_uuid(item.name):
                try:
                    mtime = item.stat().st_mtime
                    if now - mtime > self.retention_seconds:
                        shutil.rmtree(item, ignore_errors=True)
                        removed_count += 1
                except (OSError, PermissionError):
                    continue

        return removed_count


default_storage = StorageManager()
