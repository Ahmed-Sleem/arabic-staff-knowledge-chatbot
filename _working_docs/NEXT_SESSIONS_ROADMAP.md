# Next Sessions Roadmap

**Read on every session start after `AGENT_RULES.md`, `AUDIT_AND_TODO.md`, `IMPLEMENTATION_LOG.md`, and recent `CHANGELOG.md`.**

---

## Current GPR Architecture — 2026-07-22

### Product

GPR is a no-login, device-based grounded knowledge workspace for the Sample Organization / GPR organizational manual.

### Backend

- FastAPI + Async SQLAlchemy.
- SQLite by default, optional PostgreSQL via `DATABASE_URL`.
- Active routers:
  - `/api/v1/vault` — encrypted device API-key vault.
  - `/api/v1/chat` — SSE streaming chat.
  - `/api/v1/documents` — document/graph APIs; upload remains API-supported and must use vault profile keys for LLM-assisted ingestion.
- API-key model:
  - raw keys are encrypted server-side with AES-256-GCM.
  - master key: `GPR_VAULT_MASTER_KEY`.
  - device identity: HttpOnly `gpr_device_secret` cookie.
  - chat uses `X-LLM-Profile-ID`, not raw key headers.
- Streaming:
  - backend emits typed SSE events including provider deltas.
  - Gemini uses native streaming.
  - OpenAI-compatible providers use SDK streaming.

### Frontend

- Next.js 15 App Router.
- Active components:
  - `SettingsModal.tsx` — vault profile manager.
  - `ChatPanel.tsx` — chat stream UI and composer.
  - `ObsidianGraphView.tsx` — map viewer.
  - `CitationDrawer.tsx` — enriched node inspector.
  - `LeftPanel.tsx` — conversation list/search/actions.
- Removed obsolete raw-key `ApiKeyModal.tsx`.
- Conversations remain browser-local per `gpr_device_id`.
- API keys do not remain in browser localStorage after successful migration.

### Data

Active source JSON:

```text
uploads/deepseek_json_20260722_6a33e9.json
```

Built production graph:

```text
src/backend/data/curated_knowledge_graph.json
```

The enriched schema includes bilingual content, aliases, keywords, typed relations, role profiles, KPIs, approval/confidence metadata, and answerable/not-answerable boundaries.

---

## Active branch and workflow

Current feature branch:

```text
feat/gpr-vault-streaming-ui-polish-20260722
```

Workflow:

1. Continue closing `GAP-GPR-41` through `GAP-GPR-50` one by one.
2. Validate each gap before moving to the next.
3. Commit and push each completed gap to the feature branch.
4. Do **not** merge to `main` until Ahmed approves the final branch.

---

## Remaining high-level work after the latest closed gaps

- Final docs/deployment/repo hygiene if not already closed.
- Final full validation and manual UI acceptance matrix.
- Confirm with Ahmed before merge to `main`.

---

## Acceptance URLs after main merge/deploy

If/when merged to main and deployed, acceptance should be performed on the live GPR URL configured by Ahmed/Railway, plus any local Docker check if needed.
