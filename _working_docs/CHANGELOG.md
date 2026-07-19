# Changelog

**Append-only session log per Rule 5. Format: `## YYYY-MM-DD session N`**

---

## 2026-07-10 session 1 (Historical Setup - Phase 1 & 2)
- Read PRD (`PRD_ Arabic Staff Knowledge Chatbot.pdf`), Cyrkil design system (`DESIGN_SYSTEM.md`), and general development rules.
- Renamed and extracted source HR organizational manual (`uploads/hr_extracted/hr_source.pdf`).
- Completed Phase 2 deep-dive research across 11 architectural topics (`research/01` $\rightarrow$ `11`).
- Created consolidated `IMPLEMENTATION_PLAN.md` and `PROJECT_MAP.md` under `_development_docs_REMOVE_BEFORE_DEPLOYMENT/`.

---

## 2026-07-19 session 2 (Workspace Recovery & Agent Rules Governance Lock)
- Recovered extracted project structure (`workspace-019f77a8-9fbc-70cb-a35c-b6d5442a6015.zip`).
- Read and analyzed `uploads/AGENT_RULES copy 2.md` containing Ahmed's 29 mandatory standing instructions, standing context, and repository/storytelling requirements.
- Created `_working_docs/AGENT_RULES.md` containing all 29 original rules plus Rule 30 (Workspace Architecture & Document Governance), ensuring seamless integration between general project docs and mandatory AI workflow docs.
- Initialized `_working_docs/AUDIT_AND_TODO.md` with active gaps for Phase 3/4 execution (`GAP-ASKC-01` $\rightarrow$ `GAP-ASKC-05`).
- Initialized `_working_docs/IMPLEMENTATION_LOG.md`, `CHANGELOG.md`, and `NEXT_SESSIONS_ROADMAP.md` to guarantee 100% adherence to Rule 29 context recovery protocol.
- Inspected and analyzed `uploads/improved_rag_gui (16).html` via BeautifulSoup/regex and presented the interactive sketch to Ahmed using `present_file`.
- Locked the exact UI/UX patterns from the sketch (3-panel resizable layout, knowledge base scope cards with Cyrkil green `1px solid rgba(155,227,107,.55)` outlines, RTL typography, and theme toggling) into `GAP-ASKC-04` (`_working_docs/AUDIT_AND_TODO.md`) and recorded closure of `GAP-INIT-03`.

---

## 2026-07-19 session 3 (GitHub Genesis Repository Creation & `GAP-ASKC-01` Ingestion Execution)
- Verified GitHub PAT and created repository `https://github.com/Ahmed-Sleem/arabic-staff-knowledge-chatbot.git` using GitHub REST API via curl (`GAP-INIT-04`).
- Initialized git repository at root, wrote story-driven `README.md` per **Ahmed's Repository Creation & Storytelling Style (Mandatory Rule)**, configured `.gitignore`, and pushed initial project state to `origin/main` (`commit 257dbb9`).
- Updated `_working_docs/AUDIT_AND_TODO.md` (`GAP-ASKC-06`) to formally add the requirement: **LLM API Key Settings UI** (allowing staff/admins to save custom DeepSeek/OpenAI API keys in the GUI and transmit via `X-LLM-API-Key` headers).
- Scaffolded `src/backend/` structure (`models.py`, `database.py`, `ingestion/parse_hr_pdf.py`, `tests/test_ingestion.py`).
- Implemented `parse_hr_pdf.py` with custom text normalizers (`fix_kerning` + `normalize_pdfplumber_table_cell`) handling Arabic font kerning and reversing RTL visual ordering while preserving formulas and English acronyms (`TRIR`, `PMO`).
- Executed ingestion against `hr_source.pdf`: extracted and persisted `503 sections, 58 job descriptions, 220 KPIs, and 4 escalation rules` to relational database and `data/hr_indexed.json`.
- Verified `GAP-ASKC-01` closure via 100% green automated pytest suite (`4 passed in 17.78s`).

---

