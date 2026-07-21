# Agent working rules — READ THIS AT THE START OF EVERY SESSION

**Ahmed's standing instructions for how you (the AI) MUST work on this project.**
This file is APPEND-ONLY. Every session I re-read it before doing anything.

## The rules (append-only — count grows across sessions; currently 30)

### Process rules
1. **Think step-by-step in writing.** Before doing anything non-trivial, create a temp MD file in `_working_docs/thinking/` numbered `NN_topic.md`. Break the user's request into parts. Write down what you're going to do.

2. **Self-check.** After finishing a task, re-read your thinking notes AND the AUDIT gap for that task. Ask: did I miss anything? Is this what the user asked for? Would a new user find this convenient?

3. **Delete thinking notes when done.** Permanent files (`AGENT_RULES.md`, `AUDIT_AND_TODO.md`, `IMPLEMENTATION_LOG.md`, `CHANGELOG.md`, `NEXT_SESSIONS_ROADMAP.md`) stay. Thinking notes are ephemeral.

4. **Every change goes into `AUDIT_AND_TODO.md`.** New gaps discovered mid-work → append. Never delete a gap without proof it's fixed.

5. **Every session appends to `CHANGELOG.md`.** Format: `## YYYY-MM-DD session N`.

### Implementation rules (added session 6 by Ahmed)

6. **Fix gaps ONE BY ONE.** No batch mode. Do gap V01 completely, verify it, log it in `IMPLEMENTATION_LOG.md`, then start V02. Never touch two gaps at once.

7. **After finishing each gap, self-verify.** Three questions I must answer in the implementation log for EVERY gap:
   - a) Is the gap fully fixed? (evidence: file paths + line numbers)
   - b) Is everything wired and ready for production? (evidence: what did I actually connect together end-to-end)
   - c) Is my test really validating that? (evidence: how the test proves the behavior — not just "code compiles")

8. **Not allowed to move to next gap until current one is 100% done.** No "half-done, come back later."

9. **Write tests for each gap.** Unit test if pure logic. Integration test if a wire-up. Contract test if new API. Where a test can't be automated in the sandbox (e.g. requires Docker), document the manual test steps + note this in the log.

10. **Maintain `IMPLEMENTATION_LOG.md`** — a companion file to AUDIT. Every gap I close gets a section here with:
    - Gap ID + one-line description
    - Files touched (paths + change summary)
    - Tests added (paths)
    - How I verified (evidence — commands run + observed output OR manual test steps)
    - Self-check answers (a/b/c from rule 7)

11. **Compare AUDIT_AND_TODO.md vs IMPLEMENTATION_LOG.md at the end of every session.** Every "M1" gap in AUDIT must have a matching closed entry in IMPLEMENTATION_LOG. If not, the session isn't done.

### Product rules

12. **Two products, two repos, one shared bundle for testing.**
    - **Vyne** (GitHub: `Ahmed-Sleem/vyne`) — the workflow engine. Multi-tenant capable. n8n competitor. GENERIC — no product-specific hardcoding.
    - **GPR** (GitHub: `Ahmed-Sleem/gpr`) — the flagship customer of Vyne. Chat GUI with sandbox.
    - **`local-bundle/`** — throwaway testing sandbox. NEVER push its files (`docker-compose.yml`, `.env`, `start.sh`) to GitHub.
    - Any real bug fix in the bundle MUST be forward-ported to the git repo.

13. **GitHub is production.** Every fix must be: clean (no bundle-specific hardcodes), backward-compatible or documented migration, on the correct branch. GitHub state must be tracked in this doc.

14. **One PR per repo when shipping a release.** Ahmed wants single-click merge. Stacked commits inside the PR are fine. Base off `fix/p2-medium` so fast-forward-merge to main works with zero conflicts.

15. **Ask "how does the user use this?" for every design decision.** Reference n8n / Zapier / Retool / Vercel patterns when relevant.

### Communication rules

16. **Direct, no fluff, verify claims with evidence.** User: "make sure everything is perfect before giving me the zip".

