from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.match_result import MatchResult
from app.models.document import Document

router = APIRouter(tags=["results"])


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get full matching results for a completed job.
    Returns all document metadata, extracted data, and line-by-line verdicts.
    """
    result = await db.execute(
        select(Job)
        .options(
            selectinload(Job.documents).selectinload(Document.line_items),
            selectinload(Job.match_result),
        )
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in (JobStatus.COMPLETED, JobStatus.REVIEW_REQUIRED):
        return {
            "job_id": job_id,
            "status": job.status,
            "message": "Processing not yet complete",
        }

    # Build response
    documents_out = []
    for doc in job.documents:
        documents_out.append({
            "doc_type": doc.doc_type,
            "pages": doc.page_numbers,
            "ref_document": doc.ref_document,
            "document_date": doc.document_date.isoformat() if doc.document_date else None,
            "supplier_name": doc.supplier_name_raw,
            "extraction_confidence": doc.extraction_confidence,
            "extraction_source_tier": doc.extraction_source_tier,
            "has_low_confidence_fields": doc.has_low_confidence_fields,
            "field_confidence_map": doc.field_confidence_map,
            "requires_review": doc.requires_review,
            "total_ht": doc.total_ht,
            "total_ttc": doc.total_ttc,
            "lines": [
                {
                    "line_number": li.line_number,
                    "ref_produit": li.ref_produit,
                    "designation": li.designation,
                    "qty": li.qty,
                    "unit": li.unit,
                    "prix_unitaire": li.prix_unitaire,
                    "tva_rate": li.tva_rate,
                    "total_ligne_ht": li.total_ligne_ht,
                    "extraction_confidence": li.extraction_confidence,
                    "field_confidence_map": li.field_confidence_map,
                }
                for li in sorted(doc.line_items, key=lambda x: x.line_number)
            ],
        })

    match_out = None
    if job.match_result:
        mr = job.match_result
        match_out = {
            "global_verdict": mr.global_verdict,
            "total_lines": mr.total_lines,
            "match_count": mr.match_count,
            "mismatch_count": mr.mismatch_count,
            "missing_count": mr.missing_count,
            "extra_count": mr.extra_count,
            "low_confidence_count": mr.low_confidence_count,
            "used_fuzzy_link": mr.used_fuzzy_link,
            "bc_to_bl_link_confidence": mr.bc_to_bl_link_confidence,
            "bc_to_facture_link_confidence": mr.bc_to_facture_link_confidence,
            "line_verdicts": mr.line_verdicts,
        }

    return {
        "job_id": job_id,
        "status": job.status,
        "verdict": job.verdict,
        "documents": documents_out,
        "match_result": match_out,
    }