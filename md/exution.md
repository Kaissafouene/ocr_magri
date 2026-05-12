## The architecture has a dedicated scanned PDF branch with every stage designed for scanned documents:
# Layer 1 – Detects scanned pages via char count and image coverage, so scanned pages are identified correctly.
# Layer 2 – Full image preprocessing (orientation fix, deskew, denoise, binarization) to clean up scans before OCR.
# Layer 3 – Classification on scanned pages using Tesseract quick-pass text, with LLM and human review falls back if uncertain.

# Layer 5 – Extraction uses Tesseract 5 (French language pack) as primary OCR for scanned pages, then falls back to Google Document AI (strong on tables and degraded scans), and finally LLM extraction as a last resort. So even poor scans have multiple recovery paths.

# Layer 6 – Post-extraction correction and normalization (OCR error fix, French number parsing, date normalization) compensates for typical OCR noise.

# Layer 8 – Matching is deterministic, using extracted data, so once data is extracted (even with lower confidence), the matching engine still works.

# Human review queues are built-in for cases where confidence is too low, so no document is permanently blocked.

The system doesn’t promise 100% automation for every badly scanned document, but the core idea (extract BC/BL/Facture from scanned PDFs and perform 3‑way matching) is fully achievable within this architecture, as it was explicitly designed to handle the scanned path.
#*****************************************************************
#*****************************************************************
bakcend
📦server
 ┣ 📂alembic
 ┃ ┣ 📂versions
 ┃ ┗ 📜env.py
 ┣ 📂app
 ┃ ┣ 📂api
 ┃ ┃ ┣ 📜admin.py
 ┃ ┃ ┣ 📜jobs.py
 ┃ ┃ ┣ 📜results.py
 ┃ ┃ ┣ 📜upload.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂core
 ┃ ┃ ┣ 📜celery_app.py
 ┃ ┃ ┣ 📜config.py
 ┃ ┃ ┣ 📜database.py
 ┃ ┃ ┣ 📜logging.py
 ┃ ┃ ┣ 📜storage.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂models
 ┃ ┃ ┣ 📜audit_log.py
 ┃ ┃ ┣ 📜document.py
 ┃ ┃ ┣ 📜job.py
 ┃ ┃ ┣ 📜line_item.py
 ┃ ┃ ┣ 📜match_result.py
 ┃ ┃ ┣ 📜supplier_profile.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂schemas
 ┃ ┃ ┣ 📜documents.py
 ┃ ┃ ┣ 📜job.py
 ┃ ┃ ┣ 📜line_item.py
 ┃ ┃ ┣ 📜matching.py
 ┃ ┃ ┣ 📜supplier.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂services
 ┃ ┃ ┣ 📜classifier.py
 ┃ ┃ ┣ 📜extractor.py
 ┃ ┃ ┣ 📜ingestion.py
 ┃ ┃ ┣ 📜matcher.py
 ┃ ┃ ┣ 📜normalizer.py
 ┃ ┃ ┣ 📜ocr_engine.py
 ┃ ┃ ┣ 📜page_grouper.py
 ┃ ┃ ┣ 📜pdf_analyzer.py
 ┃ ┃ ┣ 📜preprocessor.py
 ┃ ┃ ┣ 📜supplier_service.py
 ┃ ┃ ┣ 📜validator.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂utils
 ┃ ┃ ┣ 📜fuzzy.py
 ┃ ┃ ┣ 📜number_parser.py
 ┃ ┃ ┣ 📜pdf_utils.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂workers
 ┃ ┃ ┣ 📜llm_worker.py
 ┃ ┃ ┣ 📜ocr_worker.py
 ┃ ┃ ┣ 📜pipeline.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📜main.py
 ┃ ┗ 📜__init__.py
 ┣ 📂tests
 ┃ ┣ 📂integration
 ┃ ┗ 📂unit
 ┣ 📜.env
 ┣ 📜.env.example
 ┣ 📜alembic.ini
 ┣ 📜docker-compose.yml
 ┣ 📜Dockerfile
 ┗ 📜requirements.txt
#***************************
//////////////////////////

