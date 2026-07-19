# Implementation Plan

**Project:** Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين)
**Status:** Phase 3 — Consolidated Plan (ready to execute)
**Last update:** 2026-07-10

---

## 1. Executive Summary

A KSA-company internal AI assistant that answers staff questions in **Arabic only**, grounded **exclusively** in a single PDF (the HR / organizational structure guide). The bot:

- Answers in Arabic with **inline citations** to source sections.
- **Refuses** with a standard message if the answer is not in the PDF.
- Supports **multi-turn** conversations.
- Handles **Arabic synonyms** (HSE ↔ السلامة, PMO ↔ إدارة المشاريع, etc.).
- Has an **admin surface** for uploading new PDF versions, testing, and viewing logs.
- Runs **identically** on Vercel + cloud services OR self-hosted (Coolify + Docker).

**Stack at a glance:**

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 App Router + TanStack Query v5 + native EventSource + IBM Plex Sans Arabic |
| Design | Full Cyrkil design system (tokens, primitives, layering, surface taxonomy) |
| Backend | FastAPI + SQLAlchemy 2.x async + ARQ (Redis) + S3-compatible storage |
| LLM | DeepSeek v4-flash (non-thinking) via OpenAI Python SDK |
| RAG | **No vector DB.** Pre-built structure (sections + KPI tables + escalation matrix + Postgres tsvector) + ReAct agent with 5 tools |
| Auth | Email + password (argon2id) + email OTP (6 digits, 10 min) + server-side session |
| Database | Postgres 16 (data + tsvector full-text) + Redis 7 (jobs + sessions) |
| Storage | S3-compatible (R2 / MinIO / AWS) |
| Email | Resend (cloud) / Postfix (self-host) / MailHog (dev) |
| Observability | Sentry (cloud) / GlitchTip (self-host) — same SDK |
| Deployment | Vercel + Fly.io + Neon (cloud) or Coolify + Docker Compose (self-host) |

---

## 2. Architecture Diagram

```
                          ┌────────────────────┐
                          │  Staff (browser)   │
                          └─────────┬──────────┘
                                    │ HTTPS
                                    ▼
                          ┌────────────────────┐
                          │  Next.js (Vercel / │
                          │  Docker)           │
                          │  Cyrkil UI         │
                          └─────────┬──────────┘
                                    │ HTTPS / SSE
                                    ▼
                          ┌────────────────────┐
                          │  FastAPI (Fly.io / │
                          │  Docker)           │
                          │  ReAct agent loop  │
                          └────┬────────┬──────┘
                               │        │
              ┌────────────────┘        └────────────────┐
              ▼                                          ▼
     ┌────────────────┐                        ┌────────────────┐
     │  DeepSeek API  │                        │  Postgres +    │
     │  (v4-flash)    │                        │  Redis         │
     └────────────────┘                        └────────────────┘
                                                        │
                                            ┌───────────┴───────────┐
                                            ▼                       ▼
                                    ┌─────────────┐         ┌─────────────┐
                                    │   S3 / R2   │         │  ARQ worker │
                                    │   (PDFs)    │         │  (reindex)  │
                                    └─────────────┘         └─────────────┘
```

---

