# Magriplast Document Processing System
# khiari mohmed 
## Principal Architect Analysis & Final Production Architecture
**Scale assumption:** 100–3,000 PDFs/day · Results within minutes · Small engineering team

## STEP 1 — FINAL HYBRID ARCHITECTURE

### Core Design Principles
1. **Native-first, OCR-second.** If the PDF has a text layer, use it. Never run OCR on clean native PDFs.
2. **Classify before extract.** Page type determines which schema and extraction template to apply.
3. **Fail loudly, never silently.** Every uncertain step emits a confidence score and a review flag.
4. **AI is a fallback, not a foundation.** Rule-based extraction is the primary path. AI fires only when templates fail.
5. **Matching is pure Python.** Zero AI, zero ML, zero randomness in the verdict.
6. **Audit everything.** Every decision made by the system is logged immutably with the inputs that caused it.
7. **Supplier profiles are the real moat.** The system gets more accurate over time as supplier profiles accumulate.


### System Flow — Step by Step

```
INPUT
  ↓
LAYER 0: INGESTION
  ↓
LAYER 1: PDF ANALYSIS & TYPE DETECTION (native vs scanned branch)
  ↓
LAYER 2: PAGE PREPROCESSING (scanned branch only)
  ↓
LAYER 3: PAGE CLASSIFICATION
  ↓
LAYER 4: PAGE GROUPING (multi-page document assembly)
  ↓
LAYER 5: SCHEMA-DRIVEN EXTRACTION (per document group)
  ↓
LAYER 6: POST-EXTRACTION CORRECTION & NORMALIZATION
  ↓
LAYER 7: SCHEMA & BUSINESS LOGIC VALIDATION
  ↓
LAYER 8: 3-WAY MATCHING ENGINE (deterministic)
  ↓
LAYER 9: OUTPUT & AUDIT
```
### Full ASCII Architecture Diagram
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LAYER 0 — INGESTION                                ║
║                                                                              ║
║   [HTTP Upload] → [File Validator]                                           ║
║                        │                                                    ║
║                   Reject if: not PDF / corrupted / password-protected        ║
║                   Reject if: > 50MB / 0 pages                               ║
║                        │                                                    ║
║                   [Job Queue] → job_id returned to client immediately        ║
║                   [Original PDF stored to object storage — immutable]        ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║  (Celery worker picks up job)
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 1 — PDF ANALYSIS & TYPE DETECTION                        ║
║                                                                              ║
║   [PyMuPDF page inspector]                                                   ║
║        │                                                                    ║
║        ├── Per page: extract raw text layer (if exists)                     ║
║        │   measure: char_count, image_coverage_ratio, page_dimensions       ║
║        │                                                                    ║
║        ├── NATIVE PAGE  (char_count > threshold AND image_coverage < 0.3)  ║
║        │   → text already extracted, skip image preprocessing               ║
║        │   → go directly to LAYER 3 (Classification)                        ║
║        │                                                                    ║
║        └── SCANNED PAGE (char_count < threshold OR image_coverage > 0.7)  ║
║            → go to LAYER 2 (Preprocessing)                                  ║
║                                                                              ║
║   Output per page: { page_id, source_type: NATIVE|SCANNED, raw_text? }     ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║  (SCANNED pages only)
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 2 — IMAGE PREPROCESSING (scanned branch)                ║
║                                                                              ║
║   [pdf2image] → render page to 300 DPI PNG                                  ║
║        │                                                                    ║
║   [OpenCV pipeline]                                                          ║
║        ├── Orientation detection (pytesseract OSD)                          ║
║        ├── Deskew (correct scan rotation up to ±15°)                        ║
║        ├── Denoise (Gaussian blur + threshold)                               ║
║        ├── Binarize (Otsu thresholding → pure black/white)                  ║
║        └── Border removal (crop scan borders)                               ║
║        │                                                                    ║
║   [Preprocessed image stored] → fed to both classifier and OCR engine       ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 3 — PAGE CLASSIFICATION                                  ║
║                                                                              ║
║   For each page independently:                                               ║
║                                                                              ║
║   [Tier 1: Rule-Based Classifier]  ─────────────────────── PRIMARY          ║
║        Input: raw text (NATIVE) or Tesseract quick-pass text (SCANNED)      ║
║        ├── Keyword match in first 20% of page:                              ║
║        │     "BON DE COMMANDE" / "N° BC" / "COMMANDE N°"  → BC             ║
║        │     "BON DE LIVRAISON" / "N° BL" / "BON LIVRAISON" → BL           ║
║        │     "FACTURE" / "AVOIR" / "N° FAC" / "INVOICE"   → FACTURE        ║
║        ├── Reference pattern regex:                                          ║
║        │     BC-\d{4}-\d{3,6} / BL-\d{4}-\d{3,6} etc.                     ║
║        ├── Table density heuristic (many rows → likely line-item doc)       ║
║        │                                                                    ║
║        → confidence >= 0.90: classify and proceed                           ║
║        → confidence < 0.90: cascade to Tier 2                               ║
║                                                                              ║
║   [Tier 2: LLM Classifier]  ───────────────────────────── FALLBACK          ║
║        Input: raw page text + image thumbnail (if scanned)                  ║
║        Prompt: structured JSON output only                                   ║
║          { "doc_type": "BC"|"BL"|"FACTURE"|"UNKNOWN",                       ║
║            "reasoning": "...",                                               ║
║            "confidence": 0.0-1.0 }                                          ║
║        temperature=0 / max_tokens=200 / response_format=json                ║
║        → confidence >= 0.70: classify and proceed                           ║
║        → confidence < 0.70: cascade to Tier 3                               ║
║                                                                              ║
║   [Tier 3: Human Review Queue]  ───────────────────────── LAST RESORT       ║
║        Flag page as UNKNOWN, pause job, notify operator                     ║
║        Operator labels page → system continues                              ║
║        Label stored → feeds future rule improvement                         ║
║                                                                              ║
║   Output: { page_id, doc_type, confidence, source_tier: 1|2|3 }            ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 4 — PAGE GROUPING (document assembly)                   ║
║                                                                              ║
║   Problem: a 5-page PDF might be:                                            ║
║     page 1 → BC (page 1 of 2)                                               ║
║     page 2 → BC (page 2 of 2, overflow line items)                          ║
║     page 3 → BL                                                             ║
║     page 4 → FACTURE (page 1 of 2)                                          ║
║     page 5 → FACTURE (page 2 of 2)                                          ║
║                                                                              ║
║   [Page Grouper]                                                             ║
║        ├── Group consecutive same-type pages into one document unit         ║
║        ├── Detect continuation pages: look for "page N of M" / "suite"     ║
║        ├── Use document reference number to confirm grouping                ║
║        │     (page 1 and page 2 have same BC ref → same document)           ║
║        └── Flag ambiguous groupings for human confirmation                  ║
║                                                                              ║
║   Output: document_groups[]                                                  ║
║     each group: { doc_type, pages[], ref_hint, confidence }                 ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 5 — EXTRACTION                                           ║
║                                                                              ║
║   Per document group:                                                        ║
║                                                                              ║
║   [Supplier Detector]  ──────────── runs FIRST before extraction            ║
║        ├── Extract header region (top 25% of first page)                    ║
║        ├── Match against supplier registry:                                 ║
║        │     name / SIRET / address pattern / VAT number                    ║
║        ├── If match found → load supplier_profile                           ║
║        │     { field_aliases, column_positions, number_locale, date_fmt }   ║
║        └── If no match → new supplier, flag for onboarding workflow         ║
║                                                                              ║
║   [Tier 1: Template-Based Extractor]  ──────────────────── PRIMARY          ║
║        ├── Load base Pydantic schema for doc_type (BC / BL / FACTURE)       ║
║        ├── Apply supplier_profile aliases on top of base schema             ║
║        │     "P.U HT" → prix_unitaire  (from supplier profile)              ║
║        │     "Réf. Art." → ref_produit (from supplier profile)              ║
║        ├── For NATIVE pages: extract directly from text layer via regex     ║
║        │     anchor patterns to known header labels + table structure       ║
║        ├── For SCANNED pages: run Tesseract 5 (fra language pack)           ║
║        │     on preprocessed image, then apply same template logic          ║
║        ├── Assign per-field confidence from:                                ║
║        │     OCR char confidence (Tesseract) OR rule match strength         ║
║        └── → If all required fields extracted AND confidence > 0.85:        ║
║              proceed with template result                                    ║
║                                                                              ║
║   [Tier 2: Cloud OCR Fallback]  ────────────────────────── FALLBACK A       ║
║        Triggered when: Tesseract confidence < 0.70 on critical fields       ║
║        OR when: table structure extraction fails                             ║
║        ├── Send page image to Google Document AI                            ║
║        │     (Form Parser for invoices/POs)                                 ║
║        ├── Map Document AI entity labels to internal schema fields          ║
║        └── Re-run Pydantic validation with Document AI results              ║
║                                                                              ║
║   [Tier 3: LLM Extraction Fallback]  ──────────────────── FALLBACK B        ║
║        Triggered when: supplier is UNKNOWN OR cloud OCR also fails          ║
║        ├── System prompt: "Extract ONLY. Do NOT infer. Do NOT calculate."   ║
║        │   "Return exactly this JSON schema: [schema definition]"           ║
║        │   "If a field is not visible, return null. Never guess."           ║
║        ├── temperature=0, max_tokens=1500                                   ║
║        ├── response_format=json_object (strict)                             ║
║        ├── Validate response against Pydantic schema immediately            ║
║        │   If validation fails → retry once with error message in prompt    ║
║        │   If second failure → flag for human review                        ║
║        └── Flag extraction source as AI for audit trail                     ║
║                                                                              ║
║   Output per document: raw extracted JSON + source_tier + confidence map   ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 6 — POST-EXTRACTION CORRECTION & NORMALIZATION           ║
║                                                                              ║
║   [OCR Error Corrector]                                                      ║
║        Applied to ALL extracted text before type casting                    ║
║        ├── Numeric fields: replace O→0, l→1, I→1, S→5, B→8               ║
║        ├── Reference fields: strip extra spaces, normalize separators       ║
║        └── Apply only to fields where type is numeric/reference             ║
║            (do NOT apply to designation/description — degrades meaning)     ║
║                                                                              ║
║   [Number Parser]                                                            ║
║        French locale: "1 200,50" → 1200.50                                 ║
║        Handle: space-as-thousands-sep + comma-as-decimal                    ║
║        Handle: period-as-thousands-sep + comma-as-decimal                   ║
║        Handle: plain decimal (some suppliers use international format)      ║
║        Fallback: if ambiguous, flag field confidence as LOW                  ║
║                                                                              ║
║   [Date Normalizer]                                                          ║
║        Known formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD       ║
║        Output: always ISO 8601 (YYYY-MM-DD) internally                     ║
║                                                                              ║
║   [Reference Normalizer]                                                     ║
║        Uppercase, strip whitespace, normalize separators                    ║
║        Compute normalized_ref for fuzzy matching downstream                 ║
║                                                                              ║
║   Output: fully typed, normalized JSON per document                         ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 7 — VALIDATION                                           ║
║                                                                              ║
║   [Schema Validator]  (Pydantic v2)                                          ║
║        ├── All required fields present?                                     ║
║        │     BC required: ref_bc, date, supplier_id, lines[]                ║
║        │     BL required: ref_bl, date, lines[]                             ║
║        │     FACTURE required: ref_facture, date, total_ht, tva, total_ttc  ║
║        ├── Correct data types post-normalization?                           ║
║        └── No null in critical fields (ref, qty, prix_unitaire)?            ║
║                                                                              ║
║   [Business Logic Validator]  (pure Python, deterministic)                  ║
║        ├── Line math: abs(qty × prix_u - total_ligne) <= tolerance          ║
║        ├── Header totals: total_ht == sum(all line totals)                  ║
║        ├── TVA math: abs(total_ttc - total_ht × (1 + tva/100)) <= tolerance ║
║        ├── Date ordering: date_bl >= date_bc (flag, not hard reject)        ║
║        ├── Date ordering: date_facture >= date_bl (flag if BL present)     ║
║        └── Quantity sanity: all quantities > 0                              ║
║                                                                              ║
║   Tolerance: configurable per supplier profile (default ±0.02 EUR/line)    ║
║                                                                              ║
║   [Confidence Aggregator]                                                    ║
║        Compute document-level confidence from per-field confidence scores   ║
║        Any field confidence < 0.70 → document.has_low_confidence_fields=True║
║                                                                              ║
║   Output: validated document objects with confidence map + validation flags ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 8 — 3-WAY MATCHING ENGINE  (100% deterministic, no AI)  ║
║                                                                              ║
║   [Document Linker]                                                          ║
║        ├── Exact match on ref: BC.ref_bc == BL.ref_bc_linked                ║
║        ├── Exact match on ref: BC.ref_bc == FACTURE.ref_bc                  ║
║        ├── If exact match fails: fuzzy match (Levenshtein distance <= 2)    ║
║        │     Flag as LOW_CONFIDENCE_LINK if fuzzy match used                ║
║        └── If no link found: UNLINKED_DOCUMENT error                        ║
║                                                                              ║
║   [Line Item Matcher]                                                        ║
║        For each line in BC:                                                  ║
║        ├── Find BL line by ref_produit (exact, then fuzzy fallback)         ║
║        ├── Find FACTURE line by ref_produit (exact, then fuzzy fallback)    ║
║        │                                                                    ║
║        Per field comparison:                                                 ║
║        ├── qty: BC.qty vs BL.qty vs FACTURE.qty                             ║
║        │     abs(a - b) <= qty_tolerance → MATCH (default: 0)              ║
║        ├── prix_unitaire: BC.prix_u vs FACTURE.prix_u (BL has no price)    ║
║        │     abs(a - b) <= price_tolerance → MATCH (default: 0.01)         ║
║        ├── tva: BC.tva vs FACTURE.tva (exact match required)               ║
║        └── designation: fuzzy text similarity check (informational only)    ║
║                                                                              ║
║   [Per-Line Verdict]                                                         ║
║        MATCH          → all fields within tolerance                         ║
║        MISMATCH       → one or more fields differ beyond tolerance          ║
║        MISSING        → product in BC not found in BL or FACTURE           ║
║        EXTRA          → product in BL/FACTURE not in BC                    ║
║        LOW_CONFIDENCE → extraction confidence below threshold on this line  ║
║        PARTIAL_DATA   → document type absent (no BL in this PDF)           ║
║                                                                              ║
║   [Global Verdict]                                                           ║
║        VALIDATED     → all lines = MATCH, no LOW_CONFIDENCE                ║
║        PARTIAL       → some MISMATCH or MISSING, but not critical fields   ║
║        REJECTED      → any MISMATCH on prix_unitaire or ref_produit         ║
║        REVIEW        → any LOW_CONFIDENCE or EXTRA lines present           ║
║        INCOMPLETE    → one document type entirely missing                   ║
╚══════════════════════════════════╦═══════════════════════════════════════════╝
                                   ║
