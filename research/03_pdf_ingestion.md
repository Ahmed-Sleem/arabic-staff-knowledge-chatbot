# Topic 3 — PDF Ingestion Pipeline (Arabic)

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Parser** for Arabic PDFs:
   - `PyMuPDF` (`fitz`) — fast, good with embedded text, may struggle with scanned / complex Arabic shaping
   - `pdfplumber` — good for tables
   - `unstructured` — robust, handles many layouts
   - `LlamaParse` — API-based, excellent on complex docs
   - `marker-pdf` / `docling` — newer, ML-based
   - `pypdf` — basic
2. **Table extraction** for KPI tables, reporting lines, escalation matrix:
   - `camelot` (lattice / stream)
   - `pdfplumber` tables
   - LLM-based extraction (pass page image to GPT-4V / Gemini Vision)
   - `img2table`
3. **Chunking** — section-aware splitter that keeps each job role intact (per PRD §10.2):
   - Heuristics: detect headings like "8.1 مدير مكتب إدارة المشاريع", split accordingly
   - Preserve page numbers and section numbers in metadata
4. **Metadata schema** (per PRD §10.2):
   ```
   { "document_name", "version", "page", "section", "title", "department", "content_type" }
   ```
5. **Handling RTL text, diacritics, ligatures, presentation forms** — normalization.
6. **The actual data file** — `uploads/hr_extracted/hr_source.pdf` is 5.7 MB. Need to inspect its structure (text-based or scanned, fonts, table density) before choosing a parser.
7. **Re-indexing lifecycle** — how to support multiple document versions side-by-side (per PRD §7.10).
8. **Storage** of raw PDFs and chunk artifacts.

---

## Findings (append below)


## Findings — PDF parsing tools for Arabic

### Source 1 — arxiv "A Comparative Study of PDF Parsing Tools" (Oct 2024)
URL: https://arxiv.org/pdf/2410.09871
- Compared pdfminer.six, PyMuPDF, pdfplumber, pypdfium2, Unstructured, Tabula, Camelot, Nougat (deep learning), TATR (Table Transformer).
- For **text extraction**: PyMuPDF and pypdfium generally outperform others, but all parsers struggled with Scientific and Patent documents. **Nougat (deep learning) demonstrated superior performance** on hard categories.
- For **table detection**: TATR excelled on Financial, Patent, Law, Scientific. Camelot on Government Tenders. PyMuPDF on Manuals.

### Source 2 — fast.io "Best PDF Parsing Tools for RAG in 2026"
URL: https://fast.io/resources/best-pdf-parsing-tools-rag/
- "LlamaParse and Docling are the top choices for LLM applications. LlamaParse uses vision models to handle complex layouts, tables, and charts with high accuracy. Docling offers similar layout awareness but is self-hosted and open-source. For simpler text-heavy PDFs, PyMuPDF4LLM is faster and lighter."
- "Markdown is best for most RAG use cases. It preserves headings, lists, tables, and code blocks in a readable format that chunks cleanly."
- "Open-source parsers like PyMuPDF, Marker, and Docling are free but need server costs for hosting. For high-volume RAG pipelines, self-hosted parsers have better economics once you pass 50,000 pages/month."

### Source 3 — Reddit r/LangChain "What's the Best PDF Extractor for RAG" (Feb 2025)
- "Docling is the gold standard imo." (multiple voices)
- "The best one, is by far Docling. I use a lot for ExtractThinker. The only downside of Docling is the fact that is super heavy, but is close to perfect. Converts everything to Markdown."
- One voice: "textract 10/10, Azure Document AI 9.8/10, Unstructured 5/10, Llamaparse okay."
- PyMuPDF4LLM "favourite" for many but "unreliable" for complex tables.

### Source 4 — pymupdf4llm PyPI
URL: https://pypi.org/project/pymupdf4llm/
- "Lightweight extension for PyMuPDF that converts documents into structured Markdown, JSON, and plain text optimised for RAG pipelines, vector embeddings, and LLM ingestion."
- "Layout-aware — multi-column pages, reading-order reconstruction, table detection."
- "Smart OCR — automatically OCRs only the regions that need it, skipping clean text."
- "Page chunking — chunk output by page."
- Integrations: LlamaIndex, LangChain.
- No GPU, no cloud, runs on any Python.
- OCR engines: Tesseract (built-in) and rapidocr_onnxruntime (auto-selected).