## 3. Locked Tech Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repo | **Monorepo** (pnpm + uv) | Single source of truth, shared types, single CI |
| Local dev | **Hybrid** (DBs in Docker, apps local) | Best HMR + reproducible |
| Config | **Env vars for secrets, `config.yaml` for non-secrets** | Best of both: portable + tunable |
| LLM | **DeepSeek v4-flash (non-thinking)** | Cheap, competitive Arabic, OpenAI-compatible |
| Embeddings | **None — no vector DB** | Pre-built structure + ReAct tools |
| Retrieval | **ReAct agent with 5 tools** | Intelligent, self-aware retries, no cosine math |
| Vector store | **None** | Postgres tsvector for keyword search; sections table for navigation |
| Database | **Postgres 16** + **Redis 7** | Open source, portable, all features in one DB |
| ORM | **SQLAlchemy 2.x async** | Industry standard, async-native |
| LLM client | **OpenAI Python SDK pointed at DeepSeek** | Easiest, streaming + function calling |
| Background jobs | **ARQ (Redis-based)** | Survives restarts, async-native, retries |
| Logging | **structlog + JSON to stdout** | 12-factor, picks up in any aggregator |
| PDF parser | **pymupdf4llm + pdfplumber** | Best Arabic text + best table extraction |
| Chunking | **Section-aware** (each job role = 1 chunk) | PRD requirement |
| Frontend | **Next.js 15 + TanStack Query + native EventSource** | Modern, minimal deps |
| Font | **IBM Plex Sans Arabic** | Bilingual, corporate, professional |
| Auth | **Email + password (argon2) + email OTP on new device** | Best UX, medium security |
| Session | **Server-side in Postgres, httpOnly cookie** | Standard, portable |
| Email | **Resend (cloud) / Postfix (self-host) / MailHog (dev)** | Configurable via env |
| Storage | **S3-compatible (R2 / MinIO / AWS)** | Standard, portable |
| Error tracking | **Sentry (cloud) / GlitchTip (self-host)** | Same SDK |
| Deployment | **Vercel + Fly.io + Neon (cloud) / Coolify + Docker (self-host)** | One codebase, env vars swap |

---

## 4. The 7 Phases (detailed)

Each phase ends with a working, validated, committed checkpoint. No phase is "done" until validation passes.

### Phase 1 — PDF Pipeline (Sections + KPI Tables + Escalation)
**Goal:** Build the structure that the ReAct agent will navigate. The PDF is decomposed into a queryable, structured form.

**Tasks:**
1. **Project skeleton** — Monorepo with `apps/web`, `apps/api`, `packages/`. `pyproject.toml`, `pnpm-workspace.yaml`, `Dockerfile`, `docker-compose.yml` (Postgres + Redis + MinIO + MailHog + API + worker).
2. **Database schema** — All tables: `users`, `sessions`, `otps`, `documents`, `sections`, `kpi_tables`, `escalation_matrix`, `search_index`, `conversations`, `messages`, `logs`.
3. **PDF ingestion script** — `apps/api/app/services/ingestion.py`:
   - Open PDF with `pymupdf4llm` → markdown.
   - Clean up: strip repeated header, page numbers, TOC dots, ligature artifacts.
   - Detect sections via regex on numbered headings (`^(\d+(?:\.\d+){0,3})\s+[\u0600-\u06FF]`).
   - For each section: extract `section_id`, `parent_id`, `level`, `title_ar`, `full_text`, `page_start`, `page_end`.
   - For each section: also save to `search_index` for keyword search (tsvector auto-updated).
4. **KPI extraction** — `apps/api/app/services/kpi_extraction.py`:
   - Use `pdfplumber` to find tables.
   - Heuristic: KPI tables have a "اسم المؤشر" / "طريقة الحساب" / "الهدف" structure.
   - Save each KPI as a row in `kpi_tables` with `role_name_ar`, `kpi_name`, `calculation`, `target`, `page`.
5. **Escalation matrix extraction** — `apps/api/app/services/escalation_extraction.py`:
   - Find the section on "قاعدة التصعيد الإداري" (escalation rule).
   - Parse into structured rules: `topic`, `first_escalation`, `second_escalation`, `third_escalation`, `conditions`.
6. **Arabic normalization** — `apps/api/app/core/arabic.py`:
   - `normalize_arabic(text)` using `pyarabic`: NFC, strip tashkeel, strip tatweel, normalize alef / yeh / teh marbuta, collapse whitespace, keep Latin tokens.
   - `normalize_for_search(text)` — same as above.
7. **Manual test on the actual PDF** — Run the script on `uploads/hr_extracted/hr_source.pdf`. Verify: 15 top-level sections detected, ~50 sub-sections, all KPI tables captured, escalation matrix parsed.
8. **Admin can upload** (stub UI is fine) — `POST /admin/docs` accepts a PDF, stores in S3, triggers ingestion.