╔══════════════════════════════════╩═══════════════════════════════════════════╗
║              LAYER 9 — OUTPUT & AUDIT                                       ║
║                                                                              ║
║   [Audit Logger]  (written before any result is returned)                   ║
║        ├── Immutable append-only log entry in PostgreSQL                    ║
║        ├── Records: job_id, upload timestamp, user_id, original_pdf_hash    ║
║        ├── Records: per-page classification result + source_tier + conf     ║
║        ├── Records: per-field extracted value + confidence + source_tier    ║
║        ├── Records: per-line matching verdict + field comparison values     ║
║        └── Records: global verdict + timestamp of verdict                   ║
║                                                                              ║
║   [Report Generator]                                                         ║
║        ├── JSON result (for API consumers and frontend)                     ║
║        ├── HTML/PDF report for accounting team                              ║
║        │     Color coding: GREEN=MATCH, RED=MISMATCH, ORANGE=LOW_CONF      ║
║        │     Each cell shows: BC value | BL value | FACTURE value | verdict ║
║        │     Low-confidence fields marked with ⚠ and confidence %          ║
║        └── Summary header: global verdict + mismatch count + review count  ║
║                                                                              ║
║   [Notification Dispatcher]                                                  ║
║        ├── VALIDATED → mark job complete, notify uploader                   ║
║        ├── REVIEW → create review task, assign to accounting team           ║
║        └── REJECTED → high-priority alert, block auto-approval              ║
║                                                                              ║
║   [Supplier Learning Loop]                                                   ║
║        When new supplier encountered and successfully onboarded:            ║
║        ├── Human reviews AI-extracted schema                                ║
║        ├── Human confirms/corrects field mappings                           ║
║        └── System promotes to permanent supplier_profile                    ║
║            Next document from same supplier → Tier 1 extraction directly    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