📦frontend
┣ 📂public
 ┃ ┗ 📜favicon.ico
 ┣ 📂src
 ┃ ┣ 📂api
 ┃ ┃ ┣ 📜admin.js
 ┃ ┃ ┣ 📜client.js
 ┃ ┃ ┗ 📜jobs.js
 ┃ ┣ 📂components
 ┃ ┃ ┣ 📂job
 ┃ ┃ ┃ ┣ 📜JobCard.jsx
 ┃ ┃ ┃ ┣ 📜JobStatusBadge.jsx
 ┃ ┃ ┃ ┗ 📜JobStatusPoller.jsx
 ┃ ┃ ┣ 📂layout
 ┃ ┃ ┃ ┣ 📜Navbar.jsx
 ┃ ┃ ┃ ┗ 📜PageWrapper.jsx
 ┃ ┃ ┣ 📂results
 ┃ ┃ ┃ ┣ 📜AuditTrail.jsx
 ┃ ┃ ┃ ┣ 📜ConfidenceIndicator.jsx
 ┃ ┃ ┃ ┣ 📜DocumentSummary.jsx
 ┃ ┃ ┃ ┣ 📜LineItemTable.jsx
 ┃ ┃ ┃ ┣ 📜LineVerdictBadge.jsx
 ┃ ┃ ┃ ┗ 📜VerdictBanner.jsx
 ┃ ┃ ┣ 📂ui
 ┃ ┃ ┃ ┣ 📜Alert.jsx
 ┃ ┃ ┃ ┣ 📜Modal.jsx
 ┃ ┃ ┃ ┗ 📜Spinner.jsx
 ┃ ┃ ┗ 📂upload
 ┃ ┃ ┃ ┣ 📜UploadProgress.jsx
 ┃ ┃ ┃ ┗ 📜UploadZone.jsx
 ┃ ┣ 📂hooks
 ┃ ┃ ┣ 📜useJobPoller.js
 ┃ ┃ ┗ 📜useJobResults.js
 ┃ ┣ 📂pages
 ┃ ┃ ┣ 📜JobPage.jsx
 ┃ ┃ ┣ 📜ResultsPage.jsx
 ┃ ┃ ┣ 📜ReviewPage.jsx
 ┃ ┃ ┗ 📜UploadPage.jsx
 ┃ ┣ 📂utils
 ┃ ┃ ┣ 📜formatters.js
 ┃ ┃ ┗ 📜verdictColors.js
 ┃ ┣ 📜App.jsx
 ┃ ┣ 📜index.css
 ┃ ┗ 📜main.jsx
 ┣ 📜.env
 ┣ 📜index.html
 ┣ 📜package-lock.json
 ┣ 📜package.json
 ┣ 📜postcss.config.js
 ┣ 📜tailwind.config.js
 ┗ 📜vite.config.js

# ##########################################################
Here’s the mapping to the production design:

Architecture Layer||	 Backend Implementation||	             Status
# Layer 0 – Ingestion||	services/ingestion.py + api/upload.py	✅
# Layer 1 – PDF Analysis	services/pdf_analyzer.py	✅
# Layer 2 – Preprocessing	services/preprocessor.py	✅
# Layer 3 – Classification	services/classifier.py	✅
# Layer 4 – Page Grouping	services/page_grouper.py	✅
# Layer 5 – Extraction	services/extractor.py + ocr_engine.py + supplier_service.py	✅
# Layer 6 – Normalization	services/normalizer.py + utils/number_parser.py	✅
# Layer 7 – Validation	services/validator.py + schemas/documents.py (Pydantic)	✅
# Layer 8 – 3‑Way Matching	services/matcher.py + schemas/matching.py	✅
# Layer 9 – Output & Audit	models/audit_log.py, api/results.py, api/admin.py	✅
# Workers / Queues	workers/pipeline.py, ocr_worker.py, llm_worker.py (Celery routes)	✅
# Supplier Profiles	models/supplier_profile.py, services/supplier_service.py	✅
# Frontend (side-by-side, confidence flags)	ResultsPage, LineItemTable, ConfidenceIndicator, VerdictBanner, AuditTrail, ReviewPage	✅

# ##########################################################
# ##########################################################
e7seb rou7k 
PDF processing system is houa fil asl Bussy  restaurant l coujina  ta5o sel3a m5alta fiha 5othdra w l7am w barcha items mo5talfin (the PDFs). li ye5dmo fil coujina  inspects each item, identifies what kind of ingredient it is (BC, BL, Facture), ynadfhom , w ya3mlo preparation , and w ba3d y9arno  the actual delivery (BL) m3a l original order (BC) wel fatora (Facture) bech ychofo ken fama 8alta saert w w in aret bethabt .lazem kol step tet3mal tbada logged  bech ba3d mola resto wala li houa yji ythabet kima l archive yarja3lo 
hathaka houa l but ml applicaion 
bech njiw n9asmoha l steps a7na taw 

📤 PDF Upload
  │
  ▼
🧾 Reception (Layer 0 – Ingestion)
  Checks: Is it really a PDF? Not damaged? Not password-locked?
  Gives the bag a job number and stores the original untouched in the big fridge.
  Tells the client: "Got it! Here's your job ID, come back later."
  Files: ingestion.py, upload.py, job.py model
    ═══════════════════════════════
  ▼
🔍 Inspector (Layer 1 – PDF Analysis)
  Opens each page and asks: "Is this a printed page or a handwritten scan?"
  Counts characters and checks how much is picture vs text.
  If it's native (clean text): skip the washing step, go straight to classification.
  If it's scanned (mostly image): send it to the kitchen sink for cleaning.
  Files: pdf_analyzer.py
  ═══════════════════════════════
    ▼ (scanned pages only)
