# Project Map

**Project:** Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين)
**Last update:** 2026-07-10

---

## Workspace root: `/home/user/`

```
/home/user/
├── uploads/                                 # Source materials (read-only inputs)
│   ├── DESIGN_SYSTEM.md                     # Mandatory Cyrkil design system
│   ├── DEVELOPMENT_REQUIREMENTS.md          # General dev process rules
│   ├── agent general task brainstoring.md   # 4-phase brainstorming process
│   ├── PRD_ Arabic Staff Knowledge Chatbot.pdf  # The PRD
│   ├── hr_structure_compressed.pdf.zip      # Renamed from the .txt extension
│   └── hr_extracted/
│       └── hr_source.pdf                    # Unzipped — the knowledge base PDF
│
├── research/                                # Phase 2 deep-dive notes (append-only)
│   ├── 01_rag_and_retrieval.md
│   ├── 02_deepseek_api.md
│   ├── 03_pdf_ingestion.md
│   ├── 04_backend_fastapi.md
│   ├── 05_frontend_nextjs.md
│   ├── 06_authentication.md
│   ├── 07_deployment_portability.md
│   ├── 08_observability_security_testing.md
│   ├── 09_admin_upload_versioning.md
│   ├── 10_arabic_nlp.md
│   └── 11_compliance_data.md
│
├── _development_docs_REMOVE_BEFORE_DEPLOYMENT/  # Process & planning docs
│   ├── README.md                            # This index
│   ├── PROJECT_MAP.md                       # This file
│   ├── DEVELOPMENT_REQUIREMENTS.md          # Copy of input for reference
│   ├── IMPLEMENTATION_PLAN.md               # Created in Phase 3
│   ├── THINGS_DONE.md                       # Append-only done log
│   └── SUPPORTING_NOTES.md                  # Special notes (created in Phase 3)
│
└── (later, in Phase 4)                      # The actual project will live in its own folder
    └── (project code, not yet created)
```

---

## Key reference points

### Product (from PRD)

- **Goal:** Internal Arabic AI chatbot that answers staff questions in Arabic **only**, using a single PDF as the source of truth.
- **KPIs:** 90%+ retrieval accuracy, near-zero hallucination, <5s simple response, 100% source citation coverage, 95%+ fallback accuracy.
- **Behavior rules (PRD §11):** Arabic-only output, refuse if not in PDF, cite section/page, multi-turn memory, synonym handling, KPI extraction, escalation matrix adherence.
- **MVP scope (PRD §15):** Arabic chat UI, RAG over PDF, source citation, fallback, chat history, admin upload, question logging, web interface.
- **Excluded from MVP:** RBAC, Teams integration, advanced analytics, multi-document, voice, mobile app, full automation.

### Tech stack decisions (locked in this turn)

- **Architecture:** Option A — Next.js + FastAPI + vector DB (PRD's primary recommendation).
- **Design system:** Full Cyrkil design system.
- **LLM:** DeepSeek API (specific model TBD during research).
- **Embeddings + vector store:** Open — to be researched in Phase 2.
- **Auth:** Email + password + email OTP.
- **MVP features:** Staff chat + admin upload + question logs dashboard.
- **Deployment:** Online cloud (Vercel etc.) but **portable** for on-prem / private cloud.

### Input constraints (from input files)

- **Cyrkil design system** forbids exposing internal provider names (n8n, webhooks, OAuth provider names, vector DB names, etc.) in user-visible copy. Apply the public-safe naming mapping in `DESIGN_SYSTEM.md §10`.
- **Public vs internal:** Per `DEVELOPMENT_REQUIREMENTS.md §5`, public users must not see provider names, webhooks, secrets, infra status, or admin controls.
- **Mobile policy:** Per `DEVELOPMENT_REQUIREMENTS.md §6`, mobile is chat/input-output only. No desktop sandbox/editor/terminal features.

---

## Locked decisions (from Phase 3 discussion)

### Repo & dev
- **Monorepo** (pnpm + uv). Apps: `apps/web` (Next.js), `apps/api` (FastAPI). Packages: `packages/ui`, `packages/tokens`.
- **Local dev:** Hybrid. DBs in Docker (Postgres, Redis, MinIO, MailHog), apps run locally with hot reload.
- **Config:** Env vars for secrets, `config.yaml` for non-secrets.

### RAG architecture
- **No vector DB. No embeddings.** Pre-built structure + ReAct agent with 5 tools.
- **Tools:** `list_sections()`, `get_section(id)`, `get_subsections(parent_id)`, `search_keyword(query)` (Postgres tsvector), `get_kpi_table(role)`, `get_escalation_path(topic)`.
- **LLM:** DeepSeek v4-flash (non-thinking) via OpenAI Python SDK.
- **Max retries:** 5 (configurable).

### Backend stack
- **Python:** FastAPI + SQLAlchemy 2.x async.
- **DB:** Postgres 16 (data + tsvector).
- **Jobs:** ARQ (Redis-based).
- **LLM client:** OpenAI Python SDK pointed at DeepSeek.
- **Storage:** S3-compatible (R2 / MinIO / AWS).
- **Email:** Resend (cloud) / Postfix (self-host) / MailHog (dev).
- **Logging:** structlog + JSON to stdout.

### Frontend stack
- **Next.js 15** App Router + TanStack Query v5 + native EventSource.
- **Font:** IBM Plex Sans Arabic.
- **Design:** Full Cyrkil design system (tokens, primitives, layering, surface taxonomy).
- **No vector DB:** the frontend never knows about embeddings.

### Auth
- **Email + password** (argon2id) + **email OTP on new device** (6 digits, 10 min, max 5 attempts).
- **Server-side sessions** in Postgres + httpOnly + Secure + SameSite=Lax cookie.
- **Invite-only registration** (admin sends invite link).

### Deployment
- **Cloud:** Vercel + Fly.io + Neon + R2 + Resend (all free tier).
- **Self-host:** Coolify + Docker Compose on single VPS.
- **One codebase**, env-var swap. No provider branches in code.

### Observability
- **Sentry** (cloud) or **GlitchTip** (self-host) — same SDK.

## Out-of-scope / explicit non-goals

- Voice input.
- Mobile native app.
- Multi-document KB.
- Microsoft Teams / WhatsApp channels.
- Role-based permissions beyond a single "admin" role for MVP.
- Modifying or interpreting Saudi labor law beyond what the PDF says.
- Legal or financial advice.
- Embedding-based vector search (we use a structured approach instead).
- LangChain / LlamaIndex (we hand-roll the pipeline).
- Cross-encoder reranking, HyDE, TreeRAG (deferred to v2 if needed).
