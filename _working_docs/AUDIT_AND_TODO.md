# Audit & To-Do List

**Project:** Cyrkil Ecosystem / Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين)
**Last Updated:** 2026-07-19
**Governance:** Every new gap discovered mid-work is appended here per Rule 4. Gaps are fixed ONE BY ONE per Rule 6.

---

## Active Implementation Gaps (Arabic Staff Knowledge Chatbot Phase 3/4)

### [M1] GAP-ASKC-01: Backend Structure Ingestion Pipeline for `hr_source.pdf`
- **Description:** Implement the Python ingestion script (`src/backend/ingestion/parse_hr_pdf.py`) that extracts organizational sections, KPI tables, and administrative escalation paths from `uploads/hr_extracted/hr_source.pdf` into relational Postgres tables (`sections`, `job_descriptions`, `kpis`, `escalation_rules`) with Arabic `tsvector` indexing.
- **Status:** Open
- **Assigned:** Phase 3 Execution

### [M1] GAP-ASKC-02: FastAPI Core Routing & ARQ Redis Background Workers
- **Description:** Implement FastAPI application (`src/backend/main.py`), async SQLAlchemy database session management, and ARQ background task queues (`src/backend/workers.py`) per `research/04_backend_fastapi.md`.
- **Status:** Open
- **Assigned:** Phase 3 Execution

### [M1] GAP-ASKC-03: DeepSeek Non-Thinking RAG Streaming & Tool Integration
- **Description:** Implement the ReAct agent service (`src/backend/agent/react_agent.py`) utilizing `deepseek-chat` via OpenAI SDK with 5 tools (`search_sections`, `get_job_description`, `get_kpis`, `get_escalation_path`, `get_reporting_line`), inline citation formatting, and strict out-of-scope refusal handling.
- **Status:** Open
- **Assigned:** Phase 3 Execution

### [M1] GAP-ASKC-04: Next.js 15 Cyrkil-Styled Frontend & SSE Chat Interface (Locked to `improved_rag_gui (16).html` Sketch)
- **Description:** Implement the frontend (`src/frontend/`) using Next.js 15 App Router, TanStack Query v5, native EventSource for token streaming, and Cyrkil design tokens locked directly to the `improved_rag_gui (16).html` sketch architecture:
  - **3-Panel Split Layout:** `panel-left` (conversation stack & history search), `panel-middle` (knowledge base explorer & document scope selection cards like `folder-card` / `file-card`), and `panel-right` (RAG chat conversation feed & composer).
  - **Interactive Panel Resizing:** Drag handles (`resize-handle` with `col-resize`) clamping dynamic widths via CSS variables (`--left-width`, `--file-width`).
  - **Document Scope Filtering:** Clicking any knowledge base card (`folder-card` or `file-card`) outlines it with `1px solid rgba(155,227,107,.55)` (Cyrkil green accent) and scopes the chat prompt (`Ask about [Source Name]...`).
  - **Inline Citation & Right-Hand Excerpt Drawer:** Interactive citation chips (`[المصدر: القسم X.Y]`) in AI responses that highlight and reveal the exact source passage from `hr_source.pdf`.
  - **Full RTL & Theme Toggling:** Native Arabic typography (IBM Plex Sans Arabic, `dir="rtl"`), subtle glass elevation, and seamless `#themeToggle` between dark and light modes (`.light-mode`).
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
