# Next Sessions Roadmap

**Architectural Guide for Future Sessions per Rule 29 Context Recovery Protocol.**
Read this file on every session start or context reset.

---

## Current Architecture & Project Status

### The Project: Cyrkil Universal Knowledge Workspace & Arabic/English Staff Chatbot
- **Goal:** Build an enterprise-grade, bilingual (`AR / EN`) internal knowledge platform and chatbot for Kayan Al-Mamlaka Company (`شركة كيان المملكة كاك`) and Cyrkil customers.
- **Key Capabilities:**
  1. **Universal Relational RAG Ingestion:** Accepts any uploaded user document (`PDF`, `DOCX`, `TXT`, `MD`), dynamically chunks by structure (`H1`, `H2`, `Table`), extracts semantic links (`chunk_connections`), and builds TOC hierarchy persistently in SQLite/Postgres (`data/knowledge_workspace.db`). Survives restarts until explicit deletion.
  2. **Bilingual Direct Toggle (`AR / EN`):** Instant layout (`dir="rtl" <-> dir="ltr"`), UI string, and LLM response language switching.
  3. **Obsidian Graph View & Dual Data Panel:** 3rd panel toggles between File Browser (`[ 📁 Files ]`) and interactive force-directed mindmap (`[ 🕸️ Obsidian Graph ]`). As the ReAct agent searches chunks during SSE streaming, the Graph View animates camera panning (`centerAt`) and node pulsing (`active_node_ids`) in real time!
  4. **Dynamic API Key Manager (`Add API Key`):** Staff enter custom DeepSeek/OpenAI API keys right in the GUI settings modal (`X-LLM-API-Key` header).
- **Phases Completed:** Phase 1 (Requirements), Phase 2 (11 Topic Deep-Dives), GitHub Genesis Repo (`Ahmed-Sleem/arabic-staff-knowledge-chatbot`), & Proof-of-Concept HR Guide Ingestion (`GAP-ASKC-01`).
- **Active Phase:** Universal Relational RAG Pipeline & Streaming Backend Execution (`GAP-ASKC-07` $\rightarrow$ `GAP-ASKC-02/03`).

---

## Roadmap of Execution Steps (ONE BY ONE per Rule 6)

1. **Step 1: Universal Dynamic Relational RAG Pipeline & Multi-Document Database (`GAP-ASKC-07`)**
   - Expand `src/backend/models.py` and `src/backend/database.py` to universal multi-document schemas:
     - `documents`: `id`, `filename`, `file_type`, `upload_time`, `status`, `toc_tree_json`, `raw_file_path`.
     - `chunks` (`sections`): `id`, `document_id`, `chunk_code`, `title`, `content`, `page_number`, `chunk_type` (`text`, `table`, `code`), `tsvector` full-text search index.
     - `chunk_connections` (`graph_edges`): `id`, `source_chunk_id`, `target_chunk_id`, `relation_type` (`parent_child`, `semantic_link`, `cross_reference`), `weight`.
     - `tables`: `id`, `document_id`, `table_name`, `headers_json`, `rows_json`.
   - Build `src/backend/ingestion/universal_pipeline.py` handling `PDF`, `DOCX`, `TXT`, and `MD` with dynamic structural chunking, table extraction, and semantic edge extraction.
   - Write automated `pytest` (`tests/test_universal_pipeline.py`) asserting multi-document persistence and graph link generation.

2. **Step 2: FastAPI Core Routing & ReAct Agent with Live Graph SSE Events (`GAP-ASKC-02` / `GAP-ASKC-03`)**
   - Build `src/backend/main.py` with multi-document upload endpoints (`POST /api/v1/documents/upload`, `GET /api/v1/documents`, `DELETE /api/v1/documents/{id}`, `GET /api/v1/documents/graph`).
   - Build `src/backend/agent/react_agent.py` using `deepseek-chat` via OpenAI SDK with dynamic `X-LLM-API-Key` header ingestion and universal retrieval tools (`search_chunks`, `get_table`, `get_chunk_relations`).
   - Implement `POST /api/v1/chat/stream` SSE streaming that emits `agent_search` / `active_node_ids` events during tool execution.

3. **Step 3: Next.js 15 Cyrkil 3-Panel GUI with Obsidian Graph View & AR/EN Toggle (`GAP-ASKC-08` / `GAP-ASKC-06`)**
   - Build full bilingual (`dir="rtl" <-> dir="ltr"`) 3-panel UI in `src/frontend/` using Cyrkil design tokens.
   - Build the **Data Panel Dual-View Toggle (`[ 📁 Files | 🕸️ Obsidian Graph ]`)**:
     - `Files View:` Upload dropzone, file list, stats, delete buttons, and chat scope selection.
     - `Obsidian Graph View (`react-force-graph-2d` / HTML5 Canvas):` Interactive force-directed network mindmap. Connects to SSE `agent_search` stream to smoothly pan/zoom (`centerAt(x, y, 1000)` / `zoomToFit`), pulse glowing active node rings (`#9BE36B`), and open exact chunk text when clicked.
   - Build the `Add API Key` (`إضافة مفتاح API`) header modal.

4. **Step 4: End-to-End Acceptance Verification & Live Testing**
   - Test full bilingual pipeline with Ahmed's DeepSeek API key across `hr_source.pdf` and custom uploaded files. Verify Obsidian Graph animations and persistent multi-document reloads.