**Acceptance criteria:**
- ✅ Running `python -m app.services.ingestion --pdf hr_source.pdf --out /tmp/result.json` produces valid output.
- ✅ All 15 top-level sections present.
- ✅ KPI tables are structured, with `calculation` and `target` populated.
- ✅ Escalation matrix has at least 3 rules.
- ✅ Arabic text round-trips through normalization (no data loss).
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `apps/api/pyproject.toml` (new)
- `apps/api/app/services/ingestion.py` (new)
- `apps/api/app/services/kpi_extraction.py` (new)
- `apps/api/app/services/escalation_extraction.py` (new)
- `apps/api/app/core/arabic.py` (new)
- `apps/api/app/models/*.py` (new)
- `apps/api/migrations/versions/0001_initial.py` (new)
- `tests/test_ingestion.py` (new)
- `docker-compose.yml` (new)
- `.env.example` (new)

---

### Phase 2 — Backend Chat with ReAct Agent
**Goal:** A user can ask a question via `POST /chat/stream` and get a streaming Arabic answer with citations.

**Tasks:**
1. **DeepSeek client** — `apps/api/app/core/llm.py`:
   - OpenAI Python SDK pointed at `DEEPSEEK_BASE_URL`.
   - Helper: `llm.chat(messages, tools, stream=True)` → async iterator of events.
   - Helper: `llm.extract_tool_call(response)` → tool name + args.
2. **The 5 tools** — `apps/api/app/services/tools.py`:
   - `list_sections(parent_id=None)` → reads from `sections` table.
   - `get_section(section_id)` → reads full text from `sections`.
   - `get_subsections(parent_id)` → reads from `sections` where `parent_id=...`.
   - `search_keyword(query)` → Postgres tsvector query.
   - `get_kpi_table(role_name_ar)` → reads from `kpi_tables` filtered by role.
   - `get_escalation_path(topic)` → reads from `escalation_matrix`.
   - Each tool is a `@tool` decorated function with a docstring (the LLM uses the docstring to know when to call it).
3. **ReAct agent loop** — `apps/api/app/services/agent.py`:
   - `Agent.run(user_message, conversation_history) → AsyncIterator[Event]`.
   - The loop:
     1. Build messages: system prompt + history + user message.
     2. Send to LLM with `tools=...`.
     3. If LLM returns a tool call → call the tool, append result to messages, loop.
     4. If LLM returns a final answer → stream tokens, parse citations, yield `done` event.
     5. If `retries >= max_retries` → yield refusal event.
   - System prompt is the strict 9-rule prompt from the design discussion.
   - Retry counter is injected into the system prompt on each iteration: "You have N retries left."
4. **Chat service** — `apps/api/app/services/chat_service.py`:
   - `handle_chat(user, message, conversation_id) → AsyncIterator[Event]`.
   - Loads conversation history from DB.
   - Calls the agent.
   - Persists messages to DB.
   - Logs the question to `logs` table (per PRD §13).
5. **REST endpoints** — `apps/api/app/routers/chat.py`:
   - `POST /chat/stream` — SSE stream. Returns `text/event-stream` with events `{type: "token", data: "..."}`, `{type: "sources", data: [...]}`, `{type: "done", data: {...}}`.
   - `POST /chat` — non-streaming (for testing). Same logic, returns JSON.
6. **Tests** — `tests/test_agent.py`:
   - Mock DeepSeek responses.
   - Test each tool individually.
   - Test the agent loop with a simple Q&A.
   - Test refusal when no info found.
   - Test the retry counter.
7. **ARQ worker** — `apps/api/app/tasks/reindex.py`:
   - The actual reindex job that runs the ingestion pipeline on an uploaded PDF.
   - Updates `documents.status` as it progresses.

**Acceptance criteria:**
- ✅ `POST /chat` answers "ما هي مسؤوليات مسؤول الجودة؟" with the right text + `[المصدر: ...]`.
- ✅ `POST /chat` with an out-of-PDF question returns the standard refusal.
- ✅ Streaming works — tokens appear progressively.
- ✅ Citations are parsed and included.
- ✅ Retries work — model tries up to 5 times, then refuses.
- ✅ All 5 tools are callable and return correct data.
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `apps/api/app/core/llm.py` (new)
- `apps/api/app/services/tools.py` (new)
- `apps/api/app/services/agent.py` (new)
- `apps/api/app/services/chat_service.py` (new)
- `apps/api/app/routers/chat.py` (new)
- `apps/api/app/tasks/reindex.py` (new)
- `apps/api/app/core/prompts.py` (new)
- `tests/test_agent.py` (new)
- `tests/test_tools.py` (new)

