import logging
import shutil
import time
from pathlib import Path

import pandas as pd

from app.config import STORAGE_DIR, STORAGE_RETENTION_SECONDS
from app.security import is_valid_uuid

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages temporary persistence, secure file retrieval, and lifecycle
    cleanup of processed dataset artifacts on local filesystem.
    """

    def __init__(
        self,
        base_dir: Path = STORAGE_DIR,
        retention_seconds: int = STORAGE_RETENTION_SECONDS,
    ):
        self.base_dir = base_dir
        self.retention_seconds = retention_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_processed_dataset(self, file_id: str, df: pd.DataFrame) -> tuple[Path, Path]:
        """
        Persists clean DataFrame into both CSV and XLSX formats under
        a dedicated UUID-scoped directory.

        Args:
            file_id: Validated UUID identifier for the session.
            df: Cleaned pandas DataFrame.

        Returns:
            Tuple of (csv_path, xlsx_path).
        """
        if not is_valid_uuid(file_id):
            raise ValueError(f"Invalid file identifier '{file_id}'.")

        target_dir = self.base_dir / file_id
        target_dir.mkdir(parents=True, exist_ok=True)

        csv_path = target_dir / "cleaned_data.csv"
        xlsx_path = target_dir / "cleaned_data.xlsx"

        # Export CSV (UTF-8 encoded, index excluded)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Export Excel via openpyxl
        df.to_excel(xlsx_path, index=False, engine="openpyxl")

        logger.info("Persisted clean dataset artifacts for session %s", file_id)
        return csv_path, xlsx_path

    def get_file_path(self, file_id: str, file_format: str) -> Path | None:
        """
        Safely retrieves the Path to an exported file.
        Guarantees that the resolved path is within base_dir to block directory traversal.

        Args:
            file_id: Session UUID.
            file_format: File format ('csv' or 'xlsx').

        Returns:
            Resolved Path if valid and existing, None otherwise.
        """
        if not is_valid_uuid(file_id):
            return None

        format_clean = file_format.lower().lstrip(".")
        if format_clean not in ("csv", "xlsx"):
            return None

        target_file = self.base_dir / file_id / f"cleaned_data.{format_clean}"

        try:
            resolved = target_file.resolve()
            base_resolved = self.base_dir.resolve()
            if not resolved.is_file() or not resolved.is_relative_to(base_resolved):
                return None
            return resolved
        except (ValueError, OSError):
            return None

    def cleanup_expired_files(self, retention_seconds: int | None = None) -> int:
        """
        Removes temporary session directories older than the specified retention window.

        Args:
            retention_seconds: Optional override for retention threshold in seconds.

        Returns:
            Count of expired session directories pruned.
        """
        effective_retention = (
            retention_seconds if retention_seconds is not None else self.retention_seconds
        )
        now = time.time()
        removed_count = 0

        if not self.base_dir.exists():
            return 0

        for item in self.base_dir.iterdir():
            if item.is_dir() and is_valid_uuid(item.name):
                try:
                    mtime = item.stat().st_mtime
                    if (now - mtime) > effective_retention:
                        shutil.rmtree(item, ignore_errors=True)
                        removed_count += 1
                        logger.info("Pruned expired session directory: %s", item.name)
                except (OSError, PermissionError) as exc:
                    logger.warning("Failed to prune directory %s: %s", item.name, exc)
                    continue

        return removed_count


default_storage = StorageManager()
