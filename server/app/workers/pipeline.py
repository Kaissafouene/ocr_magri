"""
Main processing pipeline — orchestrates all layers in sequence.
Runs in the pdf_processing Celery queue (CPU-bound workers).
"""
import asyncio
from datetime import datetime, timezone
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.storage import storage_client
from app.core.logging import get_logger
from app.core.config import settings

from app.models.job import Job, JobStatus, GlobalVerdict as JobGlobalVerdict
from app.models.document import Document, DocumentType, ExtractionSourceTier, PageSourceType
from app.models.line_item import LineItem
from app.models.match_result import MatchResult
from app.models.audit_log import AuditLog

from app.utils.pdf_utils import analyze_pdf_pages, extract_page_as_image
from app.services.preprocessor import preprocess_page_image
from app.services.ocr_engine import run_tesseract
from app.services.classifier import classify_page, DocType
from app.services.page_grouper import (
    group_pages_into_documents, PageClassified, extract_ref_hint
)
from app.services.supplier_service import get_supplier_from_text
from app.services.extractor import (
    extract_document_template, extract_document_llm, map_llm_result_to_schema
)
from app.services.validator import validate_bc, validate_bl, validate_facture, validate_date_ordering
from app.services.matcher import run_three_way_match
from app.schemas.documents import BonDeCommandeSchema, BonDeLivraison, FactureSchema, DocumentType as SchemaDocType

logger = get_logger(__name__)


def run_async(coro):
    """Run async coroutine from a sync task context."""
    return asyncio.run(coro)


@celery_app.task(
    bind=True,
    name="app.workers.pipeline.process_document_pipeline",
    queue="pdf_processing",
    max_retries=2,
    default_retry_delay=15,
    acks_late=True,
)
def process_document_pipeline(self: Task, job_id: str) -> dict:
    """
    Full pipeline task. Runs synchronously in Celery but uses asyncio internally
    for database operations.
    """
    logger.info("pipeline_started", job_id=job_id)

    try:
        return run_async(_run_pipeline(job_id))
    except Exception as exc:
        logger.error("pipeline_failed", job_id=job_id, error=str(exc), exc_info=True)
        run_async(_mark_job_failed(job_id, str(exc)))
        raise self.retry(exc=exc)


def run_pipeline_local(job_id: str) -> dict:
    """
    Local dev fallback when Celery/Redis is not available.
    Runs the same pipeline in-process from a background thread.
    """
    logger.info("pipeline_started_local", job_id=job_id)
    try:
        return run_async(_run_pipeline(job_id))
    except Exception as exc:
        logger.error("pipeline_failed_local", job_id=job_id, error=str(exc), exc_info=True)
        run_async(_mark_job_failed(job_id, str(exc)))
        return {
            "job_id": job_id,
            "status": "FAILED",
            "reason": str(exc),
        }