---

### Phase 3 — Cyrkil Frontend + Arabic Chat UI
**Goal:** A staff user can open `/chat`, type a question in Arabic, see a streamed response with citations.

**Tasks:**
1. **Cyrkil design system extraction** — `packages/ui/`:
   - Tokens (colors, spacing, radii, type, motion) → `tailwind.config.ts` + `globals.css`.
   - Layer scale: `packages/ui/src/layers.ts` (Z.background=0, Z.canvas=10, ..., Z.dialog=50, Z.toast=200).
   - Primitives: `<Button>`, `<IconButton>`, `<Input>`, `<Field>`, `<Search>`, `<RowAction>`, `<Panel>`, `<SidePanel>`, `<Dialog>`, `<Tooltip>`, `<Kbd>`, `<SectionLabel>`, `<FileBadge>`.
   - All primitives use the Cyrkil tokens, no inline color literals.
2. **Arabic setup** — `apps/web/app/layout.tsx`:
   - `<html lang="ar" dir="rtl">`.
   - Load IBM Plex Sans Arabic via `next/font/google`.
   - Apply logical CSS properties throughout.
3. **Auth flow** — `apps/web/app/(auth)/`:
   - `/login` — email + password form.
   - `/register` — invite-only (admin sends an invite link with a token).
   - `/verify-otp` — 6-digit OTP entry.
4. **Chat surface** — `apps/web/app/(main)/chat/`:
   - `<ChatThread>` — scrollable panel with messages, hidden scrollbar.
   - `<Message>` — user or assistant variant, with citation chips.
   - `<Composer>` — textarea + send button, with abort on stream.
   - `<CitationChip>` — clickable, expands to show the full chunk.
5. **Streaming** — `apps/web/lib/useChatStream.ts`:
   - `useChatStream()` hook using native `EventSource` (or `fetch` with ReadableStream for POST).
   - Returns `{ messages, send, abort, status }`.
6. **TanStack Query setup** — `apps/web/app/providers.tsx`:
   - QueryClientProvider with `staleTime: 60_000`.
7. **i18n stub** — `apps/web/lib/i18n/useT.ts`:
   - Returns Arabic strings from a static dict.
   - All user-facing copy goes through `useT()` (per Cyrkil §7.5).

**Acceptance criteria:**
- ✅ Login works (email + password).
- ✅ Chat thread renders in Arabic with RTL.
- ✅ User types "ما هي مسؤوليات مسؤول الجودة؟" → answer streams in with citation.
- ✅ Citation chip is clickable and shows the source.
- ✅ Composer aborts a stream cleanly.
- ✅ Mobile responsive (chat works on phone).
- ✅ All Cyrkil primitives used (no inline styles).
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `packages/ui/src/**` (new)
- `packages/tokens/src/**` (new)
- `apps/web/app/layout.tsx` (new)
- `apps/web/app/(auth)/login/page.tsx` (new)
- `apps/web/app/(main)/chat/page.tsx` (new)
- `apps/web/components/chat/*` (new)
- `apps/web/lib/useChatStream.ts` (new)
- `apps/web/lib/i18n/useT.ts` (new)

---

### Phase 4 — Admin Upload + Document Version Management
**Goal:** Admin can upload a new PDF, see it parsed, test questions against it, then promote it to active.

**Tasks:**
1. **Admin endpoints** — `apps/api/app/routers/admin_docs.py`:
   - `POST /admin/docs` — upload PDF (multipart). Stores in S3. Creates `documents` row. Triggers ARQ reindex job.
   - `GET /admin/docs` — list all documents.
   - `GET /admin/docs/{id}` — get one document with status.
   - `POST /admin/docs/{id}/reindex` — re-run ingestion.
   - `POST /admin/docs/{id}/activate` — promote to active (demotes old active).
   - `POST /admin/docs/{id}/disable` — disable.
   - `POST /admin/docs/{id}/test` — test question against this specific doc (bypasses active).