17. **Never lie about verification.** If I can't test something (e.g. no Docker in the sandbox), say so. Document the manual test steps for Ahmed to run.

18. **Session start checklist:**
    1. `cat _working_docs/AGENT_RULES.md` (this file)
    2. `cat _working_docs/AUDIT_AND_TODO.md` (what's outstanding)
    3. `cat _working_docs/IMPLEMENTATION_LOG.md` (what's already closed)
    4. `tail -50 _working_docs/CHANGELOG.md` (last session)
    5. Confirm git PAT still works if I need to push
    6. Then start thinking about the user's new request

19. **Session end checklist:**
    1. Update `AUDIT_AND_TODO.md` (mark closed gaps, log new ones)
    2. Update `IMPLEMENTATION_LOG.md` (every gap I closed has its section)
    3. Verify: every "closed" gap in AUDIT has a matching entry in IMPLEMENTATION_LOG
    4. Append to `CHANGELOG.md`
    5. Delete `_working_docs/thinking/*.md`
    6. Tell Ahmed what happened + what's next

### Quality & Production rules (added session 10 by Ahmed)

20. **Never assume — verify.** Before making ANY claim about code, state, config, or behavior: read the file, run the command, query the API, ssh into the VPS, whatever it takes. If verification isn't possible right now, say so out loud and label the claim as `[UNVERIFIED]`. Memory from earlier in the session doesn't count — re-read.

21. **No shortcuts, no "easy way".** Every gap gets the full treatment: root-cause diagnosis (not just symptom-patching), complete fix, self-check, tests, documentation, verified deploy. If a shortcut is being taken to unblock something, mark it EXPLICITLY as tech debt in AUDIT_AND_TODO.md before moving on. "Good enough for now" is banned language.

22. **Production-grade only — no mocks in production paths.** Every code path shipped to `main` on either repo MUST be the real implementation:
    - No mock LLM responses in production code paths.
    - No fake auth (`if password === 'admin'`), no hardcoded users.
    - No stubbed API returns (`return { fake: true }`).
    - No commented-out `TODO: implement later` where the caller silently no-ops.
    - No `console.log("would call X here")` placeholders.
    - **Test mocks in `tests/**` are fine and expected** — they belong there, not in `src/**`.
    - If a real implementation cannot ship today: DO NOT SHIP A STUB. Ship nothing, open a GAP with a clear reason + estimate, finish it in the next session.

23. **Ahmed's parse-think-verify loop — the canonical work protocol.** When Ahmed sends non-trivial instructions:
    1. **Parse** — create `_working_docs/thinking/NN_points_TOPIC.md` with every atomic instruction as a `- [ ]` bullet. Nothing skipped, nothing merged.
    2. **Header** — the top of every temp file MUST include a `# DELETE AFTER:` clause stating the exact condition for deletion.
    3. **Reason** — create a SEPARATE `_working_docs/thinking/NN_thinking_TOPIC.md` for reasoning. For each point in the points file, append the reasoning + decision.
    4. **Sweep** — when every point has a decision, delete the points file (its purpose is served).
    5. **Re-read** — read the thinking file end-to-end BEFORE acting. This catches cross-point contradictions.
    6. **Execute** — carry out the decisions, appending results to the thinking file.
    7. **Promote** — record outcomes in permanent files (`AUDIT_AND_TODO.md`, `IMPLEMENTATION_LOG.md`, `CHANGELOG.md`).
    8. **Delete** — remove the thinking file when the DELETE AFTER condition is met.
    9. **Never mix** — permanent files NEVER live under `thinking/`. Thinking files NEVER hold facts that need to outlive the current task.

24. **On ambiguity — ASK, don't guess.** Any unclear requirement gets a clarifying question (use the ask_user tool with 2–4 options where possible). Two quick questions are cheaper than one wrong implementation Ahmed has to review.

25. **Search the internet before you write code.** Whenever a claim depends on external state (library API surface, current best-practice, CVE status, version compatibility, deprecation), use `web_search` first. Training data can be months or years stale — verify.

26. **Bulletproof code standard.** Every file that ships to production must satisfy:
    - Top-of-file docblock explaining WHY this module exists (not just what).
    - Every non-obvious code path: inline comment explaining WHY.
    - Every async op: explicit error handling (try/catch, `.catch`, or documented "fire-and-forget" with justification).
    - Every external input: validated (Zod schema, or equivalent) before use.
    - Every promise: awaited OR explicitly detached with a comment stating why.
    - No `any` types unless the reason is justified in a comment above the line.
    - No `console.log` in production code — use the app's structured logger.
    - No unhandled promise rejections. No swallowed exceptions.

### Testing & Verification rules (added session 10 by Ahmed)

27. **Live VPS is the acceptance environment.** Since session 9, the auto-deploy pipeline pushes every `main` commit live within ~30–90s to https://vyne.gpr.com and https://chat.gpr.com. The verification protocol is:
    - Local unit / integration tests still run for TDD (sandbox `npm test` or `pytest`).
    - The FINAL acceptance signal is the live VPS: exercise the feature at the real HTTPS URL and observe real behavior.
    - After a push, WAIT for the deploy workflow to succeed (poll `/repos/Ahmed-Sleem/{repo}/actions/runs`) before asking Ahmed to test.
    - Include the exact URL + click-path + expected result in every "please test" message to Ahmed.

28. **Thinking-vs-permanent file separation is enforced by placement.**
    - `_working_docs/*.md` (top level) = permanent. Never delete without Ahmed's explicit approval.
    - `_working_docs/thinking/*.md` = temporary. MUST be deleted per rule 23 step 8.
    - No exceptions. No "I'll keep this thinking file around because it's useful."

### Context recovery & Architecture rules (added session 26 & completed)

29. **After every conversation summarization / compaction / new-session start / handoff — re-explore the project from scratch before acting.** Do NOT trust only the summary the previous language-model instance produced. The procedure is MANDATORY every time you get a summary or start a fresh turn without prior in-session work:
    1. Re-read the permanent MD files IN ORDER:
       - `_working_docs/AGENT_RULES.md` (this file — every rule, every time)
       - `_working_docs/AUDIT_AND_TODO.md`
       - `_working_docs/IMPLEMENTATION_LOG.md`
       - `_working_docs/CHANGELOG.md` (tail 50–100 lines)
       - `_working_docs/NEXT_SESSIONS_ROADMAP.md`
       - `_working_docs/USER_JOURNEYS.md` when a UX/product decision is on the table
       - `_working_docs/VPS_DEPLOYMENT.md` when a deploy/ops decision is on the table
    2. Re-check the ACTUAL state of both repos or current workspace with git (`git status`, `git log --oneline -N`, `git branch -a`) or filesystem inspection — do NOT trust summarized claims until bash confirms.
    3. Re-check what's live on the VPS when the task depends on live behavior (SSH + `docker ps` + curl the endpoint).
    4. If the summary and reality disagree, REALITY WINS. Update your mental model, note the divergence, keep going.
    5. Only THEN start executing the next task.
    6. This rule applies EVERY time: every message that starts a new context, every summarization event, every "continue from where you left off" prompt.
    7. Skipping this rule = Rule 20 violation ("Never assume — verify").

30. **Workspace Architecture & Document Governance.** When developing specialized internal tools or sub-projects within the GPR/Vyne ecosystem (such as the *Arabic Staff Knowledge Chatbot*):
    - **`_working_docs/` is the master agent workflow controller.** All gap management (`AUDIT_AND_TODO.md`), session logs (`CHANGELOG.md`, `IMPLEMENTATION_LOG.md`), and thinking scratchpads (`thinking/*.md`) live strictly in `_working_docs/`.
    - **`_development_docs_REMOVE_BEFORE_DEPLOYMENT/` is for developer architecture & handoff docs.** It holds project blueprints (`IMPLEMENTATION_PLAN.md`, `PROJECT_MAP.md`, `SUPPORTING_NOTES.md`). Gaps discovered in those plans MUST be mirrored and tracked to completion inside `_working_docs/AUDIT_AND_TODO.md`.
    - **`research/` holds topic deep dives.** Append-only, never rewritten from scratch.
    - **`uploads/` holds immutable source materials** (PRDs, design specifications, source PDFs). Never modify original source inputs in `uploads/` directly unless extracting or indexing.

## Standing context (short reference)

- **DeepSeek API key** (working): `${PROVIDER_API_KEY}`
- **Vyne admin creds after rotation**: `admin@vyne.local` / `${VYNE_ADMIN_PASSWORD}``
- **GitHub PAT** (scopes `repo` + `workflow`): `${GITHUB_PAT}`
- **Vyne repo**: `Ahmed-Sleem/vyne`, primary branch = `main` (auto-deploys on push)
- **GPR repo**: `Ahmed-Sleem/gpr`, primary branch = `main` (auto-deploys on push)
- **User's Mac path**: `~/local-bundle/`
- **User's timezone**: Africa/Cairo
- **`/home/user/vyne/` and `/home/user/gpr/`** are the GIT WORKING TREES. Do NOT delete. Use for GitHub pushes.
- **`/home/user/local-bundle/{gpr,vyne}/`** are the EXPORT copies (no `.git`) that go into the user's testing bundle.

### Production VPS (live since session 9)

- **Provider**: Hostinger VPS, Ubuntu 24.04 LTS
- **IP**: `76.13.62.185`
- **SSH access as deploy user**: `ssh -i /tmp/vps_privkey deploy@76.13.62.185` (agent regenerates the key each session from Ahmed's bootstrap output, per rule 20 verify-don't-assume)
- **Domains**:
  - https://vyne.gpr.com — Vyne admin UI + API + WebSocket (path-routed by Caddy)
  - https://chat.gpr.com — GPR chat GUI
- **DNS**: A records at Hostinger hPanel → `gpr.com` DNS → `vyne` + `chat` → `76.13.62.185`
- **TLS**: Let's Encrypt (auto-renewed by Caddy)
- **Deploy pipeline**: `push origin main` → GitHub Actions `Deploy to VPS` workflow → appleboy/ssh-action → `deploy@76.13.62.185:/opt/gpr-vyne/deploy.sh` → containers rebuilt + hot-swapped. Total ~30–90s for code changes, ~3–8min if any Dockerfile changes.
- **Actions secrets** (set on BOTH repos): `VPS_HOST=76.13.62.185`, `VPS_USER=deploy`, `VPS_SSH_KEY=<ed25519 private key from bootstrap>`
- **VPS layout**: `/opt/gpr-vyne/` contains `vyne/` (git tree), `gpr/` (git tree), `deploy.sh`, `docker-compose.yml`, `.env`, `vyne-workspaces/`
- **All 6 containers** (must be healthy for any acceptance test):
  - `gpr-vyne-server` — Fastify backend, `127.0.0.1:3001->3000`
  - `gpr-vyne-ui` — nginx serving React SPA, `127.0.0.1:8081->80`
  - `gpr-gui` — Next.js chat GUI, `127.0.0.1:8080->3000`
  - `gpr-docker-proxy` — restricted docker socket for sandbox tool
  - `gpr-searxng` — metasearch backend
  - `gpr-search-api` — FastAPI wrapper for web.search / deep-search tools

## Ahmed's Repository Creation & Storytelling Style (Mandatory Rule)

When creating new repositories or writing READMEs for Ahmed, always adhere to his distinct style:
1. **Story-Driven Genesis**: Never start with dry technical boilerplate. Begin the README by telling the real-world story of why the tool was built (e.g. *"I was using Instagram web, wanted to analyze my story viewers, but couldn't get a clean export list. So I got the idea to build..."*).
2. **Sharp, Direct & Minimal**: Cut the fluff. Keep instructions razor-sharp and direct. No bloated documentation paragraphs.
3. **Detail-Rich Execution**: Never miss technical details—include exact installation steps (e.g., `chrome://extensions/`, Developer Mode), usage workflows, and output file descriptions (.csv, .json, HTML reports).
4. **Professional Engineering Standards**: Clean file layouts, Manifest V3 extensions, zero-stub production code, and robust git commit hygiene.
