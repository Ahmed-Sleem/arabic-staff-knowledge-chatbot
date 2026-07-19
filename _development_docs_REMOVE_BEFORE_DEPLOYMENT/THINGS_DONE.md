# Things Done — Append-Only Log

**Last update:** 2026-07-10

> Per `DEVELOPMENT_REQUIREMENTS.md §2 Step 5`, every completed step is appended here.
> This file is append-only. Never overwrite, never delete past entries.

---

## 2026-07-10 — Phase 1: Topic Identification & Initial Gathering

- **Phase / task:** Read inputs; identify subjects; ask clarifying questions; lock topic list.
- **Files read:**
  - `uploads/PRD_ Arabic Staff Knowledge Chatbot.pdf` (extracted via pypdf, 17 pages)
  - `uploads/DESIGN_SYSTEM.md`
  - `uploads/DEVELOPMENT_REQUIREMENTS.md`
  - `uploads/agent general task brainstoring.md`
- **Files handled (data):**
  - Renamed `uploads/‎⁨دليل_الهيكل..._compressed⁩.pdf.zip.txt` → `uploads/hr_structure_compressed.pdf.zip` (removed `.txt`).
  - Extracted to `uploads/hr_extracted/hr_source.pdf` (5.7 MB). **Contents not read yet** — to be processed in Phase 2 topic 3.
- **User decisions locked:**
  - Architecture: Option A (Next.js + FastAPI + vector DB).
  - Design: full Cyrkil design system.
  - LLM: DeepSeek API.
  - Embeddings + vector store: open, to be researched in Phase 2.
  - Auth: email + password + email OTP.
  - MVP scope: staff chat + admin upload + question logs dashboard.
  - Deployment: online cloud, free-tier friendly, but **portable** to on-prem / private cloud.
- **Topic list (Phase 2 subjects, 11 total):** RAG & retrieval, DeepSeek API, PDF ingestion, FastAPI backend, Next.js frontend, auth, deployment/portability, observability/security/testing, admin upload/versioning, Arabic NLP, compliance/data.
- **Validation:** No code yet — N/A.
- **Next step:** Begin Phase 2 deep dive, starting with topic 1 (RAG & retrieval design) since it gates most of the other topics (especially embeddings choice and vector store choice).

## 2026-07-10 — Phase 2: Deep Dive per Topic (complete)

- **Phase / task:** Research + reasoning for all 11 topics, append findings to `research/*.md`.
- **Topics covered:**
  1. RAG & retrieval design → BGE-M3 / Jina v3 / multilingual-e5 shortlist; hybrid search (pgvector + tsvector + RRF) confirmed best practice.
  2. DeepSeek API → `deepseek-v4-flash` (non-thinking) as default; cost ~$0.0008/question; Arabic quality competitive.
  3. PDF ingestion → PyMuPDF / pymupdf4llm + pdfplumber for tables; section-aware chunker; data file inspected (64 pages, 16.7K Arabic words, 4-level numbering, ~300-500 chunks expected).
  4. FastAPI backend → no LangChain/LlamaIndex; hand-rolled pipeline; SSE streaming; full project structure drafted.
  5. Next.js + Cyrkil → TanStack Query v5 + native EventSource; IBM Plex Sans Arabic; logical CSS properties; Cyrkil tokens unchanged.
  6. Auth → email + password (argon2) + email OTP (6 digits, 10min, single-use, max 5 attempts); httpOnly + Secure + SameSite=Lax session cookie; Resend (cloud) / Postfix (self-host).
  7. Deployment & portability → Vercel + Fly.io + Neon (cloud) or Coolify + Docker Compose (self-host); env-var portability only.
  8. Observability, security, testing → Sentry (cloud) or GlitchTip (self-host) — same SDK; RAGAS-style in-house eval harness; prompt-injection via document-injection (PDF as attack surface) is a real risk — wrap chunks in `<retrieved_document>` tags.
  9. Admin upload & versioning → object storage (R2/MinIO) for raw PDF; one-active-document rule; test-mode before promote; full audit trail.
  10. Arabic NLP → `pyarabic` for normalization (tashkeel, tatweel, alef, yeh, teh marbuta); keep Latin tokens; preserve original text for display.
  11. Compliance / PDPL → 7 core obligations mapped; deepSeek as documented sub-processor; user data rights endpoints; 72-hour breach procedure documented; SDAIA SCCs needed for cross-border transfer; self-hosted DeepSeek as cleanest residency option.