2. **Document audit log** — `documents_audit_log` table. Every action logged.
3. **Admin UI** — `apps/web/app/(main)/admin/documents/`:
   - Document list (name, version, status, uploaded_at, last_indexed_at).
   - Upload zone (drag-drop).
   - Per-document actions: Re-index, Make Active, Disable, Test.
   - Test mode UI: a chat surface with "Testing against: doc v1.0 (draft)" banner.
4. **Invite users** — `apps/api/app/routers/admin_users.py`:
   - `POST /admin/users/invite` — admin sends invite (email + temporary token).
   - User clicks link, sets password, verifies OTP.
5. **Bootstrap admin** — first-run script (`scripts/seed_admin.py`):
   - If no admin exists, create one from `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` env vars.

**Acceptance criteria:**
- ✅ Admin can upload a PDF, see it appear as `processing` → `draft`.
- ✅ Re-index button rebuilds the index.
- ✅ "Make Active" promotes the draft and demotes the old.
- ✅ Test mode lets admin run questions against a non-active doc.
- ✅ Audit log records every action.
- ✅ Admin can invite a new user (invite email sent).
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `apps/api/app/routers/admin_docs.py` (new)
- `apps/api/app/routers/admin_users.py` (new)
- `apps/api/app/services/admin_service.py` (new)
- `apps/web/app/(main)/admin/documents/page.tsx` (new)
- `apps/web/components/admin/*` (new)

---

### Phase 5 — Authentication (Email + Password + Email OTP)
**Goal:** Production-grade auth with sessions, password reset, and device tracking.

**Tasks:**
1. **Auth endpoints** — `apps/api/app/routers/auth.py`:
   - `POST /auth/register` — invite token + password + name.
   - `POST /auth/login` — email + password. Returns session.
   - `POST /auth/otp/request` — request OTP (for new device).
   - `POST /auth/otp/verify` — verify OTP.
   - `POST /auth/logout` — delete session.
   - `POST /auth/password/reset/request` — request password reset OTP.
   - `POST /auth/password/reset/confirm` — set new password.
2. **Session management** — `apps/api/app/core/security.py`:
   - `create_session(user, device_info) → session_id`.
   - `get_session(session_id) → User | None`.
   - `delete_session(session_id)`.
   - Session expiry: 7 days, sliding renewal on each authenticated request.
   - Device fingerprint: simple hash of `user_agent + accept_language`.
3. **OTP management** — `apps/api/app/services/otp_service.py`:
   - `generate_otp() → 6-digit code`.
   - `send_otp(user, code, via='email')`.
   - `verify_otp(user, code) → bool`.
   - Hash the code with argon2 before storing.
   - Rate limits: 3 OTPs per email per hour, 5 attempts per OTP.
4. **Email service** — `apps/api/app/core/email.py`:
   - Interface: `EmailService.send(to, subject, body)`.
   - 3 implementations: `ResendEmailService`, `SMTPEmailService`, `ConsoleEmailService`.
   - Selected at startup based on `EMAIL_PROVIDER` env var.
5. **Frontend auth pages** — `apps/web/app/(auth)/`:
   - Login, register (with invite token), OTP entry, password reset.

**Acceptance criteria:**
- ✅ User can register via invite link.
- ✅ User can log in with email + password.
- ✅ OTP is required on first login from a new device.
- ✅ Logout invalidates the session.
- ✅ Password reset works (OTP via email).
- ✅ All security headers set (CSP, X-Content-Type-Options, etc.).
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `apps/api/app/routers/auth.py` (new)
- `apps/api/app/core/security.py` (new)
- `apps/api/app/services/otp_service.py` (new)
- `apps/api/app/core/email.py` (new)
- `apps/web/app/(auth)/**` (new)

---

### Phase 6 — Question Logs Dashboard
**Goal:** Admin can see what staff are asking, what's working, what's not.

**Tasks:**
1. **Logs API** — `apps/api/app/routers/admin_logs.py`:
   - `GET /admin/logs` — paginated, filterable by date / user / answered / confidence.
   - `GET /admin/logs/top` — top asked questions.
   - `GET /admin/logs/failed` — questions where the bot refused or low confidence.
   - `GET /admin/logs/{id}` — full log entry with retrieved sections.
