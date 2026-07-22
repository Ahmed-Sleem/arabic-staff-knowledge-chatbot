# Topic 9 — Admin Upload & Document Version Management

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Upload flow**:
   - Admin uploads PDF → stored in object storage → background job extracts chunks → candidate index built.
2. **Versioning model**:
   - Each upload is a new `Document` row with `version`, `status` (`draft` / `active` / `disabled`).
   - Only one `active` document at a time; old ones become `disabled`.
   - Logs reference the document version that was active at the time of the question.
3. **Test-mode sandbox**:
   - Admin can run questions against a `draft` document *before* promoting it to `active`.
   - Per PRD §7.10: "Test questions before publishing".
4. **Re-index trigger**:
   - Manual button (admin clicks "re-index").
   - Auto-triggered on upload.
5. **Diff / rollback**:
   - Easy rollback to a previous version by changing the `active` flag.
6. **Storage**:
   - Raw PDF in object storage.
   - Chunk artifacts: serializable JSON in DB or file system, or just rebuild on demand.
7. **Document metadata** shown to admin: name, version, issue date, page count, status, last indexed at, size.
8. **Audit trail**: who uploaded / re-indexed / disabled what, when.

---

## Findings (append below)


## Findings — Admin upload + document versioning

(No external search needed — this is mostly design. Synthesis based on prior topic findings + PRD requirements.)

### Storage strategy
- **Object storage for raw PDFs:** S3-compatible. Cloud: Cloudflare R2 (free egress), AWS S3. Self-host: MinIO (S3-compatible, runs in Docker).
- **Postgres for metadata + chunks:** the `documents` table stores name, version, status, file_key (S3 key), uploaded_by, uploaded_at. The `chunks` table stores section, page, content, embedding.
- **Why not store PDFs in Postgres:** large blobs slow down backups and queries. Object storage is cheaper and standard.

### Document lifecycle
```
draft ──upload──▶ processing ──success──▶ active ──admin-disable──▶ disabled
                       │
                       └──fail──▶ failed (admin can retry or delete)
```

- Only ONE `active` document at a time. New uploads start as `draft`; admin can test them; admin can promote to `active` (which automatically sets the previous `active` to `disabled`).
- The `active` document is the one used for ALL chat queries.
- The `draft` document is only queryable by the admin (in a "test mode" UI).

### Re-indexing
- Triggered automatically on upload.
- Manual re-index button (admin clicks) for the currently `active` document.
- Re-index is a background job (FastAPI BackgroundTasks for MVP, ARQ/Dramatiq for production).
- Job status visible to admin: queued / running (with progress) / success / failed.

### Test mode
- Admin selects a `draft` document, types a question, sees the answer that WOULD be given if this were the active document.
- Implementation: same `/chat` endpoint, but with `?use_document_id=<id>` query param, admin-only, results NOT logged to user conversation history.

### Rollback
- Admin clicks "Make Active" on any non-active document. Status changes; queries immediately use it.
- The old active document becomes `disabled` but its chunks and logs are preserved for audit.

### Audit trail
- `document_audit_log` table: `document_id`, `action` (upload / reindex / activate / disable), `actor_id`, `timestamp`, `details` (JSONB).
- All admin actions are logged.

### File handling details
- **Allowed types:** PDF only (MVP).
- **Max size:** 50 MB (configurable). Our PDF is 5.7 MB.
- **Filename:** original filename preserved. Display name = `name` field set by admin on upload.
- **MIME check:** `application/pdf`. Reject otherwise.
- **Virus scan:** optional, deferred to v2.

### UI components (GPR-styled)
- `<SidePanel>` for "Documents" sidebar (in admin mode).
- List of documents: name, version, status badge, "Re-index" button, "Make Active" button, "Disable" button, "Test" button.
- Upload: drag-drop zone in admin panel.
- Test mode: temporary chat surface with a "Testing against: <doc name> v<version>" banner.

### Acceptance criteria
- Admin can upload a PDF, see it appear as `draft`.
- Admin can run questions against the draft (test mode) and see results.
- Admin can promote draft → active, and chats immediately use the new doc.
- Admin can disable the current active doc, and chats fall back to: "no active document — please contact admin".
- Re-index button rebuilds the index from the raw PDF (useful if embeddings model is upgraded later).

