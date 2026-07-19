# Project Documentation Index

**Project:** Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين)
**Status:** Phase 2 — Deep Dive (per `agent general task brainstoring.md`)
**Last update:** 2026-07-10

---

## Start here

1. **`PROJECT_MAP.md`** — human-readable map of the project workspace (folders, files, sources).
2. **`DEVELOPMENT_REQUIREMENTS.md`** — the process rules we're following (copy of the input).
3. **`IMPLEMENTATION_PLAN.md`** — the phased plan we will execute (created in Phase 3).
4. **`THINGS_DONE.md`** — append-only log of completed work (per validation cycles).
5. **`SUPPORTING_NOTES.md`** — merged special notes (design, deployment, security, mobile, testing).

---

## Source documents (in `uploads/`)

- `DESIGN_SYSTEM.md` — mandatory UI / engineering style guide (Cyrkil).
- `DEVELOPMENT_REQUIREMENTS.md` — general dev process rules.
- `agent general task brainstoring.md` — 4-phase brainstorming process.
- `PRD_ Arabic Staff Knowledge Chatbot.pdf` — the product requirements.
- `hr_structure_compressed.pdf.zip` → `uploads/hr_extracted/hr_source.pdf` — the source document the chatbot will answer from. **Do not read the contents until the deep-dive phase needs it.** (PRD already tells us its structure: organizational guide, job descriptions, KPIs, reporting lines, escalation matrix.)

---

## Research workspace (in `research/`)

One file per topic. Append-only. Use copy-paste, never rewrite from scratch.

| # | Topic | File |
|---|---|---|
| 1 | RAG & retrieval design (Arabic) | `research/01_rag_and_retrieval.md` |
| 2 | DeepSeek API specifics | `research/02_deepseek_api.md` |
| 3 | PDF ingestion pipeline (Arabic) | `research/03_pdf_ingestion.md` |
| 4 | Backend (FastAPI) design | `research/04_backend_fastapi.md` |
| 5 | Frontend (Next.js, Cyrkil-styled) | `research/05_frontend_nextjs.md` |
| 6 | Authentication (email + password + email OTP) | `research/06_authentication.md` |
| 7 | Portability & free-tier deployment | `research/07_deployment_portability.md` |
| 8 | Observability, security, testing | `research/08_observability_security_testing.md` |
| 9 | Admin upload & version management | `research/09_admin_upload_versioning.md` |
| 10 | Arabic NLP specifics | `research/10_arabic_nlp.md` |
| 11 | Compliance / data handling | `research/11_compliance_data.md` |

---

## Process

- We are in **Phase 2 — Deep Dive per Topic** of the brainstorming process.
- Each topic gets its own deep dive in its `.md` file.
- After Phase 2 is done, we move to **Phase 3 — Consolidation, Conflict Resolution & Plan Creation** (which fills `IMPLEMENTATION_PLAN.md`).
- Phase 4 = implementation (we're not there yet).