2. **Logging instrumentation** — `apps/api/app/services/chat_service.py`:
   - Every chat request logs: user_id, question, answer, retrieved_sections, confidence_score, answered (bool), timestamp, latency_ms, tokens_used.
3. **Logs UI** — `apps/web/app/(main)/admin/logs/`:
   - Table view: time, user, question (truncated), confidence, status, retrieved sections.
   - Filters: date range, answered/not, confidence threshold.
   - Detail view: full question, full answer, retrieved sections, latency, tokens.
   - "Top asked" panel: most frequent questions.
   - "Failed" panel: low confidence / refusals.

**Acceptance criteria:**
- ✅ Every chat request is logged.
- ✅ Admin can filter and search logs.
- ✅ Admin can see the top asked questions.
- ✅ Admin can see failed questions.
- ✅ Charts work (top questions, daily volume).
- ✅ Lint + typecheck + tests pass.
- ✅ Checkpoint archive created.

**Files changed:**
- `apps/api/app/routers/admin_logs.py` (new)
- `apps/api/app/models/log.py` (new)
- `apps/web/app/(main)/admin/logs/page.tsx` (new)

---

### Phase 7 — Deployment + Production Hardening
**Goal:** Production-ready. Runs on Vercel + cloud, or self-hosted. Secure. Observable.

**Tasks:**
1. **CI/CD** — `.github/workflows/`:
   - `lint.yml` — runs lint, typecheck, tests on every PR.
   - `deploy-cloud.yml` — on merge to main, deploys to Vercel + Fly.io.
   - `deploy-selfhost.yml` — builds and pushes Docker images to GHCR.
2. **Deployment configs**:
   - `vercel.json` — Next.js config.
   - `fly.toml` — FastAPI on Fly.io.
   - `infra/coolify/` — Coolify compose file for self-host.
3. **Observability**:
   - Sentry SDK on backend (`sentry-sdk[fastapi]`) and frontend (`@sentry/nextjs`).
   - `/healthz` and `/readyz` endpoints.
   - Structured JSON logs to stdout.
4. **Security hardening**:
   - CSP, HSTS, X-Content-Type-Options headers.
   - Rate limiting (slowapi) on auth endpoints (5/min) and chat (30/min per user).
   - CSRF protection on state-changing endpoints.
   - Secrets via env vars, never in code.
5. **PDPL compliance**:
   - `GET /me/data` — export all user data as JSON.
   - `DELETE /me/data` — soft-delete (30-day grace).
   - Privacy notice shown on first login (in Arabic).
   - Breach notification procedure documented in SUPPORTING_NOTES.md.
6. **Eval harness** — `apps/api/tests/eval/`:
   - Golden question set (50-100 staff-style questions, marked "in-PDF" or "out-of-PDF").
   - `run_eval.py` script that runs the agent over the golden set and reports:
     - Answer rate (did it answer instead of refuse, when expected).
     - Refusal accuracy (did it refuse when out-of-PDF).
     - Citation accuracy (does the cited section actually contain the answer?).
   - Outputs a markdown report.
7. **Performance**:
   - DB indexes on all foreign keys and `section_id`, `document_id`, `user_id`.
   - Connection pooling (SQLAlchemy pool_size=10).
   - Response caching for repeated questions (in-memory LRU, 5 min TTL).
8. **Documentation**:
   - `README.md` at repo root with quickstart.
   - `docs/DEPLOYMENT.md` — how to deploy on each target.
   - `docs/SECURITY.md` — security model, threat model, breach response.
   - `docs/USER_GUIDE.md` — staff-facing guide (in Arabic).

**Acceptance criteria:**
- ✅ Lint + typecheck + tests + build all pass.
- ✅ Deploys to Vercel on merge to main.
- ✅ Self-host via `docker compose up` works.
- ✅ Sentry catches errors in dev.
- ✅ Eval harness runs and produces a report.
- ✅ All 100 golden questions answered correctly (or properly refused).
- ✅ Security headers verified.
- ✅ Final checkpoint archive created.