🧼 Kitchen Sink (Layer 2 – Preprocessing)
  Renders the scanned page into a photo, straightens it, removes stains (noise),
  turns it into crisp black and white – like washing dirty vegetables.
  Files: preprocessor.py (uses OpenCV)
  ═══════════════════════════════
  🏷️ Sorter (Layer 3 – Page Classification)
  Looks at each page and says: "This is a Purchase Order (BC), this is a Delivery Note (BL), this is an Invoice (FACTURE)."
  First tries reading keywords with simple rules (regex). If obvious → done.
  If not sure, asks a smart assistant (AI) to help. If still unsure, calls a human to come label it.
  Files: classifier.py
  ═══════════════════════════════
  📚 Binder (Layer 4 – Page Grouping)
  Sometimes a single document spreads over multiple pages (like a long grocery list).
  This step groups consecutive pages of the same type together using reference numbers.
  Files: page_grouper.py
   ═══════════════════════════════
  🔎 Reader (Layer 5 – Extraction)
  First: "Who sent this?" Looks at the top of the page and matches with our known suppliers (supplier profiles).
  If the supplier is known, uses a pre-made cheat sheet (template) to know where the quantity, price, and product names sit.
  For scanned pages: reads the photo using OCR (like Google Lens for French documents).
  If OCR fails, asks a smarter cloud reader (Google Document AI).
  If still fails, asks the AI assistant to carefully read and fill in a form – but mark it "AI did this" so we double-check.
  Files: extractor.py, ocr_engine.py, supplier_service.py
   ═══════════════════════════════
  ▼
🧹 Cleaner & Translator (Layer 6 – Post-Extraction Correction)
  Fixes common OCR mistakes: "1 2OO,5O" → "1 200,50 EUR".
  Converts French number format to standard numbers (1 200,50 → 1200.50).
  Normalises dates to ISO format (01/12/2025 → 2025-12-01).
  Files: normalizer.py, number_parser.py
  ═══════════════════════════════
  ▼
✔️ Quality Check (Layer 7 – Validation)
  Checks that all required fields are present (like missing item in a delivery).
  Does math: "quantity × unit price should equal line total. Does it?"
  Verifies tax calculations (TVA) are correct.
  Marks fields with low confidence for later review.
  Files: validator.py, Pydantic schemas (documents.py)
  ═══════════════════════════════
  ⚖️ Accountant (Layer 8 – 3‑Way Matching Engine)
  This is the core comparison:
  - Links the order (BC), delivery note (BL), and invoice (FACTURE) using reference numbers.
  - Compares line by line: quantities, prices, taxes, products.
  - Verdict per line: MATCH ✅, MISMATCH ❌, MISSING 🔍, EXTRA ➕, or LOW_CONFIDENCE ⚠.
  - Global verdict: VALIDATED (all good) or REVIEW/REJECTED.
  (This part is pure Python, no AI – because accounting must be predictable.)
  Files: matcher.py, fuzzy.py (for close-enough reference matching)
  ═══════════════════════════════
  ▼
📝 Report & Logbook (Layer 9 – Output & Audit)
  Saves every single decision (who, what, why) in a locked, write-only log book (audit_log table).
  Generates a colourful report: green for match, red for mismatch, orange for low confidence.
  Sends notifications: "All good!" or "Human review needed."
  Files: audit_log.py, results.py, formatters.js (frontend)
  ═══════════════════════════════

  # ################################################################################################
  🧰 Backend Files — Simple Job Descriptions
File / Folder	Restaurant Analogy
app/api/upload.py	The front door where PDFs enter; gives out job tickets.
app/core/celery_app.py	The bell system that assigns tasks to kitchen staff (workers).
app/core/config.py	The restaurant rule book (settings).
app/core/database.py	The recipe binder – connects to the database.
app/core/storage.py	The fridge for original PDFs (S3 or local).
app/models/job.py	The job ticket (status, ID).
app/models/document.py	An ingredient card (type, content).
app/models/line_item.py	A single line on the grocery list.
app/models/match_result.py	The final comparison verdict per line.
app/models/supplier_profile.py	Cheat sheet per supplier (where to find fields).
app/models/audit_log.py	The eternal black book – cannot be erased.
app/services/ingestion.py	Receptionist: validates and stores the PDF.
app/services/pdf_analyzer.py	Inspector: checks if native or scanned.
app/services/preprocessor.py	Kitchen hand: cleans scanned images.
app/services/classifier.py	Sorter: "This is a BC, this is a BL."
app/services/page_grouper.py	Binder: groups pages into documents.
app/services/extractor.py	Chef: pulls out numbers, dates, products using templates.
app/services/ocr_engine.py	Optical reader (Tesseract + Google Doc AI).
app/services/supplier_service.py	Supplier rolodex: finds and builds profiles.
app/services/normalizer.py	Language translator: fixes numbers, dates.
app/services/validator.py	Quality inspector: checks math and completeness.
app/services/matcher.py	The accountant that compares BC ↔ BL ↔ Facture.
app/utils/number_parser.py	Expert for French number formats.
app/utils/fuzzy.py	Matcher for slightly-misspelled reference numbers.
app/workers/pipeline.py	The Head Chef: runs the whole sequence from analysis to matching.
app/workers/ocr_worker.py	Worker that runs only OCR tasks (CPU-heavy).
app/workers/llm_worker.py	Worker that calls AI assistant when needed (I/O-heavy).


