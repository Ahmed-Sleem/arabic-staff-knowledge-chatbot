# Implementation Plan — 2026-07-22

**Status:** Planning only. No source implementation, commit, branch creation, force push, or deployment has been performed in this session.

## Verified repository baseline
- Repository: `Ahmed-Sleem/gpr-general-purpose-rag`
- Public remote inspected without credentials.
- Checked-out branch: `main`; HEAD and `origin/main` are identical at `115afeb4e7e174eefa17717a217cb7708850e677`; working tree is clean.
- Remote exposes only `main`; there is no current feature branch to audit or continue.
- The recent commit contains the documented preceding UI work. The repository is not behind the public remote; its documentation is internally inconsistent in historical references but current source is authoritative.

## Required approvals before implementation
1. Approve credential-incident remediation, including a history rewrite/force-push if the exposed provider credential must be removed from Git history.
2. Confirm whether BYOK keys may remain browser-local or must become server-managed.
3. Approve the proposed branch naming and merge workflow.
4. Confirm the plan below. After approval, work proceeds one atomic gap at a time, with an audit/log/test entry before the next gap.

## Ordered execution plan

### 0. Security gate — GAP-GPR-31
- Ask owner to revoke the exposed GitHub PAT and rotate the separate provider credential observed in tracked history.
- Build a disposable mirror for history surgery; create an offline backup; use replacement/path filtering only after credentials are revoked.
- Add preventive ignore rules and a local/CI secret scanner that reports only file/path/type, never secret values.
- Verify all refs and working tree have no real token matches, document clone reset instructions, then seek a separate confirmation before any destructive force push.

### 1. Native streaming backend — GAP-GPR-32
- Trace the supported provider paths in `src/backend/agent/react_agent.py` and remove production word-loop simulation.
- Use each provider's streaming endpoint/API, forward every content delta verbatim as a JSON SSE `delta` payload, and retain model/tool status as distinct typed events.
- Implement Gemini native `streamGenerateContent` parsing rather than non-streaming `generateContent` followed by local splitting.
- Add response headers to prevent intermediary buffering; include a keepalive for long retrieval phases; bind upstream cancellation to request disconnect.
- Normalize errors without exposing provider keys or raw request headers.

### 2. Incremental stream client and Markdown — GAP-GPR-33
- Replace the hand-written per-line parser in `ChatPanel.tsx` with a newline/CRLF-safe event-block parser that flushes the final decoded text at EOF.
- Accumulate exact deltas in a ref; schedule React visual updates through `requestAnimationFrame` only. This limits rerenders but does not manufacture or delay text.
- Persist the assistant turn only after terminal `done`; retain partial UI plus actionable retry/cancel error state on failure.
- Add safe incremental Markdown handling (headings, lists, emphasis, code/citations) with text escaping and partial-token tolerance; no HTML injection.
- Support user-controlled scrolling: autoscroll only if already near bottom, otherwise show a “new output” affordance.

### 3. Composer redesign — GAP-GPR-34
- Replace layout coupling with a semantic `<form>` and stable composer shell.
- Reserve an inline-end action rail equal to the send button’s hit area; absolutely anchor send at the shell’s block-end/inline-end so growing input height cannot move it.
- Implement Enter send / Shift+Enter newline / IME composition guard; expose accessible label, keyboard focus ring, disabled/loading status, and a cancel control only if backend cancellation lands in gap 1.
- Use shared sizing tokens and RTL logical properties rather than one-off pixel-only inline styling.

### 4. Message viewport and input separation — GAP-GPR-35
- Scope top/bottom fade exclusively to `.chat-messages`, with `mask-image` / `-webkit-mask-image` and an overlay fallback that does not intercept pointer events.
- Maintain a short fade (about 16–24 px), disabled/reduced for `prefers-reduced-motion` if animated, and ensure focused citations/messages remain visible.
- Give composer a themed background, divider and soft upward shadow that visually separates it without obscuring the last message.
- Increase spacing above the thinking card to match adjacent bubble inset/spacing using a named spacing token.

### 5. Sidebar/mobile geometry — GAP-GPR-36
- Eliminate conflicting 160px inline max-width. Build the sidebar controls as a full-width grid/flex row: flexible search plus two equal icon buttons, all with common 32–36px height and equal outer insets.
- Define left-panel minimum width from its minimum viable row (search minimum + two controls + two gaps + double inset) and use it as the desktop default/resize clamp.
- Ensure the right panel/search follows the same `--space-*` and `--edge` rhythm.
- Retain the menu SVG but verify button semantics, focus style, Escape/backdrop close, scroll locking, and visually centered mobile drawer contents.

### 6. Loading continuity — GAP-GPR-37
- Load validated persisted theme/language preferences synchronously/safely enough to render the load screen in the same final mode; use default English/light/dark only when no preference exists.
- Share theme tokens between `LoadScreen` and main app, avoid a flash of opposite mode, and provide a non-blocking failure fallback.

### 7. Tests and acceptance — GAP-GPR-38
- Backend: provider stream adapters mocked only in tests; SSE framing/header/cancellation tests; test a first delta occurs before done; verify no production word-splitting loop remains.
- Frontend: parser tests for fragmented UTF-8/CRLF/event boundaries, Markdown partials, user scroll intent, textarea/send anchoring, mobile drawer controls, and stored-mode load screen.
- Build/test: `pytest` full suite, frontend production build, static type/lint checks available in project, secret scan.
- Manual acceptance: Chromium desktop and narrow mobile viewport; English and Arabic/RTL; light/dark persisted state; actual provider with a non-sensitive owner-supplied BYOK key; inspect Network timing for progressive SSE arrival; keyboard-only composer/menu journey.
- Git: create `feat/gpr-streaming-composer-ux` from current `main` only after approval, commit atomic gaps, show diff/test evidence, wait for approval, then one merge/push to `main` to trigger Railway.

## Expected final result
The application will display genuine provider-delivered text deltas in real time (not fabricated typing), safely render progressively formed Markdown, and retain a stable, accessible AI composer whose send button stays at the input’s bottom-right corner. The chat feed will have subtle top/bottom fades and a clear composer separation. Sidebar/mobile controls, loading state, and spacing will be consistent across layouts. Credential exposure will be remediated with an explicit, safe history-cleanup plan. No production push occurs until you review and approve it.