##Data Models
### Pydantic Schema Examples

```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from decimal import Decimal
from datetime import date

class LineItem(BaseModel):
    ref_produit: str
    designation: str
    qty: Decimal
    prix_unitaire: Optional[Decimal] = None  # BL may not have price
    tva_rate: Optional[Decimal] = None
    total_ligne: Optional[Decimal] = None
    extraction_confidence: float = 1.0

    @model_validator(mode='after')
    def check_line_math(self):
        if self.prix_unitaire and self.total_ligne:
            expected = self.qty * self.prix_unitaire
            if abs(expected - self.total_ligne) > Decimal('0.02'):
                self.extraction_confidence = min(self.extraction_confidence, 0.5)
        return self

class BonDeCommande(BaseModel):
    ref_bc: str
    date_bc: date
    supplier_name: str
    supplier_id: Optional[str] = None
    lines: list[LineItem]
    total_ht: Optional[Decimal] = None
    extraction_confidence: float = 1.0
    extraction_source_tier: int  # 1=template, 2=cloud, 3=LLM

class MatchingVerdict(BaseModel):
    line_ref: str
    qty_bc: Decimal
    qty_bl: Optional[Decimal]
    qty_facture: Optional[Decimal]
    prix_bc: Optional[Decimal]
    prix_facture: Optional[Decimal]
    tva_bc: Optional[Decimal]
    tva_facture: Optional[Decimal]
    verdict: str  # MATCH|MISMATCH|MISSING|EXTRA|LOW_CONFIDENCE|PARTIAL_DATA
    mismatch_fields: list[str]
    confidence: float
```

