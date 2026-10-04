from typing import Any

from pydantic import BaseModel, Field


class ProcessingMetrics(BaseModel):
    """Auditable quantitative metrics summarizing data pipeline execution."""

    rows_initial: int = Field(..., description="Total rows in original input file")
    rows_final: int = Field(..., description="Cleaned rows retained in output")
    rows_removed_empty: int = Field(0, description="Count of completely empty rows dropped")
    columns_removed_empty: int = Field(0, description="Count of completely empty columns dropped")
    duplicate_rows_removed: int = Field(0, description="Exact duplicate rows eliminated")
    invalid_emails_count: int = Field(0, description="Invalid email formats flagged")
    invalid_values_detected: int = Field(0, description="Total anomalous or invalid values flagged")
    fields_normalized: int = Field(0, description="Individual cell transformations applied")
    null_values_count: int = Field(0, description="Count of missing/null cells in final dataset")
    processing_time_ms: float = Field(..., description="Execution time in milliseconds")


class ProcessingResult(BaseModel):
    """Full API response payload after processing a dataset."""

    file_id: str = Field(..., description="Unique UUID for downloading processed artifacts")
    original_filename: str = Field(..., description="Original name of the uploaded file")
    processed_at: str = Field(..., description="ISO 8601 UTC timestamp of completion")
    metrics: ProcessingMetrics = Field(..., description="Quantitative execution metrics")
    changes_summary: list[str] = Field(..., description="Itemized audit list of transformations")
    warnings: list[str] = Field(..., description="Data quality issues flagged for review")
    columns: list[str] = Field(..., description="Cleaned output column names")
    sample_preview: list[dict[str, Any]] = Field(..., description="First records preview")
    csv_download_url: str = Field(..., description="Relative download URL for clean CSV")
    xlsx_download_url: str = Field(..., description="Relative download URL for clean Excel")


class HealthStatus(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service status indicator")
    version: str = Field(..., description="API semantic version")
    service: str = Field(..., description="Service identifier")