### Source 5 — Towards Data Science "Your Chunks Failed Your RAG in Production" (Apr 2026)
URL: https://towardsdatascience.com/your-chunks-failed-your-rag-in-production/
- **Strongly recommends PyMuPDF for layout-aware extraction** + `pdfplumber` for granular table control.
- Key insight: `get_text('blocks')` returns text grouped by visual block, not raw character order. Sorting by (vertical, horizontal) position reconstructs correct reading order for multi-column layouts.
- Routing heuristic: OCR only when PyMuPDF returns <50 words/page (identifies scanned docs).
- LlamaParse as managed alternative for teams that can't invest in parsing infra. Trade-off: external service.

### Implication for our project
- **Our PDF is text-based (Arabic, generated from a word processor) per the PRD's structure description.** No scanning, no multi-column layout expected. Sections are numbered (1, 1.1, 8.2.3, etc.).
- We need:
  1. Good Arabic text extraction (no garbled shaping, no missing letters).
  2. Section detection (so chunker can keep each job role's description together).
  3. Table extraction (KPI tables, reporting lines, escalation matrix).
- **Our shortlist:**
  1. **PyMuPDF (`fitz`)** — fast, reliable Arabic text, good layout-aware extraction via blocks. Good for our text-based PDF. Zero cost, runs anywhere.
  2. **pymupdf4llm** — wrapper that converts PyMuPDF output to Markdown optimized for RAG. **Top pick for our use case.**
  3. **pdfplumber** — for KPI table extraction specifically (better table detection than PyMuPDF on grid-like tables).
  4. **Docling** — if PyMuPDF output is messy. Slower, heavier, but better at complex layouts.
  5. **LlamaParse** — last resort if all else fails. External service, costs money.

### Recommendation (locked candidate for plan)
- **Primary pipeline:**
  1. `pymupdf4llm.to_markdown(pdf, page_chunks=True)` — get markdown with page boundaries.
  2. Custom Arabic-aware section splitter (regex on numbered headings like "8.1.2 المهام والمسؤوليات").
  3. `pdfplumber` to detect and extract KPI tables specifically.
  4. `pymupdf` to read page numbers per chunk.
- **Chunking strategy** (PRD §10.2 requires section-aware):
  - Detect numbered headings: `^(\d+)(\.\d+)*\s+(.+)$` (e.g., "8.1.2 المهام والمسؤوليات").
  - Group paragraphs under the most recent heading.
  - Keep each job role's full description (heading + duties + reporting + KPIs + requirements) as one chunk when it fits within ~1500 tokens. Else split on sub-headings.
  - Add metadata: `page`, `section`, `title`, `department` (inferred from section), `content_type` (job_description / kpi_table / escalation / general).
  - Target chunk size: 800–1500 tokens, 200 token overlap.


## Findings — Actual structure of `hr_source.pdf` (the data file)

**Inspected on 2026-07-10.** This is real empirical data — the only data inspection done so far.

### Overview
- **Pages:** 64
- **Text length:** ~116,000 characters
- **Word count:** ~16,700 Arabic words
- **File size:** 5.7 MB (mostly images, but text is clean)
- **Generation:** Word-exported PDF with crisp text layer. No OCR needed.
- **Language:** Arabic only (some Latin abbreviations: PMO, QHSE, CEO, QA/QC, HSE, KPI, KSA, PMO, etc. — these are kept as Latin, which is exactly the mixed-content case our research identified).
- **Diacritics:** mostly absent (good — most Arabic LLMs are trained on non-diacritized text). Some words have them (e.g., "اﻟﺗﻧﻔﯾذي") — these need to be stripped before embedding but preserved in the displayed chunk.

### Document structure (from TOC and page inspection)
- **Document name:** دليل الهيكل التنظيمي والمسؤوليات الوظيفية ومؤشرات الأداء
- **English name:** Organizational Structure, Job Responsibilities & KPIs Guide
- **Version:** 1.0
- **Issue date:** 18/05/2026
- **Issuer:** HR Department of "شركة كيان المملكة" (KSA company)
- **Approved by:** CEO

### Numbered sections (sample)
| Section | Title | Page |
|---|---|---|
| 1 | مقدمة الدليل (Introduction) | 6 |
| 2 | الهدف من الدليل (Purpose) | 6 |
| 3 | نطاق التطبيق (Scope) | 6 |
| 4 | قاعدة التصعيد الإداري (Escalation Rule) | 6 |
| 5 | مجلس الإدارة (Board of Directors) | 7 |
| 5.1 | مجلس الإدارة (Board) | 7 |
| 6 | الإدارة التنفيذية العليا (Executive Management) | 8 |
| 6.1 | الرئيس التنفيذي CEO (CEO) | 8 |
| 7 | إدارة الجودة والصحة والسلامة والبيئة QHSE | 9 |
| 7.1 | مدير الجودة والصحة والسلامة والبيئة (QHSE Manager) | 9 |
| 7.2 | مسؤول الجودة QA/QC (QA/QC Officer) | 10 |
| 7.3 | مسؤول الصحة والسلامة والبيئة HSE | 11 |
| 8 | مكتب إدارة المشاريع PMO | 12 |
| 8.1 | مدير مكتب إدارة المشاريع (PMO Manager) | 12 |
| 8.2 | مسؤول التخطيط (Planning Officer) | 13 |
| 8.3 | مسؤول ضبط التكاليف (Cost Control Officer) | 14 |
| 8.4 | مسؤول التقارير (Reports Officer) | 14 |
| 8.5 | مسؤول إدارة المخاطر (Risk Officer) | 15 |
| 8.6 | (continues) | 16 |
| 9 | ... | 17 |
| ... | ... | ... |
| 15 | (final section) | 54+ |

- Numbering goes up to 4 levels: `8.2.3.1` style.
- Up to 15 top-level sections.
- 64 pages total. So average ~4-5 pages per top-level section.

### Per-role structure (what each `8.x.y` section likely contains, per PRD §10.2)
The PRD requires for each job role:
- الوصف الوظيفي (Job description)
- التبعية التنظيمية (Reporting line)
- المتطلبات (Requirements)
- المهام والمسؤوليات (Duties and responsibilities)
- مؤشرات الأداء (KPIs)

This pattern is the key for chunking. Each "job role" section should be ONE chunk, with all 5 sub-sections.

### Tables
- KPI tables appear within the job role sections (per PRD §10.3: `{role, section, kpi_name, calculation, target, page}`).
- The TOC uses dotted lines and right-aligned page numbers — typical Word PDF.

### Special text handling
- The text contains "Moshref" (purpose-only) markers and dotted leader lines from the TOC that should be cleaned out at ingestion.
- Repeated header "شركة كيان المملكة كاك" + "إدارة الموارد البشرية" + "كيان المملكة كاك" on every page — should be stripped from chunks.
- Page numbers appear in the text and need to be extracted as `page` metadata, NOT included in the chunk content.
- The string "كاك" is the company abbreviation ("KAK" — Kian Al-Mamlaka).

### Implication for the ingestion pipeline
- **Section detection regex** (post-cleanup):
  ```
  ^(\d{1,2}(\.\d{1,3}){0,3})\s+[\u0600-\u06FF].*$
  ```
  Matches lines starting with a number followed by Arabic text. Each match is a section boundary.
- **Chunk boundaries** = section boundaries, NOT page boundaries. One job role's full description = one chunk.
- **Heading hierarchy preservation:** store `section` (full path like "8.1"), `title` (Arabic title), `level` (1-4).
- **Department inference** from section prefix: e.g., 7.x = QHSE, 8.x = PMO, 9.x = Legal (we'll know the full mapping after we map all sections).
- **KPI table extraction:** after initial text chunking, detect blocks that look like tables (consecutive lines with tab-like separation or repeated column patterns) and extract as structured data per PRD §10.3.
- **Cleanup needed before embedding:**
  1. Strip repeated header.
  2. Strip page numbers.
  3. Strip TOC dots/leaders.
  4. Normalize Arabic (per topic 10 findings).
  5. Keep "KPI", "PMO", "QHSE", "HSE" as Latin (don't strip).

### Approximate chunk count
- ~15 top-level sections + ~50 sub-sections + ~150 sub-sub-sections + ~250 sub-sub-sub-sections.
- If we chunk by "each job role's full description = 1 chunk", expect ~80-120 chunks.
- If we chunk by section (any level) = 1 chunk, expect ~300-500 chunks.
- Either is well within any vector store's free tier.