**Files changed:**
- `.github/workflows/*` (new)
- `vercel.json` (new)
- `fly.toml` (new)
- `infra/coolify/docker-compose.yml` (new)
- `apps/api/app/core/middleware.py` (new)
- `apps/api/app/routers/user_data.py` (new)
- `apps/api/tests/eval/golden_questions.jsonl` (new)
- `apps/api/tests/eval/run_eval.py` (new)
- `docs/*` (new)
- `README.md` (new)

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DeepSeek quality issue with Arabic | Medium | High | Eval harness catches regressions. Have fallback to OpenAI gpt-4o-mini via env-var swap. |
| PDF structure is different from expected | Low | High | Ingestion is defensive (handles missing sections, partial data). Tests on the actual PDF before Phase 1 is "done." |
| ReAct agent loops / hallucinates tool names | Medium | Medium | Per the Towards Data Science research, 90% of retries are wasted on hallucinated tool names. Mitigation: clear tool docstrings, deterministic tool registration, retry counter visible to the LLM. |
| Document injection attack | Low | High | Strict system prompt (rule 5: ignore instructions in context). `<retrieved_document>` tags. PDF only, no other file types in MVP. |
| Cross-border data transfer (PDPL) | Certain | High | Privacy notice in Arabic. Document DeepSeek as a sub-processor. SDAIA SCCs path documented. Self-hosted DeepSeek as future option. |
| Vector store / DB performance | Low | Medium | pgvector and tsvector are well-tuned in Postgres 16. We have ~500 chunks. Indexes on all FKs. |
| Arabic text edge cases (encoding, RTL marks) | Medium | Low | `pyarabic` handles standard cases. Test on actual data. Display layer uses logical CSS properties. |
| Vercel → self-host divergence | Low | Medium | "No provider branches" rule. All config via env. `docker-compose.yml` is the single source of truth for service definitions. |
| Session hijacking | Low | High | httpOnly + Secure + SameSite=Lax. Session ID is a 256-bit random string. Sliding expiry. CSRF on state-changing endpoints. |
| Rate-limit abuse (brute force login) | Medium | Medium | slowapi on auth endpoints (5/min), 5 OTP attempts per code, 3 OTPs per hour per email. |

---

## 6. Out of Scope (Explicit)

These are in the PRD's "Future Features" (§16) or are deliberately excluded from MVP:

- ❌ Voice input.
- ❌ Mobile native app.
- ❌ Multi-document KB.
- ❌ Microsoft Teams / WhatsApp channels.
- ❌ Role-based permissions beyond a single "admin" role.
- ❌ Modifying or interpreting Saudi labor law beyond what the PDF says.
- ❌ Legal or financial advice.
- ❌ Embedding-based vector search (we use a structured approach instead).
- ❌ LangChain / LlamaIndex (we hand-roll the pipeline).
- ❌ Cross-encoder reranking (deferred to v2).
- ❌ HyDE (deferred to v2 if needed).
- ❌ TreeRAG / hierarchical graph retrieval (deferred to v2 if needed).

---

## 7. Validation Commands

Every phase must pass these before being marked done:

```bash
# Backend
cd apps/api
uv run ruff check .          # Lint
uv run ruff format .         # Format check
uv run mypy .                # Typecheck
uv run pytest                # Tests
uv run python -m app.main    # App boots

# Frontend
cd apps/web
pnpm lint                    # Lint
pnpm typecheck               # TypeScript
pnpm test                    # Tests
pnpm build                   # Production build

# Both
docker compose -f docker-compose.yml config    # Compose is valid
python -m app.services.ingestion --pdf test.pdf  # Ingestion script works
```

---

## 8. Checkpoint Naming

After each phase:
```bash
project_phase_01_pdf_pipeline.zip
project_phase_02_chat_agent.zip
project_phase_03_cyrkil_frontend.zip
project_phase_04_admin_upload.zip
project_phase_05_auth.zip
project_phase_06_logs.zip
project_phase_07_deployment.zip
project_complete_checkpoint.zip    # after all phases
```

Excluded from zip: `node_modules`, `.venv`, `.git`, `dist`, `build`, `coverage`, `__pycache__`, `.cache`, `.next`, `.turbo`.

---

## 9. Next Step

Phase 1 starts immediately. The first commit will be the monorepo skeleton + docker-compose + the ingestion script running on the actual PDF.
