# Supporting Notes

**Project:** Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين)
**Status:** Phase 3 — Consolidated Plan
**Last update:** 2026-07-10

This file collects special notes that don't fit cleanly into the plan.

---

## 1. Public-Safe Naming (per Cyrkil DESIGN_SYSTEM §10 + DEVELOPMENT_REQUIREMENTS §5)

The user-facing UI must NEVER expose these internal names:

| Internal | Public label |
|---|---|
| DeepSeek / LLM API | (not exposed — appears as "the AI assistant" generically) |
| OpenAI Python SDK | (not exposed — it's just a library) |
| pgvector / Postgres | (not exposed — just "the database") |
| Redis | (not exposed — internal) |
| S3 / R2 / MinIO | "document storage" |
| Sentry / GlitchTip | (not exposed — internal observability) |
| Vercel / Fly.io / Coolify | (not exposed — just "the deployment") |
| Docker / docker-compose | (not exposed — internal) |
| ARQ | (not exposed) |
| Next.js / React | (not exposed) |
| FastAPI | (not exposed) |

**In practice:** the user only sees the chat interface, the login page, the admin pages (if they're admin), and the privacy notice. None of these pages need to mention any of the above.

The README and developer docs CAN mention these — those are for developers, not end users.

---

## 2. GUI Requirements (Arabic + Cyrkil)

### 2.1 Font loading
```ts
// apps/web/app/layout.tsx
import { IBM_Plex_Sans_Arabic } from "next/font/google";

const ibmPlex = IBM_Plex_Sans_Arabic({
  subsets: ["arabic", "latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-arabic",
});
```

### 2.2 Tailwind config (Cyrkil tokens)
All Cyrkil design tokens are loaded as CSS variables in `globals.css` and exposed via Tailwind v4's `@theme inline`. The Cyrkil color tokens, spacing scale, radii, control heights, type scale, motion easings, and z-index layers are all set up.

### 2.3 RTL setup
- `<html lang="ar" dir="rtl">` in `apps/web/app/layout.tsx`.
- All paddings/margins use Tailwind's logical utilities (`ms-2`, `me-2`, `ps-4`, `pe-4`).
- Icons that have direction (arrows, chevrons) are mirrored with `rtl:scale-x-[-1]` or `rtl:rotate-180` (Lucide handles some, others we wrap).
- Numbers in Western Arabic (0-9) by default. Currency, dates, etc. follow user locale.
- Form labels are ABOVE inputs (per Arabic conventions).

### 2.4 Cyrkil primitives to build
We extract these from the Cyrkil design system and put them in `packages/ui/src/primitives/`:

- `<Button>` — 3 sizes (sm/md/lg), 5 variants (primary/secondary/ghost/danger/link).
- `<IconButton>` — 3 sizes, `aria-label` required.
- `<Input>` — themed.
- `<Field>` — label + input + error.
- `<Search>` — universal search box (used in sidebar).
- `<RowAction>` — inline X/⋯ on a row.
- `<Panel>` — scrollable container.
- `<SidePanel>` — sidebar panel (header + primary action + search + scrollable body + footer).
- `<Dialog>` — modal (only for command palette, NOT for normal flow per Cyrkil §1.3).
- `<Tooltip>` — wraps `<TooltipProvider>` once at root.
- `<Kbd>` — keyboard shortcut chip.
- `<SectionLabel>` — mini-uppercase section header.
- `<FileBadge>` — file extension badge.
- `<Skeleton>`, `<SkeletonChatMessage>` — loading states.
- `<Toaster>` — transient notifications.

### 2.5 Layering
Every elevated element imports `Z` from `@cyrkil/ui/layers`:
```ts
// packages/ui/src/layers.ts
export const Z = {
  background: 0,
  canvas: 10,
  rail: 20,
  header: 30,
  overlay: 40,
  dialog: 50,
  drawer: 70,
  toast: 200,
} as const;
```

NEVER use `z-50` or `z-[200]` in component code.

### 2.6 Surface taxonomy (Cyrkil §1.3)
- **Tabs** (not modals) for: Settings, Profile, file previews.
- **Anchored popovers** for: rename, file context menu, conversation context menu.
- **Inline** for: tab close X, attach chip remove, dirty dot, toaster.

`<Dialog>` is RESERVED for: the command palette (if we add one), and rare blocking confirmations (delete confirm, sign-out confirm).

### 2.7 Forbidden patterns
- ❌ `transform: translate(...)` for layout positioning.
- ❌ `position: absolute` for inline siblings.
- ❌ `window.confirm`, `window.alert`, `window.prompt`.
- ❌ `getComputedStyle()` to read theme values for non-DOM consumers.
- ❌ Mocked controls (buttons without `onClick`).
- ❌ Random `z-50` / `z-[200]`.
- ❌ Inline color literals (`#fff`, `rgb()`).

---

## 3. Deployment Notes

### 3.1 Cloud path (Vercel + Fly.io + Neon + Resend + R2)

| Service | Provider | Free tier |
|---|---|---|
| Frontend (Next.js) | Vercel | 100 GB bandwidth, unlimited sites |
| Backend (FastAPI) | Fly.io | 3 shared VMs, 3 GB persistent storage |
| Database (Postgres) | Neon | 0.5 GB, 191 project-hours |
| Cache + Jobs (Redis) | Upstash | 10K commands/day |
| Object storage (PDFs) | Cloudflare R2 | 10 GB, free egress |
| Email (OTP) | Resend | 3K emails/month |
| Error tracking | Sentry | 5K events/month |

Total monthly cost: **$0** for MVP scale (a few hundred users).

### 3.2 Self-host path (Coolify + Docker Compose on single VPS)

Recommended VPS: Hetzner CX22 (€4.5/month) or DigitalOcean basic droplet ($6/month). 2 vCPU, 4 GB RAM is plenty for our scale.

Services running on the VPS:
- Coolify (UI for managing deployments)
- Postgres 16
- Redis 7
- MinIO (S3-compatible)
- FastAPI (Docker)
- Next.js standalone (Docker)
- ARQ worker (Docker)
- GlitchTip (optional, for self-hosted error tracking)
- Postfix (optional, for self-hosted email)
- Caddy (TLS reverse proxy, automatic Let's Encrypt)

### 3.3 Local dev (Docker Compose)

Same docker-compose as self-host, but:
- Use MailHog instead of Postfix (catches emails locally).
- Use MinIO console (port 9001) for inspecting uploaded PDFs.
- Use a Postgres admin UI (e.g., Adminer on port 8080).
- Hot reload: apps run locally (`uvicorn --reload` for API, `pnpm dev` for web), DBs in Docker.

### 3.4 First-run procedure

1. Clone the repo.
2. Copy `.env.example` to `.env`. Fill in:
   - `DEEPSEEK_API_KEY` (required).
   - `SESSION_SECRET` (generate: `openssl rand -hex 32`).
   - `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` (for the first admin).
3. Run `docker compose up -d` (or `make dev`).
4. The API will auto-create the first admin from the bootstrap env vars on first boot.
5. Log in as that admin, invite other users.

### 3.5 Migration between paths

Migrating from cloud to self-host (or vice versa):
1. Dump the database: `pg_dump $DATABASE_URL > dump.sql`.
2. Copy the S3 bucket: `rclone sync` (for R2 / S3 / MinIO).
3. Update DNS.
4. Start the new deployment with the same `DATABASE_URL`, `S3_*`, `REDIS_URL` env vars.
5. Done. No code changes.

---

## 4. Security Checklist

### 4.1 Backend
- [ ] All endpoints require auth (except `/auth/*`, `/healthz`, `/readyz`).
- [ ] Passwords hashed with argon2id (parameters: `time_cost=3, memory_cost=65536, parallelism=4`).
- [ ] OTPs hashed with argon2id.
- [ ] Session IDs are 256-bit random strings (`secrets.token_urlsafe(32)`).
- [ ] Sessions stored server-side, expire in 7 days, slide on use.
- [ ] httpOnly + Secure + SameSite=Lax cookies.
- [ ] CSRF protection on all state-changing endpoints (double-submit cookie or `seasurf` for FastAPI).
- [ ] Rate limiting on `/auth/login` (5/min), `/auth/otp/*` (3/hour per email, 5 attempts per code).
- [ ] SQLAlchemy parameterized queries (no string concatenation for SQL).
- [ ] User input is Pydantic-validated, never trusted.
- [ ] File upload validates MIME type and size.
- [ ] Logs are structured, no PII unless necessary.

### 4.2 Frontend
- [ ] CSP header set (no inline scripts except where needed; strict-src 'self').
- [ ] HSTS header set (max-age=31536000; includeSubDomains).
- [ ] X-Content-Type-Options: nosniff.
- [ ] Referrer-Policy: strict-origin-when-cross-origin.
- [ ] All forms use POST with CSRF token.
- [ ] Session cookie is httpOnly (set by backend, not accessible from JS).
- [ ] All user-facing strings go through `useT()` (per Cyrkil §7.5).
- [ ] No inline event handlers in HTML (Next.js handles this naturally).
- [ ] No `dangerouslySetInnerHTML` unless content is sanitized.

### 4.3 Document-injection mitigation (CRITICAL)
- [ ] System prompt explicitly forbids following instructions from retrieved content.
- [ ] Retrieved chunks are wrapped in `<retrieved_document source="..." role="data_only">` tags.
- [ ] Admin uploads are logged with user_id, timestamp, file hash.
- [ ] The PDF is the only allowed file type (MVP). No other formats.
- [ ] Bot refuses to act on any instruction that appears in the document.

### 4.4 Infrastructure
- [ ] TLS everywhere (Let's Encrypt via Coolify, or Vercel/Fly.io built-in).
- [ ] Database backups (Neon automatic; self-host: nightly `pg_dump` to S3).
- [ ] Secrets only in env vars, never in code or git.
- [ ] SSH access to VPS via key only (no password).
- [ ] Firewall: only ports 80, 443 open to public.

---

## 5. Mobile Policy

Per `DEVELOPMENT_REQUIREMENTS §6` and Cyrkil DS:

- **Mobile is chat-only.** No admin features on mobile.
- Mobile chat UI is the same `<ChatThread>` + `<Composer>` as desktop, with:
  - Larger tap targets (min 44x44).
  - `paddingBottom: env(safe-area-inset-bottom)` for iOS.
  - Keyboard-aware layout (composer stays above the keyboard).
- Admin pages are desktop-only. If opened on mobile, show "Please use a desktop browser for this section."

---

## 6. Testing Checklist

### 6.1 Unit tests
- [ ] PDF ingestion produces correct sections, KPIs, escalation matrix.
- [ ] Arabic normalization is idempotent.
- [ ] OTP generation, hashing, verification, expiry.
- [ ] Session creation, validation, expiry.
- [ ] Each tool function returns correct data.
- [ ] Agent loop respects retry counter.
- [ ] Agent refuses with the standard message when no info found.

### 6.2 Integration tests
- [ ] Full chat flow: question → agent → LLM → tools → answer.
- [ ] Full admin flow: upload PDF → reindex → test → activate.
- [ ] Auth flow: invite → register → verify → login → logout.

### 6.3 End-to-end tests (Playwright)
- [ ] Staff user logs in, asks a question, gets an answer with citation.
- [ ] Staff user asks an out-of-PDF question, gets refusal.
- [ ] Admin uploads a PDF, sees it in the list, tests it, activates it.
- [ ] Admin views logs, filters, exports.

### 6.4 Arabic eval harness
- [ ] 50-100 golden questions covering all major topics.
- [ ] Each marked "in-PDF" or "out-of-PDF" with expected behavior.
- [ ] Run via `python -m tests.eval.run_eval` after each phase.
- [ ] Output markdown report with: answer rate, refusal accuracy, citation accuracy.

### 6.5 Performance tests
- [ ] Chat latency p95 < 5s (simple), < 10s (complex).
- [ ] Admin upload + reindex < 60s for 5MB PDF.
- [ ] DB queries < 100ms p95.
- [ ] SSE first byte < 2s.

### 6.6 Security tests
- [ ] SQL injection attempts rejected.
- [ ] XSS attempts sanitized.
- [ ] CSRF protection on state-changing endpoints.
- [ ] Rate limiting enforced.
- [ ] Auth required on protected endpoints.

---

## 7. External Service Acceptance Criteria

Before going live, verify each external service is properly configured:

| Service | Acceptance |
|---|---|
| DeepSeek API | API key works. `deepseek-v4-flash` model available. Streaming works. Function calling works. |
| Postgres | Database created. Migrations applied. Indexes in place. |
| Redis | Reachable. ARQ worker can enqueue jobs. |
| S3 / R2 / MinIO | Bucket created. Access keys work. Upload + download tested. |
| Email (Resend / SMTP) | Test email sent successfully. From address verified. SPF/DKIM in place. |
| Sentry / GlitchTip | DSN works. Test event captured. |
| Vercel | Build succeeds. Custom domain (if any) configured. Env vars set. |
| Fly.io | App deployed. Health check passes. Env vars set. |

---

## 8. PDPL Compliance Notes (KSA)

### 8.1 What counts as personal data
- Email + password hash.
- Session metadata (IP, user agent — minimal, hashed if possible).
- Chat history (questions, answers, timestamps).
- Admin logs (same).

### 8.2 What does NOT count as personal data
- The PDF content (it's a company policy, not personal data of any individual).

### 8.3 Lawful basis
- The company's legitimate interest in providing internal services to its staff.
- Contractual necessity (the chatbot is part of the employment relationship).
- Document this in the privacy notice.

### 8.4 Data subject rights
Implement these endpoints:
- `GET /me/data` — export all user data as JSON.
- `DELETE /me/data` — soft-delete (30-day grace), then hard-delete.

### 8.5 Cross-border transfer
- DeepSeek is a sub-processor. Document this in the privacy notice.
- For full KSA-residency, self-host DeepSeek-V3 (deferred to v2).
- SDAIA SCCs (Standard Contractual Clauses) required for transfers.

### 8.6 Breach notification
- 72-hour window from breach awareness to SDAIA notification.
- Documented procedure in this file:
  1. Contain the breach.
  2. Notify the DPO (admin email).
  3. Assess scope and impact.
  4. Notify SDAIA within 72 hours.
  5. Notify affected users if high risk.

### 8.7 DPO contact
- Configured via `DPO_EMAIL` env var.
- Shown in the privacy notice.

### 8.8 Data retention
- Active conversations: kept until user deletes them.
- Admin logs: 1 year max, then auto-purged (configurable in `config.yaml`).
- Soft-deleted user data: 30-day grace, then hard-deleted.

---

## 9. Operational Runbooks

### 9.1 How to onboard a new admin
1. Admin visits `/admin/users`.
2. Clicks "Invite Admin".
3. Enters the new admin's email.
4. System sends an invite email with a one-time link.
5. New admin clicks the link, sets a password.
6. New admin can now log in.

### 9.2 How to upload a new PDF version
1. Admin visits `/admin/documents`.
2. Drags the new PDF into the upload zone.
3. System stores the PDF, starts ingestion in the background.
4. Admin sees the new document in the list with status `processing` → `draft`.
5. Admin clicks "Test" to run questions against the draft (test mode).
6. If satisfied, admin clicks "Make Active".
7. Old active document becomes `disabled`. New one becomes `active`.
8. All future chat queries use the new document.

### 9.3 How to roll back to a previous PDF
1. Admin visits `/admin/documents`.
2. Finds the previous version in the list (status `disabled`).
3. Clicks "Make Active" on it.
4. Current active becomes `disabled`. Previous becomes `active`.
5. All future chat queries use the rolled-back document.

### 9.4 How to investigate a "the bot got it wrong" report
1. Admin goes to `/admin/logs`.
2. Searches for the question.
3. Clicks the log entry.
4. Sees: full question, full answer, retrieved sections, confidence, latency.
5. If the issue is in the document, admin updates the PDF (new version).
6. If the issue is in the agent, dev fixes it (e.g., better tool, different prompt).

### 9.5 How to handle a security incident
1. Detect (Sentry alert, user report, anomaly).
2. Contain (disable affected accounts, rotate secrets).
3. Investigate (logs, Sentry events, DB queries).
4. Notify (SDAIA within 72h, affected users).
5. Post-mortem (what went wrong, how to prevent).

---

## 10. Glossary

| Term | Meaning |
|---|---|
| **ReAct** | Reasoning + Acting. An LLM agent pattern where the model alternates between thinking and calling tools. |
| **RAG** | Retrieval-Augmented Generation. The LLM is given retrieved context to ground its answers. |
| **Reranking** | A second pass that re-scores retrieved chunks with a stronger model. (We don't use this in MVP.) |
| **HyDE** | Hypothetical Document Embeddings. Generate a fake answer, embed it, retrieve. (We don't use this.) |
| **TSVector** | Postgres full-text search type. The `ts_rank_cd` function is BM25-flavored. |
| **pgvector** | Postgres extension for vector similarity search. (We don't use this — no embeddings.) |
| **ARQ** | Async job queue for Python, backed by Redis. |
| **Cyrkil** | The design system we're following. See DESIGN_SYSTEM.md. |
| **SDAIA** | Saudi Data and AI Authority. PDPL regulator. |
| **PDPL** | Personal Data Protection Law (KSA, Royal Decree M/19, in force since 14 Sept 2024). |
| **KPI** | Key Performance Indicator. The bot needs to extract these from the PDF. |
| **PMO** | Project Management Office. |
| **QHSE** | Quality, Health, Safety, Environment. |
| **HSE** | Health, Safety, Environment (subset of QHSE). |
| **JSA** | Job Safety Analysis. (Not in our PDF, but common in HR docs.) |
