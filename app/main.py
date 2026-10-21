import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    ALLOWED_EXTENSIONS,
    MAX_PREVIEW_ROWS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    configure_logging,
)
from app.models import HealthStatus, ProcessingResult
from app.processor import (
    DataProcessingError,
    default_processor,
    load_dataframe_from_bytes,
)
from app.security import is_valid_uuid, validate_file_metadata
from app.storage import default_storage

# Initialize structured logging
configure_logging()
logger = logging.getLogger("app.main")

# Base filesystem directories
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: clean up expired storage artifacts on startup and shutdown."""
    logger.info("Initializing Data Processing Tool API...")
    pruned = default_storage.cleanup_expired_files()
    logger.info("Startup storage prune complete. Removed %d expired sessions.", pruned)
    yield
    logger.info("Shutting down Data Processing Tool API.")


app = FastAPI(
    title="Data Processing Tool API",
    description=(
        "Business-grade automated CSV & Excel data cleaning, normalization, and validation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthStatus, tags=["System"])
async def health_check() -> HealthStatus:
    """Returns service health status and API version metadata."""
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        service="data-automation-demo",
    )


@app.post("/api/process", response_model=ProcessingResult, tags=["Processing"])
async def process_dataset(file: UploadFile = File(...)) -> ProcessingResult:
    """
    Accepts an uploaded .csv or .xlsx business dataset, executes deterministic
    cleaning and validation, and returns audit metrics, change logs, and download paths.
    """
    # Periodic pruning of expired sessions
    default_storage.cleanup_expired_files()

    filename = file.filename or "uploaded_data"

    # Fast extension pre-check before reading request body
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        logger.warning("Rejected upload with disallowed extension '%s'", ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Permitted extensions: {allowed_list}",
        )

    # Stream file bytes with strict size limit to prevent memory exhaustion / DoS
    chunk_size = 1024 * 1024  # 1 MB chunk buffer
    total_bytes = bytearray()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes.extend(chunk)
        if len(total_bytes) > MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "Upload '%s' exceeded size limit of %d MB",
                filename,
                MAX_UPLOAD_SIZE_MB,
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB.",
            )

    file_bytes = bytes(total_bytes)

    # Validate filename safety and byte size
    is_valid, error_msg = validate_file_metadata(filename, len(file_bytes), MAX_UPLOAD_SIZE_BYTES)
    if not is_valid:
        logger.warning("Metadata validation failure for '%s': %s", filename, error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Parse raw bytes into DataFrame
    try:
        raw_df = load_dataframe_from_bytes(file_bytes, filename)
    except DataProcessingError as e:
        logger.warning("Data parsing failed for '%s': %s", filename, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Unexpected parsing exception for '%s': %s", filename, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read file content: {e}",
        ) from e

    # Execute deterministic cleaning pipeline
    try:
        cleaned_df, metrics, changes_summary, warnings = default_processor.process(raw_df, filename)
    except Exception as e:
        logger.error("Pipeline failure for '%s': %s", filename, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed internally: {e}",
        ) from e

    # Persist cleaned artifacts under UUID session token
    session_id = str(uuid.uuid4())
    try:
        default_storage.save_processed_dataset(session_id, cleaned_df)
    except Exception as e:
        logger.error("Failed to save artifacts for session %s: %s", session_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist processed dataset: {e}",
        ) from e

    # Prepare JSON-safe preview records
    preview_df = cleaned_df.head(MAX_PREVIEW_ROWS).copy()
    preview_df = preview_df.replace({float("nan"): None})
    sample_preview: list[dict[str, Any]] = preview_df.to_dict(orient="records")

    return ProcessingResult(
        file_id=session_id,
        original_filename=Path(filename).name,
        processed_at=datetime.now(UTC).isoformat(),
        metrics=metrics,
        changes_summary=changes_summary,
        warnings=warnings,
        columns=list(cleaned_df.columns),
        sample_preview=sample_preview,
        csv_download_url=f"/api/download/{session_id}/csv",
        xlsx_download_url=f"/api/download/{session_id}/xlsx",
    )


@app.get("/api/download/{file_id}/{file_format}", tags=["Downloads"])
async def download_cleaned_file(file_id: str, file_format: str) -> FileResponse:
    """
    Streams the clean dataset in either CSV or Excel (.xlsx) format.
    Enforces strict UUID validation and directory containment to block traversal attacks.
    """
    if not is_valid_uuid(file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file identifier format.",
        )

    clean_format = file_format.lower().lstrip(".")
    if clean_format not in ("csv", "xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format requested. Available: 'csv' or 'xlsx'.",
        )

    file_path = default_storage.get_file_path(file_id, clean_format)
    if not file_path or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or session has expired.",
        )

    media_types = {
        "csv": "text/csv; charset=utf-8",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return FileResponse(
        path=str(file_path),
        filename=f"cleaned_data.{clean_format}",
        media_type=media_types.get(clean_format, "application/octet-stream"),
    )


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if DEMO_DIR.exists():
    app.mount("/demo-data", StaticFiles(directory=str(DEMO_DIR)), name="demo-data")


@app.get("/", tags=["UI"])
async def serve_index() -> FileResponse:
    """Serves the main application single-page interface."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UI template not found.",
        )
    return FileResponse(index_file)