---

## STEP 5 — TECH STACK
### Backend: Python 3.11 + FastAPI + Pydantic + PostgreSQL
**Why Python:** The OCR, PDF, and data validation ecosystem in Python has no peer. PyMuPDF, Tesseract bindings, OpenCV, Pydantic — all first-class.
**Why FastAPI:** Async-native, automatic OpenAPI schema generation, Pydantic integration built in. For a team that will write API contracts that a frontend consumes, this is the correct choice.
**Not Node.js:** The PDF/OCR tooling in Python is 5 years ahead. Not Django: too much ceremony for an API-first service.
### Frontend: React + Vite + TailwindCSS
The frontend is a thin display layer. React is justified. The key UI requirement is a side-by-side table showing BC | BL | FACTURE values with color-coded verdict per cell, with the original PDF viewable alongside. Use `react-pdf` for the in-browser PDF viewer. TanStack Query for polling the job status endpoint.

### PDF Processing
**PyMuPDF (fitz):** Extract text layer from native PDFs, page metadata, image coverage ratio. Free, fast, no external API calls.
**pdf2image + Pillow:** Render scanned PDF pages to PNG at 300 DPI for preprocessing.
**OpenCV:** Deskew, denoise, binarize. Use `cv2.threshold` with Otsu for binarization. Use `imutils.correct_skew` for deskew.

