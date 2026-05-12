import hashlib
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import storage_client
from app.core.config import settings
from app.models.job import Job, JobStatus
from app.workers.pipeline import process_document_pipeline, run_pipeline_local
from app.utils.pdf_utils import get_page_count
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["upload"])


@router.post("/jobs/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uploaded_by: str = "anonymous",
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF for processing.
    Returns job_id immediately. Processing happens asynchronously.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted",
        )
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_pdf_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_pdf_size_bytes // 1024 // 1024}MB",
        )

    # Basic PDF header check basict tnajm t3mlo improve 
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not appear to be a valid PDF",
        )
    try:
        page_count = get_page_count(file_bytes)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read PDF structure — file may be corrupted",
        )

    if page_count > settings.max_pdf_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF has {page_count} pages — maximum is {settings.max_pdf_pages}",
        )

    job = Job(
        status=JobStatus.PENDING,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
        page_count=page_count,
        original_pdf_key="", 
        original_pdf_hash=hashlib.sha256(file_bytes).hexdigest(),
        uploaded_by=uploaded_by,
    )
    db.add(job)
    await db.flush() 
    storage_key = storage_client.upload_pdf(job.id, file_bytes)
    job.original_pdf_key = storage_key

    await db.commit()
    await db.refresh(job)

    logger.info("job_created", job_id=job.id, filename=file.filename, pages=page_count)


    if settings.task_mode.lower() == "local":
        background_tasks.add_task(run_pipeline_local, job.id)
    else:
        try:
            process_document_pipeline.apply_async(
                args=[job.id],
                queue="pdf_processing",
                task_id=f"pipeline_{job.id}",
            )
        except Exception:
            logger.warning("celery_dispatch_failed_falling_back_local", job_id=job.id, exc_info=True)
            background_tasks.add_task(run_pipeline_local, job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "filename": file.filename,
        "page_count": page_count,
        "message": "Document accepted for processing",
    }
