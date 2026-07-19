# Next Sessions Roadmap

**Architectural Guide for Future Sessions per Rule 29 Context Recovery Protocol.**
Read this file on every session start or context reset.

---

## Current Architecture & Project Status

### The Project: Arabic Staff Knowledge Chatbot (Cyrkil Ecosystem)
- **Goal:** Build an internal KSA-company AI assistant answering staff questions in Arabic ONLY, grounded strictly in `uploads/hr_extracted/hr_source.pdf` (Organizational Structure and KPI Guide v1.0).
- **Phases Completed:** Phase 1 (Requirements & Scope) & Phase 2 (11 Topic Deep-Dives in `research/`).
- **Active Phase:** Phase 3/4 Execution — Backend structural RAG ingestion, FastAPI core services, ReAct agent tools, and Next.js 15 Cyrkil frontend.

---

## Roadmap of Execution Steps (ONE BY ONE per Rule 6)

1. **Step 1: Backend Structure Ingestion Pipeline (`GAP-ASKC-01`)**
   - Write `src/backend/ingestion/parse_hr_pdf.py` using `pypdf` / `pdfplumber` to extract organizational hierarchy, job descriptions, KPI formulas/targets, and escalation matrices from `hr_source.pdf`.
   - Populate relational Postgres tables (`sections`, `job_descriptions`, `kpis`, `escalation_rules`) and generate Arabic `tsvector` indexes.
   - Verify via automated pytest assertions checking row counts and search precision.

2. **Step 2: FastAPI Core Routing & ARQ Redis Background Workers (`GAP-ASKC-02`)**
   - Build `src/backend/main.py` with async SQLAlchemy pooling and ARQ Redis worker integration for document processing and async tasks.
   - Implement SSE token streaming endpoint (`/api/v1/chat/stream`).

3. **Step 3: DeepSeek Non-Thinking ReAct Agent & Tool Suite (`GAP-ASKC-03`)**
   - Implement `src/backend/agent/react_agent.py` using OpenAI Python SDK calling `deepseek-chat` (`REMOVED_PROVIDER_CREDENTIAL`).
   - Wire 5 specialized tools (`search_sections`, `get_job_description`, `get_kpis`, `get_escalation_path`, `get_reporting_line`).
   - Enforce exact inline citation format `[المصدر: القسم X.Y - العنوان]` and out-of-scope refusal `عذراً، هذه المعلومة غير متوفرة في دليل الهيكل التنظيمي المعتمد حالياً.`

4. **Step 4: Next.js 15 Cyrkil-Styled Frontend (`GAP-ASKC-04`)**
   - Build full RTL (`dir="rtl"`) chat UI in `src/frontend/` using IBM Plex Sans Arabic font and Cyrkil design system (`uploads/DESIGN_SYSTEM.md`).
   - Implement interactive citation cards that open a right-hand drawer highlighting the exact text chunk from `hr_source.pdf`.

5. **Step 5: 2-Step Authentication (`GAP-ASKC-05`)**
   - Implement Argon2id password verification followed by 6-digit email OTP (10-minute expiry) and server-side sessions.