- **Data file:** inspected (page 1 + TOC) for actual structure. Empirical findings saved to `research/03_pdf_ingestion.md`. Total: 64 pages, ~16,700 Arabic words.
- **Key locked decisions** (per topic findings, to be ratified in Phase 3):
  - LLM: `deepseek-v4-flash` (non-thinking, default)
  - Embeddings: **Jina v3** hosted (free tier) for MVP, plan for self-hosted BGE-M3 for portability
  - Vector store: **pgvector** (in the same Postgres as app data)
  - Lexical: Postgres `tsvector` with `simple` config + Arabic normalization
  - Fusion: RRF (k=60), top-50 from each → top-10
  - Rerank: cross-encoder optional in v2
  - PDF parser: `pymupdf4llm` for markdown, `pdfplumber` for KPI tables
  - Chunking: section-aware, keep each job role's full description together
  - Frontend: Next.js 15 App Router + TanStack Query v5 + native EventSource
  - Font: IBM Plex Sans Arabic
  - Email (cloud): Resend. (Self-host): Postfix
  - Error tracking: Sentry (cloud) / GlitchTip (self-host) — same SDK
  - Auth: argon2 + email OTP + server-side session in Postgres
  - Deployment: env-var portability between cloud (Vercel + Fly.io + Neon) and self-host (Coolify + Docker Compose)
- **Validation:** Research is in append-only MD files. No code yet. Phase 3 next.
- **Next step:** Move to Phase 3 — consolidate findings, resolve any conflicts, write the full `IMPLEMENTATION_PLAN.md` and `SUPPORTING_NOTES.md`.


## 2026-07-10 — Phase 3: Consolidation, Conflict Resolution & Plan Creation (complete)

- **Phase / task:** Consolidate all 11 research findings into a single executable plan; resolve any conflicts; write `IMPLEMENTATION_PLAN.md` and `SUPPORTING_NOTES.md`.
- **User discussion (multiple rounds):**
  - RAG architecture options presented and discussed: Naive, Advanced, Agentic, HyDE, Section-router.
  - User pivoted to **no vector DB**, asked for cutting-edge alternatives.
  - Researched: LLM Wiki pattern, Prompt-RAG, TreeRAG, Hierarchical RAG, ReAct tool-calling.
  - Final decision: **Prompt-RAG + ReAct tool-calling hybrid** (Option 2 hybrid). No embeddings, no vector DB. 5 tools (list_sections, get_section, get_subsections, search_keyword, get_kpi_table, get_escalation_path). LLM decides which tool to use, aware of retries (default 5, configurable).
  - Python stack: SQLAlchemy 2.x async, OpenAI Python SDK pointed at DeepSeek, ARQ (Redis) for background jobs, structlog + JSON logging.
  - Frontend: Next.js 15 + TanStack Query v5 + native EventSource + IBM Plex Sans Arabic.
  - Auth: email + password (argon2id) + email OTP on new device. Invite-only registration.
  - Deployment: env-var-only portability. Cloud (Vercel + Fly.io + Neon + R2 + Resend) and self-host (Coolify + Docker Compose) from one codebase.
- **Files written:**
  - `IMPLEMENTATION_PLAN.md` — full 7-phase plan with acceptance criteria, file lists, validation commands.
  - `SUPPORTING_NOTES.md` — public-safe naming, GUI requirements, deployment, security checklist, mobile policy, testing, PDPL compliance, operational runbooks, glossary.
- **Decisions documented:** all locked decisions are in `IMPLEMENTATION_PLAN.md §3` (Locked Tech Decisions table).
- **Phase plan:** 7 phases, each ending with a working, validated, committed checkpoint.
- **Phase 1 starts next:** project skeleton + docker-compose + ingestion script on the actual PDF.
- **Next step:** Begin Phase 1 implementation. Await user "go" signal.

