# Audit & To-Do List

**Project:** Cyrkil Ecosystem / Arabic Staff Knowledge Chatbot & Universal Knowledge Workspace
**Last Updated:** 2026-07-19
**Governance:** Every new gap discovered mid-work is appended here per Rule 4. Gaps are fixed ONE BY ONE per Rule 6.

---

## Active Implementation Gaps (Universal Relational RAG Workspace - Phase 3/4)

### [M1] GAP-ASKC-07: Universal Dynamic Relational RAG Pipeline & Multi-Document Database (`src/backend/ingestion/universal_pipeline.py`)
- **Description:** Upgrade our data layer from single-PDF ingestion into a **Universal Relational RAG Engine** supporting any uploaded user file (`PDF`, `DOCX`, `TXT`, `MD`).
  - **Dynamic Ingestion:** Accepts uploaded files (`POST /api/v1/documents/upload`), extracts raw text via multi-format parsers (`pypdf`, `pdfplumber`, `python-docx`, `markdown`), cleans and normalizes Arabic/English formatting, and chunks dynamically based on structural headings (`H1`, `H2`, `Table`, `List`).
  - **Dynamic LLM Analysis & Semantic Graph Extraction:** Uses the user-provided LLM API key (`X-LLM-API-Key`) or heuristic parser to analyze each chunk, generate concise titles (`title`), extract semantic cross-references/links (`chunk_connections` / graph edges), and build the Table of Contents (`toc_tree`).
  - **Persistent Multi-Document Storage:** Stores uploaded source files (`data/uploads/`) and relational records (`documents`, `chunks`, `chunk_connections`, `tables`) persistently inside SQLite/Postgres (`data/knowledge_workspace.db`). Survives app restarts and browser refreshes until explicit user deletion (`DELETE /api/v1/documents/{id}`).
- **Status:** Open (Next Execution Step)
- **Assigned:** Phase 3 Execution

### [M1] GAP-ASKC-02 & GAP-ASKC-03: FastAPI Streaming Server & ReAct Agent with Graph Events (`src/backend/main.py`, `agent/react_agent.py`)
- **Description:** Implement the FastAPI application (`src/backend/main.py`), async session management, and ReAct agent service (`src/backend/agent/react_agent.py`) using `deepseek-chat` via OpenAI SDK.
  - **Universal Retrieval Tools:** Equip the agent with universal tools (`search_chunks`, `get_table`, `get_chunk_relations`, `get_document_toc`).
  - **Dynamic Header Key:** Routes requests dynamically using the user's `X-LLM-API-Key` header (`Authorization: Bearer <user_key>`), falling back to server environment key if missing.
  - **Live Graph Animation SSE Events:** During streaming (`POST /api/v1/chat/stream`), as the ReAct agent executes retrieval tools across chunks, emit live node-activation SSE events (`data: {"event": "agent_search", "query": "...", "active_node_ids": ["chunk_12", "chunk_15"]}`) so the frontend Obsidian Graph View can pan and highlight active chunks in real time.
  - **Bilingual Grounding:** Enforces exact inline citations (`[المصدر: ...]` / `[Source: ...]`) and answers cleanly in either Arabic or English based on the user's language toggle (`X-App-Language: ar | en`).
- **Status:** Open
- **Assigned:** Phase 3 Execution

### [M1] GAP-ASKC-08: Next.js 15 Cyrkil 3-Panel GUI with Obsidian Graph View & Dual-View Toggle (`src/frontend/`)
- **Description:** Build our locked 3-panel resizable Cyrkil frontend (`src/frontend/`) incorporating:
  - **Bilingual AR/EN Direct Toggle:** Instant toggle button (`عربي | English`) switching layout (`dir="rtl" <-> dir="ltr"`), UI strings (`i18n`), and API language context.
  - **Panel 1 (Left / Conversation Stack):** Searchable conversation history and new chat trigger.
  - **Panel 2 (Center / RAG Chat Composer):** Conversation feed with typing indicators and interactive citation chips (`[المصدر: القسم X.Y]`) that click open an excerpt modal/drawer.
  - **Panel 3 (Right / Data Panel Dual-View Toggle):** Header toggle `[ 📁 Files | 🕸️ Obsidian Graph ]`:
    - **View 1 (File Browser):** Lists persistent uploaded documents, drag-and-drop uploader (`POST /api/v1/documents/upload`), status indicators (`Indexed`, `Ready`), delete button (`🗑️`), and scope filter checkboxes.
    - **View 2 (Obsidian Graph View / Interactive Mindmap):** High-fidelity force-directed network graph (`react-force-graph-2d` / HTML5 Canvas) where every chunk is a node and semantic links are edges.
      - **Live Traversal Animation:** Listens to SSE `agent_search` / `active_node_ids` events during chat queries, animating camera panning (`centerAt(x, y, 1000)` / `zoomToFit`), pulsing glowing Cyrkil green rings around nodes (`#9BE36B`), and emitting link particles (`emitParticle`).
      - **Interactive Exploration:** Manual dragging of nodes, pan/zoom, and click-to-open full chunk content in a modal drawer.
- **Status:** Open
- **Assigned:** Phase 4 Execution

### [M1] GAP-ASKC-06: Dynamic LLM API Key Management Modal (`إضافة مفتاح API` / `Add API Key`)
- **Description:** Implement a dedicated settings modal in the Cyrkil header (`🔑 Add API Key` / `إضافة مفتاح API`) where staff/admins can input their own DeepSeek/OpenAI API key (`sk-...`). Persists in client state/headers and routes dynamically to `/api/v1/chat/stream` (`X-LLM-API-Key`).
- **Status:** Open
- **Assigned:** Phase 4 Execution

### [P2] GAP-ASKC-05: 2-Step Authentication (Email/Password + 6-Digit Email OTP)
- **Description:** Implement Argon2id password hashing + 10-minute 6-digit OTP delivery flow and server-side sessions per `research/06_authentication.md`.
- **Status:** Open
- **Assigned:** Phase 4 Execution

---

## Closed & Verified Gaps

- **[CLOSED] GAP-INIT-01:** Project structure recovery and extraction of source materials (`uploads/hr_extracted/hr_source.pdf`, `PRD_ Arabic Staff Knowledge Chatbot.pdf`, `DESIGN_SYSTEM.md`). Verified on 2026-07-19.
- **[CLOSED] GAP-INIT-02:** Recovery and completion of mandatory agent working rules (`_working_docs/AGENT_RULES.md` & governance files). Verified on 2026-07-19.
- **[CLOSED] GAP-INIT-03:** UI/UX sketch analysis & architectural blueprint lock (`uploads/improved_rag_gui (16).html` $\rightarrow$ `GAP-ASKC-04`). Verified on 2026-07-19.
- **[CLOSED] GAP-INIT-04:** GitHub repository creation (`Ahmed-Sleem/arabic-staff-knowledge-chatbot`), story-driven README, and initial git push. Verified on 2026-07-19.
- **[CLOSED] GAP-ASKC-01:** Backend structure ingestion pipeline (`src/backend/ingestion/parse_hr_pdf.py`) and relational models (`models.py`, `database.py`) extracting `503 sections, 58 job descriptions, 220 KPIs, and 4 escalation rules` from `hr_source.pdf`. Verified via 100% green pytest suite (`test_ingestion.py`) on 2026-07-19.
