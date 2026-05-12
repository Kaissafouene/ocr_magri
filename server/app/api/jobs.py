from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.job import Job

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Poll for job processing status."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status,
        "verdict": job.verdict,
        "filename": job.original_filename,
        "page_count": job.page_count,
        "created_at": job.created_at.isoformat(),
        "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
        "processing_completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
    }

    if job.error_message:
        response["error"] = job.error_message

    return response