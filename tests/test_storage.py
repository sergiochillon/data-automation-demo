import os
import time
import uuid

import pandas as pd
import pytest

from app.storage import StorageManager


@pytest.fixture
def temp_storage(tmp_path):
    """StorageManager fixture operating in an isolated temporary directory."""
    return StorageManager(base_dir=tmp_path / "test_storage", retention_seconds=60)


def test_storage_save_and_retrieve(temp_storage):
    """Saving a DataFrame generates both CSV and Excel files correctly."""
    file_id = str(uuid.uuid4())
    df = pd.DataFrame([{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}])

    csv_path, xlsx_path = temp_storage.save_processed_dataset(file_id, df)
    assert csv_path.is_file()
    assert xlsx_path.is_file()

    # Retrieve paths
    retrieved_csv = temp_storage.get_file_path(file_id, "csv")
    retrieved_xlsx = temp_storage.get_file_path(file_id, "xlsx")
    assert retrieved_csv == csv_path.resolve()
    assert retrieved_xlsx == xlsx_path.resolve()


def test_storage_invalid_uuid_rejected(temp_storage):
    """Invalid UUID raises ValueError on save and returns None on retrieval."""
    df = pd.DataFrame([{"col": 1}])
    with pytest.raises(ValueError, match="Invalid file identifier"):
        temp_storage.save_processed_dataset("not-a-valid-uuid", df)

    assert temp_storage.get_file_path("not-a-valid-uuid", "csv") is None


def test_storage_invalid_format_returns_none(temp_storage):
    """Unsupported export format returns None."""
    file_id = str(uuid.uuid4())
    df = pd.DataFrame([{"col": 1}])
    temp_storage.save_processed_dataset(file_id, df)

    assert temp_storage.get_file_path(file_id, "pdf") is None
    assert temp_storage.get_file_path(file_id, "exe") is None


def test_storage_cleanup_expired_sessions(temp_storage):
    """Old session folders are pruned while fresh session folders are preserved."""
    old_id = str(uuid.uuid4())
    fresh_id = str(uuid.uuid4())
    df = pd.DataFrame([{"col": 1}])

    temp_storage.save_processed_dataset(old_id, df)
    temp_storage.save_processed_dataset(fresh_id, df)

    old_dir = temp_storage.base_dir / old_id
    fresh_dir = temp_storage.base_dir / fresh_id

    # Set old directory modification time to 2 hours ago
    past_time = time.time() - 7200
    os.utime(old_dir, (past_time, past_time))

    # Run cleanup with 3600s retention
    pruned = temp_storage.cleanup_expired_files(retention_seconds=3600)
    assert pruned == 1
    assert not old_dir.exists()
    assert fresh_dir.exists()
