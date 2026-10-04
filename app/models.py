from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ProcessingMetrics(BaseModel):
    rows_initial: int = Field(..., description="Total rows in original input")
    rows_final: int = Field(..., description="Cleaned rows retained")
    rows_removed_empty: int = Field(0, description="Count of completely empty rows dropped")
    columns_removed_empty: int = Field(0, description="Count of completely empty columns dropped")
    duplicate_rows_removed: int = Field(0, description="Exact duplicate rows eliminated")
    invalid_emails_count: int = Field(0, description="Invalid email formats flagged")
    invalid_values_detected: int = Field(0, description="Total anomalous or invalid values flagged")
    fields_normalized: int = Field(0, description="Individual cell transformations applied")
    null_values_count: int = Field(0, description="Count of missing/null cells in final dataset")
    processing_time_ms: float = Field(..., description="Execution time in milliseconds")


class ProcessingResult(BaseModel):
    file_id: str
    original_filename: str
    processed_at: str
    metrics: ProcessingMetrics
    changes_summary: List[str]
    warnings: List[str]
    columns: List[str]
    sample_preview: List[Dict[str, Any]]
    csv_download_url: str
    xlsx_download_url: str


class HealthStatus(BaseModel):
    status: str
    version: str
    service: str