### OCR
**Primary: Tesseract 5** with `fra` (French) language pack. Self-hosted. Fast for native-like quality scans. ~50ms per page on a modern CPU. Free.
**Fallback: Google Document AI** (Form Parser). Handles degraded scans, handwritten annotations, complex table layouts. ~$0.065 per page (Document AI v2). Trigger only when Tesseract confidence on critical fields falls below 0.70. At 3,000 PDFs/day with 3 pages each, if 10% fall through to Google = 900 pages/day × $0.065 = $58/day = $1,740/month maximum. In practice, for a single manufacturing company with known suppliers, well under 5% should fall through once supplier profiles are built.

**Do NOT use:** OpenAI Whisper or GPT-4V as primary OCR. Expensive, inconsistent on structured tables, no confidence scores per field.
### AI Usage — Precise Rules

| Use Case | Allowed | Constraints |
|----------|---------|-------------|
| Page classification fallback (Tier 2) | Yes | temperature=0, JSON only, max_tokens=200 |
| Extraction from unknown supplier layout (Tier 3) | Yes | temperature=0, JSON only, Pydantic validated, one retry |
| New supplier schema suggestion | Yes | Human reviews before promoting to supplier profile |
| Matching logic | **Never** | Pure Python only |
| Numeric comparison | **Never** | Python Decimal arithmetic only |
| Reference number comparison | **Never** | Exact + Levenshtein distance only |
| Final verdict generation | **Never** | Deterministic rule engine only |