## 2026-07-19 session 4 (Universal Workspace Expansion, Bilingual AR/EN Toggle & Obsidian Graph View Architecture Lock)
- Dissected and registered all new universal capabilities from Ahmed into `_working_docs/AUDIT_AND_TODO.md` (`GAP-ASKC-07` through `GAP-ASKC-10`, `GAP-INIT-05`).
- **Bilingual AR/EN Direct Toggle:** Locked instant switching (`dir="rtl" <-> dir="ltr"`, UI translation, and system prompt language adjustment).
- **Universal Relational RAG Pipeline (`GAP-ASKC-07`):** Re-architected data layer to accept any uploaded document (`PDF`, `DOCX`, `TXT`, `MD`), chunk dynamically by structural headings/tables, analyze with user LLM API keys (`X-LLM-API-Key`), extract semantic link connections (`chunk_connections`), build TOC hierarchy (`toc_tree`), and store persistently inside multi-document SQLite/Postgres schemas (`documents`, `chunks`, `chunk_connections`, `tables`) surviving app restarts.
- **Data Panel Dual-View Toggle (`GAP-ASKC-08`):** Locked 3rd panel top switch `[ 📁 Files | 🕸️ Obsidian Graph ]`:
  - `Files View:` Persistent multi-document browser, status pills (`Ready`), dropzone uploader, delete button (`🗑️`), and chat scope selection.
  - `Obsidian Graph View:` High-fidelity force-directed interactive mindmap (`react-force-graph-2d` / HTML5 Canvas).
- **Live Agent Traversal Animation:** Designed real-time SSE stream integration (`agent_search` / `active_node_ids`) causing the Obsidian Graph View to automatically pan/zoom (`centerAt(x, y, 1000)` / `zoomToFit`) to focus on active chunks, pulse glowing Cyrkil green node rings (`#9BE36B`), and open exact chunk content when clicked.

---

## 2026-07-19 session 5 (Modular Code Organization & Universal Dynamic RAG Execution `GAP-ASKC-07`)
- Organized `src/backend/` into modular, domain-driven packages (`models/`, `db/`, `services/ingestion/parsers/`) suitable for clean production scaling and maintenance per `Rule 26`.
- Migrated legacy `models.py` to `models/legacy.py` and implemented multi-document persistent schemas in `models/orm.py` and `models/domain.py` (`ConfigDict` clean Pydantic DTOs).
- Implemented `db/session.py` and `db/repositories.py` (`DocumentRepository`, `ChunkRepository`, `GraphRepository`, `TableRepository`) with idempotent document replacement (`create_document` auto-cleans old chunks) and bilingual keyword `search_chunks`.
- Implemented modular ingestion engine (`services/ingestion/`):
  - `normalizer.py`: Bilingual text normalizer (`fix_kerning`, RTL table orientation repair, acronym protection).
  - `parsers/` (`pdf_parser.py`, `docx_parser.py`, `text_parser.py`): Multi-format structural parsing for `.pdf`, `.docx`, `.md`, and `.txt`.
  - `chunker.py`: Dynamic structural chunker dividing content by heading hierarchy and generating `toc_tree_json`.
  - `graph_builder.py`: Extracts hierarchical parent-child edges AND semantic keyword cross-references across chunks (`ChunkConnectionORM`) for force-directed rendering.
  - `universal_pipeline.py`: Master multi-document ingestion orchestrator.
- Created `tests/test_universal_pipeline.py` and ran complete verification across all 10 unit and integration tests (`test_ingestion.py` + `test_universal_pipeline.py`). Confirmed 100% test pass (`10 passed in 38.17s`), including explicit verification that persistent documents, Table of Contents hierarchies, and `450+` Obsidian Graph nodes survive simulated database restarts.

---

## 2026-07-19 session 6 (FastAPI Core Routing & ReAct Streaming Agent with Live Graph Events `GAP-ASKC-02/03`)
- Implemented universal retrieval tools in `src/backend/agent/tools.py` (`search_chunks`, `get_table`, `get_chunk_relations`, `get_document_toc`) executing directly against our repository layer.
- Implemented `src/backend/agent/react_agent.py` featuring:
  - Dynamic API key resolution (`X-LLM-API-Key` header or server fallback without hardcoded production constraints).
  - System prompt generation enforcing strict AR/EN inline citations (`[المصدر: القسم X.Y - العنوان]`) and standard out-of-scope refusal.
  - ReAct tool execution loop (`run_agent_stream`) yielding live `{"event": "agent_search", "data": "{"query": "...", "active_node_ids": [...]}"}` dictionaries before token generation (`{"event": "token", "data": token}`).
- Implemented `src/backend/api/documents.py` providing `POST /api/v1/documents/upload`, `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`, and `GET /api/v1/documents/graph`.
- Implemented `src/backend/api/chat.py` providing `POST /api/v1/chat/stream` SSE generator.
- Implemented `src/backend/main.py` with CORS middleware (`allow_origins=["*"]`) and modern Lifespan startup DB initialization.
- Created `src/backend/tests/test_api.py` and `src/backend/tests/test_react_agent.py` and executed verification across the full backend suite (`PYTHONPATH=/home/user/src/backend pytest -v tests/`). All **15 automated tests passed 100% (`15 passed in 58.14s`)**.
