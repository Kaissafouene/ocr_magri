from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.job import Job, JobStatus, GlobalVerdict
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.workers.pipeline import process_document_pipeline

router = APIRouter(tags=["admin"])


class ReviewDecision(BaseModel):
    reviewer_id: str
    approved: bool
    notes: Optional[str] = None
    corrected_doc_type: Optional[str] = None  # For page re-classification


@router.patch("/jobs/{job_id}/review")
async def submit_review(
    job_id: str,
    decision: ReviewDecision,
    db: AsyncSession = Depends(get_db),
):
    """
    Human review endpoint.
    Called by accounting team to approve/reject a flagged job.
    All decisions are written to the immutable audit log.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in (JobStatus.REVIEW_REQUIRED, JobStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job status is {job.status} — review not applicable",
        )

    audit_entry = AuditLog(
        job_id=job_id,
        event_type="HUMAN_REVIEW_COMPLETED",
        event_data={
            "reviewer_id": decision.reviewer_id,
            "approved": decision.approved,
            "notes": decision.notes,
            "corrected_doc_type": decision.corrected_doc_type,
            "previous_status": job.status,
            "previous_verdict": job.verdict,
        },
        actor=decision.reviewer_id,
    )
    db.add(audit_entry)
    if decision.approved:
        job.status = JobStatus.COMPLETED
        job.verdict = GlobalVerdict.VALIDATED
    else:
        job.status = JobStatus.FAILED
        job.verdict = GlobalVerdict.REJECTED

    await db.commit()

    return {
        "job_id": job_id,
        "new_status": job.status,
        "new_verdict": job.verdict,
        "reviewed_by": decision.reviewer_id,
        "message": "Review decision recorded",
    }


@router.get("/jobs/{job_id}/audit")
async def get_audit_trail(job_id: str, db: AsyncSession = Depends(get_db)):
    """Return the full immutable audit log for a job."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.job_id == job_id)
        .order_by(AuditLog.created_at.asc())
    )
    logs = result.scalars().all()

    if not logs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No audit logs found")

    return {
        "job_id": job_id,
        "audit_trail": [
            {
                "event_type": log.event_type,
                "actor": log.actor,
                "timestamp": log.created_at.isoformat(),
                "data": log.event_data,
            }
            for log in logs
        ],
    }