**Model:** Claude claude-sonnet-4-20250514 (structured outputs support, cost-efficient for JSON-constrained calls).
### Schema Validation: Pydantic v2

Pydantic v2 over raw JSON Schema validation. Reasons: Python-native type coercion, field_validator for per-field regex/range checks, model_validator for cross-field business logic (line math), native FastAPI integration, excellent error messages that can be logged verbatim.

### Database: PostgreSQL 15
**JSONB columns** for extracted document data — flexible schema, queryable with -> operators, indexable.
**Separate normalized tables** for: jobs, pages, document_groups, extracted_headers, extracted_lines, match_verdicts, audit_log.

The audit_log table has `INSERT` privileges only for the application user — no `UPDATE` or `DELETE`. Immutability enforced at the database level.

**Indexes:** on job_id, on supplier_id, on ref_bc (for historical lookups).

### Queue: Celery + Redis

**Justified at this scale.** 3,000 PDFs/day = 125/hour = just over 2/minute. A synchronous approach would work in theory but creates backpressure problems under burst loads.

**Two separate worker pools:**

| Queue | Worker Type | Concurrency | Reason |
|-------|-------------|-------------|--------|
| `pdf_processing` | CPU-bound (Tesseract, OpenCV) | N CPU cores | CPU-intensive, no I/O wait |
| `cloud_ocr` | I/O-bound (Google Doc AI API) | 20–50 threads | Waiting on network, not CPU |
| `llm_extraction` | I/O-bound (Claude API) | 10 threads | Rate-limited by API |

**Do NOT** put all jobs on a single queue. Slow cloud OCR jobs will block CPU-bound Tesseract jobs and destroy throughput.

### Object Storage: AWS S3 or self-hosted MinIO

**Use managed S3** (or compatible) unless there is a hard data sovereignty requirement. MinIO is operationally complex for a small team. If the data must stay on-premises (accounting data for a Tunisian company may have residency requirements), then MinIO is correct — but run it as a dedicated service, not on the same machine as the API.

Retention policy: original PDFs stored indefinitely (accounting audit requirement). Intermediate page images stored for 30 days then deleted.

---

## Critical Engineering Rules
**Rule 1: Do not start coding before 5-10 real PDFs are analyzed manually.** Map every field, every supplier variant, every edge case. This 2-day investment determines the quality of every subsequent layer. Skipping this is the single most common reason OCR pipelines fail in production.

**Rule 2: The matching engine must have 50+ unit tests.** Cover: exact match, qty mismatch, price mismatch, missing product, extra product, reference mismatch by one character, partial document (no BL), tolerance edge cases (exactly at boundary). This is accounting software — bugs have financial consequences.

**Rule 3: Confidence scores surface to the accounting UI.** Every field in the result report shows its extraction confidence. An accountant who sees a ⚠ 71% confidence flag next to a unit price will manually verify it. This is the difference between a tool people trust and a liability.

**Rule 4: Supplier profiles are day-one work.** For every known supplier, build the field mapping table before the first real document is processed. This immediately removes 90% of Tier 2 and Tier 3 fallback calls, which means faster results and lower cost.

**Rule 5: Never auto-approve REVIEW or REJECTED verdicts.** The workflow must be: system matches → if not VALIDATED → human reviews → human approves → system logs approval with user_id and timestamp. Full stop. No exception for urgency.

**Rule 6: The audit log is write-only from the application.** The application database user has `INSERT` on audit_log but not `UPDATE` or `DELETE`. An accountant or regulator can always reconstruct exactly what the system did, what it extracted, and why it gave the verdict it gave.
