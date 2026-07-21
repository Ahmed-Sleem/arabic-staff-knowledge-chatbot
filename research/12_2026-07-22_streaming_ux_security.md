
---

## 2026-07-22 — Research Addendum: Authentic Streaming, Chat UX, Mobile Layout, and Credential Hygiene

### Evidence reviewed
- WHATWG SSE format requires UTF-8 event streams and event blocks terminated by a blank line. A `data:` field cannot safely carry raw multi-line arbitrary content without correct framing. JSON-encoding each typed payload avoids newline/Unicode corruption. [WHATWG SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- MDN documents `text/event-stream`, blank-line event boundaries, comment keepalives, and `X-Accel-Buffering: no` for proxies that might buffer an event stream. [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- OpenAI-compatible streaming returns incremental `delta` content when `stream=True`; deltas are fragments, not words or sentences. A client must append verbatim, preserve whitespace, and commit durable conversation state only on successful completion. [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/how_to_stream_completions)
- An accessible chat composer uses a native auto-resizing textarea, disabled send control when empty/streaming, Enter-to-send and Shift+Enter newline semantics, plus IME composition protection. [MUI Chat Composer](https://mui.com/x/react-chat/material/composer/)
- A scroll-mask is preferable to a coloured overlay for fading message content because it adapts to themes; use prefixed and unprefixed mask declarations with a static/overlay fallback. [shadcn scroll-fade](https://ui.shadcn.com/docs/utils/scroll-fade)
- GitHub says revocation/rotation comes first for exposed credentials. Removing a credential from current files is insufficient; use `git-filter-repo --sensitive-data-removal` on a disposable mirror, verify all refs, force-push deliberately, coordinate clone resets, and contact GitHub Support for cache/PR reference removal where applicable. [GitHub documentation](https://github.com/github/docs/blob/main/content/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository.md)

### Findings in the checked-out repository (verified 2026-07-22)
1. `main` is clean and identical to `origin/main` at `115afeb`; public remote exposes only `main`, with no existing feature branch.
2. The current UI already has a mobile menu SVG, an auto-growing textarea, JSON token parsing, and a load screen. The requested work is therefore a correctness/refinement pass, not a greenfield build.
3. The browser currently includes the selected provider key in `X-LLM-API-Key`. It is also persisted in browser `localStorage` by the existing profile manager. This is acceptable only for a deliberately user-managed BYOK design, and cannot be called server-secret storage.
4. The backend uses a mix of genuine streaming and synthetic word splitting. Gemini's cycle request currently uses non-streaming `generateContent`, then splits full text into words. Several fallback paths also split a completed string into words. These are not genuine provider-token streaming paths.
5. The frontend mutates React state for every parsed token; it needs an animation-frame batching boundary to remain responsive under high token rates while still displaying each received delta without an artificial typing delay.
6. A tracked governance file contains a live-looking API credential and appears in reachable repository history. The checked-out tracked files and reachable history contain no GitHub-PAT-format string. A test fixture contains a deliberately fake API-key-shaped value.

### Design decisions proposed for implementation
- Define a versioned typed SSE envelope for `status`, `delta`, `done`, `error`, and optional keepalive comments. Continue parsing real provider deltas verbatim.
- Pass the request-disconnect signal through the API route to the agent/provider stream; cancel upstream work when the browser cancels. Add no-buffer/cache-control headers and test them as an HTTP contract.
- Render partial Markdown in a conservative, safe subset without dangerously injecting HTML. Incomplete syntax remains literal until complete; completed Markdown re-renders deterministically. Citation parsing remains explicit rather than HTML rendering.
- Use a fixed-height composer shell with its own padding/reserved send-button column. The textarea alone grows inside the shell; the send action is absolutely anchored to the shell’s block-end/inline-end, so it never moves when the textarea height changes.
- Apply a theme-aware top/bottom message viewport fade using a mask where supported, with non-interactive gradient overlays as fallback. Keep the composer outside the masked scroll region and give it a subtle elevation/shadow separator.
- Mobile menu remains an icon-only native button with text accessible name, focus target, Escape/backdrop close, and body-scroll locking. The left panel’s min width will be calculated from the required controls plus consistent side padding rather than an arbitrary width.

### 2026-07-22 remediation outcome
- A user-authorized mirror rewrite removed discovered credential material from all eight reachable repository commits, then force-updated GitHub `main`.
- The scan intentionally detects GitHub PAT forms, provider key forms, Google API-key forms, PEM private-key markers, and the specific documented admin password. It returned no matches after rewrite.
- Production source equivalence was measured with a SHA-256 manifest of 70 non-test application/deployment files before and after history surgery; all hashes matched.
- GitHub’s Secret Scanning alerts endpoint was accessible and returned zero alerts after the force-push.
- This is repository hygiene, not credential revocation: any credential previously exposed must still be rotated at its issuing provider, and GitHub Support/clone owners may be necessary to remove external caches/copies.