async def _run_pipeline(job_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        # ── Update job status ──────────────────────────────────────────
        job = await _get_job(db, job_id)
        job.status = JobStatus.PROCESSING
        job.processing_started_at = datetime.now(timezone.utc)
        await db.commit()

        await _audit(db, job_id, "PIPELINE_STARTED", {"job_id": job_id})

        # ── Layer 0: Download PDF ──────────────────────────────────────
        pdf_bytes = storage_client.download_pdf(job.original_pdf_key)

        # ── Layer 1: PDF Analysis — native vs scanned ──────────────────
        page_analyses = analyze_pdf_pages(pdf_bytes)
        await _audit(db, job_id, "PDF_ANALYZED", {
            "page_count": len(page_analyses),
            "native_pages": sum(1 for p in page_analyses if p.source_type.value == "NATIVE"),
            "scanned_pages": sum(1 for p in page_analyses if p.source_type.value == "SCANNED"),
        })

        # ── Layers 2–3: Preprocess + Classify each page ────────────────
        job.status = JobStatus.CLASSIFYING
        await db.commit()
        classified_pages: list[PageClassified] = []
        for page_analysis in page_analyses:
            page_num = page_analysis.page_number

            if page_analysis.source_type.value == "NATIVE":
                page_text = page_analysis.raw_text
            else:
                raw_image = extract_page_as_image(pdf_bytes, page_num, dpi=300)
                processed_image = preprocess_page_image(raw_image)
                storage_client.upload_page_image(job_id, page_num, processed_image)
                ocr_result = run_tesseract(processed_image)
                page_text = ocr_result.full_text
            classification = await classify_page(page_text)
            await _audit(db, job_id, "PAGE_CLASSIFIED", {
                "page_number": page_num,
                "doc_type": classification.doc_type,
                "confidence": classification.confidence,
                "source_tier": classification.source_tier,
                "source_type": page_analysis.source_type.value,
            })
            if classification.doc_type == DocType.UNKNOWN:
                job.status = JobStatus.REVIEW_REQUIRED
                await db.commit()
                await _audit(db, job_id, "PAGE_REQUIRES_HUMAN_CLASSIFICATION", {
                    "page_number": page_num,
                    "reasoning": classification.reasoning,
                })
            ref_hint = extract_ref_hint(page_text)
            classified_pages.append(PageClassified(
                page_number=page_num,
                doc_type=classification.doc_type,
                confidence=classification.confidence,
                source_tier=classification.source_tier,
                raw_text=page_text,
                ref_hint=ref_hint,
            ))

        # ── Layer 4: Group pages into document units ───────────────────
        document_groups = group_pages_into_documents(classified_pages)

        await _audit(db, job_id, "PAGES_GROUPED", {
            "groups": [
                {"doc_type": g.doc_type, "pages": g.pages, "ref_hint": g.ref_document}
                for g in document_groups
            ]
        })

        # ── Layer 5: Extract each document group ──────────────────────
        job.status = JobStatus.EXTRACTING
        await db.commit()

        extracted_documents: dict[str, BonDeCommandeSchema | BonDeLivraison | FactureSchema] = {}

        for group in document_groups:
            if group.doc_type == DocType.UNKNOWN:
                continue # TODO: Handle unknown doc type
            header_text = group.combined_text[:500]
            supplier_profile = await get_supplier_from_text(header_text, db)
            schema_doc_type = SchemaDocType(group.doc_type.value)
            extracted = extract_document_template(group, supplier_profile)

            if extracted is None or extracted.extraction_confidence < 0.60:
                await _audit(db, job_id, "LLM_FALLBACK_TRIGGERED", {
                    "doc_type": group.doc_type,
                    "pages": group.pages,
                    "reason": "Template extraction confidence too low or failed",
                })
                raw_llm = await extract_document_llm(group)
                if raw_llm:
                    extracted = map_llm_result_to_schema(raw_llm, schema_doc_type)

                    if extracted is None:
                        from pydantic import ValidationError
                        raw_llm_retry = await extract_document_llm(
                            group,
                            validation_error="Previous extraction returned incomplete data. Ensure all required fields are present."
                        )
                        if raw_llm_retry:
                            extracted = map_llm_result_to_schema(raw_llm_retry, schema_doc_type)

            if extracted is None:
                await _audit(db, job_id, "EXTRACTION_FAILED", {
                    "doc_type": group.doc_type,
                    "pages": group.pages,
                })
                job.status = JobStatus.REVIEW_REQUIRED
                await db.commit()
                continue

            # ── Layer 6: Correction + Normalization already applied in extractor ──

            # ── Layer 7: Validation ───────────────────────────────────
            if isinstance(extracted, BonDeCommandeSchema):
                val_result = validate_bc(extracted)
                extracted_documents["BC"] = extracted
            elif isinstance(extracted, BonDeLivraison):
                val_result = validate_bl(extracted)
                extracted_documents["BL"] = extracted
            elif isinstance(extracted, FactureSchema):
                val_result = validate_facture(extracted)
                extracted_documents["FACTURE"] = extracted
            else:
                continue

            await _audit(db, job_id, "DOCUMENT_VALIDATED", {
                "doc_type": group.doc_type,
                "is_valid": val_result.is_valid,
                "errors": val_result.errors,
                "warnings": val_result.warnings,
            })
            doc_model = Document(
                job_id=job_id,
                doc_type=DocumentType(group.doc_type.value),
                page_numbers=group.pages,
                classification_confidence=group.classification_confidence,
                classification_source_tier=group.source_tier,
                extraction_confidence=extracted.extraction_confidence,
                extraction_source_tier=ExtractionSourceTier(extracted.extraction_source_tier.value),
                has_low_confidence_fields=extracted.has_low_confidence_fields,
                supplier_id=supplier_profile.id if supplier_profile else None,
                supplier_name_raw=extracted.supplier_name if hasattr(extracted, "supplier_name") else None,
                ref_document=_get_ref(extracted),
                ref_bc_linked=extracted.ref_bc_linked if hasattr(extracted, "ref_bc_linked") else None,
                document_date=extracted.document_date,
                total_ht=float(extracted.total_ht) if hasattr(extracted, "total_ht") and extracted.total_ht else None,
                total_ttc=float(extracted.total_ttc) if hasattr(extracted, "total_ttc") and extracted.total_ttc else None,
                tva_rate=float(extracted.tva_rate) if hasattr(extracted, "tva_rate") and extracted.tva_rate else None,
                raw_extracted_data=extracted.model_dump(mode="json"),
                field_confidence_map=extracted.field_confidence_map,
                requires_review=not val_result.is_valid or extracted.has_low_confidence_fields,
            )
            db.add(doc_model)
            await db.flush()
            for li in extracted.lines:
                li_model = LineItem(
                    document_id=doc_model.id,
                    line_number=li.line_number,
                    ref_produit=li.ref_produit,
                    ref_produit_normalized=li.ref_produit_normalized,
                    designation=li.designation,
                    qty=float(li.qty) if li.qty else None,
                    unit=li.unit,
                    prix_unitaire=float(li.prix_unitaire) if li.prix_unitaire else None,
                    tva_rate=float(li.tva_rate) if li.tva_rate else None,
                    total_ligne_ht=float(li.total_ligne_ht) if li.total_ligne_ht else None,
                    field_confidence_map=li.field_confidence_map,
                    extraction_confidence=li.extraction_confidence,
                    has_low_confidence=li.has_low_confidence,
                )
                db.add(li_model)

        await db.commit()

        # ── Layer 8: Matching ─────────────────────────────────────────
        if "BC" not in extracted_documents:
            await _mark_job_failed(job_id, "No BC (Purchase Order) found in document")
            return {"job_id": job_id, "status": "FAILED", "reason": "No BC found"}

        job.status = JobStatus.MATCHING
        await db.commit()

        bc = extracted_documents.get("BC")
        bl = extracted_documents.get("BL")
        facture = extracted_documents.get("FACTURE")
        date_warnings = validate_date_ordering(bc, bl, facture)
        if date_warnings:
            await _audit(db, job_id, "DATE_ORDER_WARNING", {"warnings": date_warnings})
        supplier_price_tol = None
        supplier_qty_tol = None
        if bl and bl.supplier_name:
            supplier_profile = await get_supplier_from_text(bl.supplier_name, db)
            if supplier_profile:
                supplier_price_tol = supplier_profile.price_tolerance
                supplier_qty_tol = supplier_profile.quantity_tolerance

        match_result = run_three_way_match(
            bc=bc,
            bl=bl,
            facture=facture,
            job_id=job_id,
            supplier_price_tolerance=supplier_price_tol,
            supplier_qty_tolerance=supplier_qty_tol,
        )

        await _audit(db, job_id, "MATCHING_COMPLETE", {
            "global_verdict": match_result.global_verdict,
            "total_lines": match_result.total_lines,
            "match_count": match_result.match_count,
            "mismatch_count": match_result.mismatch_count,
            "missing_count": match_result.missing_count,
            "extra_count": match_result.extra_count,
            "low_confidence_count": match_result.low_confidence_count,
        })

        # ── Layer 9: Save results ─────────────────────────────────────
        mr_model = MatchResult(
            job_id=job_id,
            global_verdict=match_result.global_verdict,
            bc_to_bl_link_confidence=match_result.bc_to_bl_link_confidence,
            bc_to_facture_link_confidence=match_result.bc_to_facture_link_confidence,
            used_fuzzy_link=match_result.used_fuzzy_link,
            total_lines=match_result.total_lines,
            match_count=match_result.match_count,
            mismatch_count=match_result.mismatch_count,
            missing_count=match_result.missing_count,
            extra_count=match_result.extra_count,
            low_confidence_count=match_result.low_confidence_count,
            line_verdicts=[r.model_dump() for r in match_result.line_results],
        )
        db.add(mr_model)
        final_status = (
            JobStatus.REVIEW_REQUIRED
            if match_result.global_verdict in ("REVIEW", "INCOMPLETE")
            else JobStatus.COMPLETED
        )
        job.status = final_status
        job.verdict = JobGlobalVerdict(match_result.global_verdict)
        job.processing_completed_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(
            "pipeline_complete",
            job_id=job_id,
            verdict=match_result.global_verdict,
            status=final_status,
        )

        return {
            "job_id": job_id,
            "status": final_status,
            "verdict": match_result.global_verdict,
        }


# ─── Helpers ───────────────────────────────────────────────────────────────

async def _get_job(db: AsyncSession, job_id: str) -> Job:
    from sqlalchemy import select
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    return job


async def _audit(db: AsyncSession, job_id: str, event_type: str, data: dict):
    log = AuditLog(job_id=job_id, event_type=event_type, event_data=data, actor="system")
    db.add(log)
    await db.commit()


async def _mark_job_failed(job_id: str, error: str):
    async with AsyncSessionLocal() as db:
        job = await _get_job(db, job_id)
        job.status = JobStatus.FAILED
        job.error_message = error[:2000]
        job.processing_completed_at = datetime.now(timezone.utc)
        await _audit(db, job_id, "JOB_FAILED", {"error": error})
        await db.commit()


def _get_ref(doc) -> str | None:
    if hasattr(doc, "ref_bc"):
        return doc.ref_bc
    if hasattr(doc, "ref_bl"):
        return doc.ref_bl
    if hasattr(doc, "ref_facture"):
        return doc.ref_facture
    return None
