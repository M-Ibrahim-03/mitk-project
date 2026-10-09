# Veil — Project Context and Agent Handoff

Last verified: 2026-10-10
Project root: `mitk-project`
Status: React intake accepts only the known local ticket `TICKET-DEMO-1042`, and the chat explains this rule. The synthetic benchmark now has separate development and held-out corpora covering all 11 advertised entity types, per-type TP/FP/FN/precision/recall/F₂, independent scans of exact tool receipts, a blocked-path zero-call check, and warmed repeated gateway-only timing. The Streamlit fallback has a separate generic nested-JSON example. A valid spaced-IBAN-in-prose miss was found by the expanded corpus and fixed test-first. The live Gemini browser path remains unverified after its latest reported `ServerError`; keep it optional until a fresh same-run trace completes.

> **Start here when opening this repository in another IDE, agent, or chat.** Read this file first, then `implementation-plan.md` and `README.md`. Treat this file's **Current state** and **Next action** as the freshest checkpoint. The plan preserves the original design and implementation sequence; some early Phase 7 paragraphs describe React Flow as the intended graph, while the implemented page uses an accessible vertical CSS-connected evidence flow, animated connector particles, and Motion. Do not rebuild already working features because a plan paragraph is historical.

## Quick handoff

Veil is a local-first hackathon prototype of middleware between an AI agent and a tool. A user submits a synthetic helpdesk message to either the default deterministic offline agent or an explicitly configured Gemini agent. Gemini mode sends only a locally tokenized prompt to Google's hosted API; its proposed call is schema-checked and must still pass through Veil before the offline simulated helpdesk. Gemini sees a protected tool result, and Veil restores known tokens locally after the draft answer. The React chat and workflow pages share the same backend run.

The Python workflow, API, React pages, and tests are already implemented. Keep the middleware and local simulated tool as the core; the UI is evidence of that workflow. Gemini is optional and server-configured. Do not replace the tested privacy path or send real personal/confidential data to Gemini.

## Current state and next action

### Latest continuation checkpoint — 2026-10-10

**Goal:** strengthen the judge evidence while preserving the React valid-ticket intake and the existing Veil gateway.

**Implemented:**

- `data/benchmark.json` retains the original eight cases and adds cases for every advertised detector type. `data/benchmark-heldout.json` contains a separate fixed synthetic held-out set. Both include natural-language, nested object/array, repeated, formatting, and benign-lookalike cases.
- `veil/evaluation.py` reports exact-span TP/FP/FN, precision, recall, and F₂ globally and per entity type for development and held-out splits. It scans the exact `SimulatedTool.received` payload recursively for planted literals in both keys and values. Its fault-injected blocked path reports zero tool calls and zero receipts.
- Latency now uses 20 warm-up calls and 100 measured calls per fixture, records Python/platform/machine and payload-byte ranges, and measures the gateway sanitize/egress interval only. The mock tool, restoration, Gemini, and network are excluded.
- `veil/structured_demo.py` runs a nested JSON plus free-text synthetic request through the generic `VeilGateway` and captures the receipt directly from `SimulatedTool.received`. The Streamlit fallback displays this as a separate example; React intake remains ticket-only.
- The held-out corpus exposed that a spaced IBAN followed by prose could be greedily matched with the following words. `tests/test_detection.py` first reproduced the miss; the detector now selects the shortest checksum-valid boundary.

**Latest benchmark:** development 33 cases / 49 planted spans, TP 49, FP 2, FN 0, precision 96.08%, recall 100%, F₂ 99.19%; held out 26 cases / 26 planted, TP 26, FP 2, FN 0, precision 92.86%, recall 100%, F₂ 98.48%. The independent receipt scan found zero planted literals, restoration was 100% in both splits, and the blocked path made zero tool calls. The two phone false positives in each split are numeric lookalikes, including an invalid card-shaped string; they are documented in `benchmark-results.md`. Timings vary by run; the latest recorded table is authoritative for this checkpoint.

**Verification:** `tests/test_detection.py tests/test_evaluation.py tests/test_structured_demo.py` — 22 passed. `tests/test_gateway.py -k 'not http_tool_endpoint'` — 7 passed, 1 deselected. `python -m veil.evaluation` completed with 3,300 development and 2,600 held-out timing samples. `git diff --check` is clean apart from normal Windows LF-to-CRLF notices. `python -m py_compile` passed for the changed Python modules. The focused Streamlit `AppTest` for the new panel stalled without producing a test result; UI behavior is not claimed verified. `.venv\Scripts\python.exe -m pytest --last-failed` collected 80 tests, passed the 12 tests before `tests/test_demo_ui.py`, then stalled there without output for 60 seconds and was interrupted. The full suite is not verified.

**Gemini status:** no fresh same-run browser rehearsal has been established after the reported final-answer `ServerError`. A direct API start from this execution environment failed with Windows socket error `10013`; the local health request was blocked the same way. No API or frontend listener was left running. Gemini remains optional; do not claim its live path succeeded until one run visibly completes tokenized model input, validated proposal, egress, exact protected receipt, protected tool context, trusted restoration, and final answer. No API key was inspected or printed.

**Next action:** rehearse the Streamlit structured example and the same-run Gemini flow from the user's local project terminals, where loopback binding is available. Use synthetic data only. Keep Gemini optional if any stage cannot be verified, and keep all prior checkout changes intact.

### Earlier handoff snapshot — exact stop point (2026-10-10)

**Goal:** finish and verify the optional real Gemini agent path in the existing Veil application. The original user requested Gemini as the agent, with the local Veil middleware protecting data before agent-to-tool handoffs. Gemini use is explicitly authorized for synthetic data. The helpdesk remains simulated and local.

**What exists and why:**

- The hackathon MVP is an explainable privacy gateway: selected PII recognizers, recursive text/JSON scanning, task-scoped reversible tokens, fail-closed egress verification, simulated helpdesk, trusted response restoration, synthetic benchmark, FastAPI run API/SSE, and Streamlit fallback.
- The deterministic local agent remains an offline fallback. Gemini is opt-in and server-configured because user requested a real agent while keeping the tool simulated. Veil locally tokenizes the prompt before Gemini sees it; Gemini proposes one allowlisted tool call without SDK auto-execution; the proposal goes through `VeilGateway`; Gemini receives protected tool context; Veil restores only current-task tokens locally.
- The React chat page (`/`) is a single free-form message field with a liquid-glass treatment. Its API accepts only tickets that exist in the local simulated helpdesk; the only seeded ticket is `TICKET-DEMO-1042`. Gemini mode exposes only the real Gemini ticket-lookup proposal. The workflow page (`/runs/{run_id}`) displays six persistent connected stages and evidence from that exact run. It uses CSS/SVG connectors and Motion; React Flow was an earlier proposal and is not the current implementation.
- PII detection is deliberately selected-pattern and limited. Tokens are reversible pseudonyms, not encryption. Never claim universal detection or production security. Use synthetic data only and avoid logging raw values.

**Recent source changes:**

- `veil/payload.py` now scans a same-length view with exact current-vault tokens masked. This prevents a token issued during Gemini prompt protection from being reclassified and nested during the gateway's second scan, while preserving offsets and keeping unknown token-like strings subject to detection. `tests/test_gateway.py` contains the test-first regression.
- `requirements.txt` allows `google-genai>=1.0,<3`; `tests/test_setup.py` checks the installed SDK version is covered by the declaration.
- The React run API validates one ticket ID against the local simulated ticket list before queueing. It explains the accepted example, `TICKET-DEMO-1042`; malformed, unknown, missing, or ambiguous IDs are rejected before Gemini or the helpdesk runs. Gemini tool declarations now expose only `lookup_helpdesk_ticket`.
- The chat now defines a valid ticket in plain language: it must exist in the local helpdesk, and this demo accepts only `TICKET-DEMO-1042`; missing or other IDs are rejected. A detector regression showed that `My name is Jordan Sample and ...` was missed because the case-insensitive name regex greedily included lowercase `and`. The prefix is now case-insensitive while name capitalization stays case-sensitive.
- `create_gemini_client()` now configures three SDK attempts with short exponential backoff. The installed Google Gen AI SDK disables retries when `HttpRetryOptions` are omitted; this explains why a transient `ServerError` on the final-answer request ended the run immediately. `tests/test_gemini_agent.py` checks the retry configuration.
- The chat displays API validation errors and final failed-run events. Gemini's protected context event records both its tokenized user message and the checked helpdesk result.
- The checkout was already dirty before this work. Keep every existing modification and inspect status before editing; do not reset or clean the tree.

**Verified in the current source:**

- `.venv` has Python 3.12 and `google-genai` 2.29.0; `pip check` passes.
- Focused Python suite after the latest Gemini retry change: `tests/test_gemini_agent.py` — **10 passed**. The retry-configuration regression failed first because `retry_options` was absent, then passed after the fix.
- A synthetic preflight and direct current-source workflow covered 10 selected categories (person, email, phone, Aadhaar, bank account, UPI ID, card, PAN, IFSC, IBAN). Detected values were absent from the captured helpdesk payload; egress passed; trusted restoration and agent answer completed.
- Direct blocked-path execution ended at the egress gate with no helpdesk event or payload.
- Frontend tests: **15 passed across 4 files**. The chat test confirms the valid-ticket explanation, API rejection visibility, and failed-run visibility. `npm run build` passes.
- `git diff --check` passes; Git emits only LF-to-CRLF working-copy notices.

**Current visual/runtime snapshot:**

| Surface | Observed state | Meaning |
| --- | --- | --- |
| Chat `/` | The browser rejected synthetic `TICKET-1000` immediately with guidance to use `TICKET-DEMO-1042`; no run was queued. It visibly explains that only tickets present in the local helpdesk are valid. | Confirms the active browser API enforces the ticket allowlist and the UI explains it. |
| Valid ticket request | Latest reported run `61ea0f91295d450198f71d4d0ea2954a` ended with “Gemini final-answer request failed (ServerError).” | The workflow reached the final-answer request, so Gemini likely accepted the key for the earlier proposal call. The final model request failed; this does not verify a successful answer. The exact request text is intentionally not copied here. |
| Gemini SDK retries | Current SDK source sets one attempt when `retry_options` are omitted, including for retryable 5xx errors. | Source now requests three attempts with short backoff. Restart the API before testing this fix in the browser. |
| Detector regression | A direct current-source probe initially found only the synthetic email, not the context-labelled name followed by `and`. After the focused regression/fix, detector plus sensitive workflow tests passed. | Current local source protects this supported context-name form. Earlier run `5dc8237648c148c182c1d96585d53e65` should not be treated as current-source proof. |
| Local server control | The open browser can reach the app, but this shell's health request and listener query did not reveal the backend. | Do not start a second server on port 8000; the active browser service remains outside this shell's control. |

The existing project key was authorized by the user for this synthetic project rehearsal and must not be read or printed. The user plans to revoke it after the project. Do not copy it into prompts, terminal output, browser state, or this file.

**Exact next action:** restart the existing API process from the project checkout so it loads the bounded retry configuration. Use only a synthetic message with `TICKET-DEMO-1042` and synthetic PII. Follow the same-run workflow and verify Gemini mode, tokenized prompt, validated lookup, egress success, exact protected helpdesk receipt, protected model context, trusted local restoration, and final answer. Do not claim success unless every stage is visible in that same run. The invalid-ticket case is already browser-verified. Never reuse the user's latest entered message in another request.

**Known verification limits:** after the retry regression passed, `pytest --last-failed` had no remembered failures, selected all 73 tests, and stalled at `tests/test_demo_ui.py`; the full Python suite is not verified. The focused Gemini adapter tests pass (**10/10**). Frontend tests pass (**15/15**) and `npm run build` passes. PII coverage remains limited to selected recognizers. A successful live synthetic Gemini path with the retry change must still be observed.

### Earlier implementation checkpoints

- The chat UI was simplified to one message field after the user asked to remove separate contact details. The workflow UI was then redesigned around six persistent nodes, animated arrows connecting each step, restrained color differences, and a dark dotted background, following the user's GIF reference.
- A successful browser rehearsal on 2026-10-09 showed a same-run six-step deterministic trace for the then-tested contact values. It does not verify the newer identifier patterns or Gemini mode.
- Gemini adapter, fake-client flow, server mode validation, run-mode evidence, and UI presentation are already implemented. Read [gemini-privacy-implementation-plan.md](gemini-privacy-implementation-plan.md) for the feature plan and [implementation-plan.md](implementation-plan.md) for broader project rationale; this snapshot is the source of truth for status.

## Project origin and decisions

### Original problem

The hackathon brief shared by the user (Moodlakatte Institute of Technology, Department of CSE) asks for middleware that intercepts agent-to-tool payloads, detects selected PII in text and structured data, replaces values with reversible tokens, blocks leakage, restores values in trusted responses, and demonstrates detection, leakage prevention, restoration, and processing time. The challenge's fairness note requires synthetic personal data only.

### Product purpose

**Veil** is a privacy firewall for local agent tool calls. The judging story is: “The agent can work with a tool while Veil controls which sensitive values cross the tool boundary, and the audience can inspect what the tool actually received.” The prototype is designed for a 24-hour hackathon and should be easy to run and explain.

### Decisions made with the user

1. Keep deterministic offline mode as default. Gemini is an opt-in networked agent mode using synthetic data only; all tools remain simulated and local, with no external telemetry.
2. Keep three real workflow components: user-facing local agent, Veil middleware/gateway, and offline simulated helpdesk. A polished UI alone is not the deliverable; the Python request/response path is the MVP.
3. Provide two coordinated user surfaces: a simple chat page for sending a request and seeing the agent's answer, and a separate visual workflow page that proves how that exact run moved through the system.
4. The React page accepts one free-form synthetic ticket message and has no separate contact fields. Its API accepts only the seeded local ticket `TICKET-DEMO-1042`. Gemini receives only locally tokenized selected values and can propose only the ticket lookup; the legacy Streamlit fallback stays deterministic. Automatic detection covers selected patterns and is not universal.
5. The workflow view should be visual-first. The user provided a three-exhibit comparison image as inspiration only and explicitly said not to copy it. They requested connected circular nodes, with each node showing the message/payload and what that stage did. The implementation uses a distinctive six-step timeline rather than the image's exhibit-card layout.
6. Keep the existing Streamlit demo as a fallback while the React path is rehearsed. The React frontend and the Streamlit fallback use the same Python workflow code; the React UI calls the FastAPI run API.
7. Preserve test-first development for behavioral changes. Keep `context.md` updated after meaningful steps. Explain instructions simply and give concrete Windows/PowerShell commands.

## How the application works

```text
User in React chat
  → POST /api/runs (one run_id)
  → FastAPI worker selects the configured offline or Gemini agent
  → Gemini receives a locally tokenized prompt when Gemini mode is enabled
  → agent proposes one validated ticket lookup for the known local ticket
  → Veil detects and tokenizes selected values
  → egress verifier checks the tool-bound payload; unsafe/error paths stop here
  → offline helpdesk captures the exact received payload and returns a tokenized reply
  → Veil restores known values for the trusted local path
  → Gemini mode drafts from tokenized tool context; Veil restores known tokens locally
  → answer is shown in chat
  → workflow page reads/replays this same run's events and artifacts
```

The React API validates that a request names a known local ticket before queueing. The current accepted ticket is `TICKET-DEMO-1042`, shaped as `TICKET-{CATEGORY}-{4 DIGITS}`. Gemini mode is selected with backend environment variables only and uses the real Gemini agent to propose the allowlisted ticket lookup. The simulated helpdesk stays local. Its captured payload is the ground truth for what left the Veil boundary.

### API and run storage

- `GET /health` — local API health.
- `POST /api/runs` — accepts the message-only React request, returns the selected agent mode, creates one run ID, and schedules the workflow. Gemini mode requires a backend `GEMINI_API_KEY`; the key is never accepted by the browser.
- `GET /api/runs/{run_id}` — returns that run's status, ordered events, artifacts, tool payload/response, restored response, answer, and audit summary.
- `GET /api/runs/{run_id}/events` — replayable Server-Sent Events stream; numeric event IDs and `Last-Event-ID` support reconnect.
- Existing `/tool-call` endpoint and Streamlit application remain in the codebase; do not route the judge flow around `VeilGateway`.

Run records are held in a process-local, thread-safe store, capped at 100 runs, and terminal records expire after 15 minutes. A server restart clears them, and separate backend worker processes would not share them. The token vault is task-scoped and is not kept in the run store. Workflow evidence intentionally includes the synthetic original request for the local judge view; do not log raw PII or ever encourage entry of real data.

## Privacy scope and failure cases

- Recognizers cover selected email, phone, synthetic ID, contextual/person-name, labeled Aadhaar and bank-account, payment-card checksum, PAN, IFSC, and IBAN patterns. JSON objects/arrays are recursively scanned in the Python payload layer.
- Token strings are reversible **pseudonyms**, not encryption. The original-to-token map is held only for the active workflow and used to restore the trusted response.
- The gateway verifies the outgoing sanitized payload before calling the simulated tool and fails closed on residual detections or processing/tool errors. A blocked trace must not show a helpdesk receipt or fabricate a response.
- Name detection is the least reliable recognizer. Unknown secrets, ambiguous numbers, other languages, image/audio content, and obfuscation may be missed. A user-supplied exact value can cover an unsupported secret only where that feature is exposed.
- Do not describe Veil as a universal PII detector, as cryptographic encryption, or as production security. A real tool that needs the original value requires a trusted service boundary; a token alone cannot let an external system act on the hidden value.
- Keep all examples synthetic. Avoid putting raw values in logs, error details, test output, screenshots intended for public use, or external requests.

## Repository map

- `veil/detection.py`, `payload.py`, `token_vault.py` — local detection, recursive payload handling, and per-run reversible tokens.
- `veil/gateway.py` — mandatory sanitize/verify/tool/restore boundary and audit metadata.
- `veil/demo_agent.py`, `veil/gemini_agent.py`, `demo_flow.py`, `helpdesk.py`, `mock_tool.py` — offline and Gemini adapters, orchestration/events, and simulated tools.
- `veil/api.py`, `run_registry.py` — FastAPI endpoints, worker orchestration, bounded run history, replayable SSE.
- `veil/demo.py` — Streamlit fallback using the same workflow.
- `frontend/src/pages/ChatPage.tsx` — request form and actual agent answer.
- `frontend/src/pages/WorkflowPage.tsx` — connected six-node evidence timeline, Motion animation, run replay.
- `frontend/src/api.ts`, `App.tsx`, `styles.css` — backend client, routes, and visual styles.
- `tests/` — Python unit/integration/API and Streamlit tests.
- `frontend/src/**/*.test.ts(x)` — React/API/UI behavior tests.
- `data/benchmark.json`, `benchmark-results.md` — synthetic benchmark corpus and a historical run snapshot. Re-run before presenting fresh benchmark metrics.
- `README.md` — user-facing overview, demo script, and original Streamlit instructions.
- `implementation-plan.md` — detailed project history and staged plan. Consult it for rationale/checklists, but use this file for actual present status.

### Important visual implementation detail

`implementation-plan.md` originally proposed React Flow (`@xyflow/react`). The implemented workflow view instead uses a semantic ordered list, CSS connector rail, circular status markers, and Motion animations. `@xyflow/react` remains in `frontend/package.json` but is not needed by the current component. This is an intentional simpler responsive rendering of the user's requested connected-node visual. Do not migrate it to React Flow just to match the old plan. If a later visual redesign is proposed, inspect the current page and get the design right before implementing.

## Run locally on Windows

Use Node 20.19+ (or 22.12+); the verified workspace used Node 24.21.0/npm 11.19.0 and Python 3.12.14. From the repository root, open two PowerShell terminals.

**Terminal 1 — API:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn veil.api:app --host 127.0.0.1 --port 8000
```

If `.venv` already exists, skip the venv creation and dependency installation. If the Python launcher `py` is unavailable, install Python 3.12 and use `python -m venv .venv` once. Do not start a second backend if port 8000 is already in use; check `http://127.0.0.1:8000/health`.

**Terminal 2 — React UI:**

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`, submit a fully synthetic request, read the agent answer, then click **View animated workflow**. The Vite dev server proxies `/api` to `127.0.0.1:8000`. Deterministic mode needs no key or internet at runtime. Gemini mode needs a valid `GEMINI_API_KEY` in ignored `.env` and outbound access to Google's Gemini API; keep the simulated helpdesk local.

### Exact launch for the next Gemini rehearsal

Keep the current key only in ignored `.env`; do not print or copy it. The user plans to revoke it after the project. Stop the old API and Vite servers with Ctrl+C in their own terminal windows, then run these from the project checkout:

**API terminal:**

```powershell
$env:VEIL_AGENT_MODE = "gemini"
.\.venv\Scripts\python.exe -m uvicorn veil.api:app --host 127.0.0.1 --port 8000
```

**Frontend terminal:**

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/`. If a port is already in use, inspect the actual server terminal and stop only the stale project process; don't kill an unidentified process. Confirm the chat badge and the new workflow snapshot both report Gemini mode before treating the trace as current.

**Optional Streamlit fallback, in a third terminal from the repo root:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints, usually `http://127.0.0.1:8501`.

## Verification checkpoint

Most recent completed checks (2026-10-10):

- Focused Gemini/workflow/API/middleware subset, including the current SDK-range test — **59 passed, 1 deselected, 1 warning**; warning is Starlette's `httpx` TestClient deprecation.
- `google-genai` **2.29.0** is installed; `pip check` reports no broken installed requirements. `requirements.txt` allows versions `>=1.0,<3`, and the setup regression confirms the installed version is permitted.
- Current-source synthetic workflow — 10 selected PII categories detected; the protected tool payload had none of those detected values; restoration returned the test values; answer present. The intentional blocked run ended at egress with no helpdesk event or payload.
- Gemini client construction succeeded, but a real request with a safe prompt failed with `ConnectError`. This does not validate that the key is accepted and is not a live Gemini workflow pass.
- Fresh in-app-browser run `2a7c97b6a4b340909a1ed42baafc415a` showed an answer and same-run workflow, but the server reported deterministic mode and its old detector left some supported formats unprotected. Treat the browser service as stale, not as current-source verification.
- `pytest --last-failed -q` and a broad run excluding the known hanging UI/HTTP cases both stalled after 12 tests and were interrupted; this is not a full-suite pass.
- In `frontend/`, `npm test -- --run` — **12 passed across 4 files**.
- In `frontend/`, `npm run build` — **passed** (TypeScript and Vite production build).
- `.venv\Scripts\python.exe -m veil.evaluation` — **22/22 planted synthetic instances detected; 0 false positives; 0 original-value leakage; 22/22 token occurrences restored; p50 0.490 ms / p95 1.206 ms across 8 cases**. This small curated corpus does not demonstrate universal detection; see `benchmark-results.md`.
- `git diff --check` — clean after removing Markdown whitespace; Git may print a non-failing LF-to-CRLF warning for `veil/api.py`.
- Earlier browser rehearsal (2026-10-09) — run `f605001eaf4042ee9be47b460ac292ae` showed six connected steps on one synthetic workflow, but covered only the then-current contact patterns; see the fresh stale-server finding above.
- Uvicorn could not bind a new listener in this execution environment (`[WinError 10013]`); the already-open browser app's localhost service is not visible to this shell.

These results describe this working tree, not a clean clone. `uv` was unavailable in the prior shell, so tests used the project `.venv`; the user's supplied workflow instructions still prefer `uv` and request `uv run pytest --last-failed` after each change. If `uv` remains unavailable, use `.\.venv\Scripts\python.exe -m pytest --last-failed` and report the observed stall rather than claiming a complete suite. The frontend tests/build and benchmark numbers above are from earlier checkpoints; don't represent them as rerun during the latest backend change.

## Project history

This is the concise project history so a new session can continue without the original conversation:

1. The user shared the hackathon prompt and asked for an easy explanation, a free 24-hour MVP idea, and a winning demonstration concept. We chose Veil: local privacy middleware around agent-to-tool calls.
2. The user requested a persistent `context.md`, implementation plan, IDE prompts, checklists, and test-after-each-feature workflow. The project was built in Python using synthetic data only; paid APIs were excluded.
3. The core MVP added PII recognizers, recursive payload processing, reversible task-scoped tokens, gateway dispatch, egress checks, mock/simulated tools, response hydration, evaluation, and a Streamlit demonstration. Presidio/spaCy was not made a required dependency because the available environment blocked its native extension.
4. The user asked for an agent and helpdesk tool, not just a privacy dashboard. The app gained a deterministic local agent and a request-driven helpdesk scenario. It supports ticket lookup and general support intake, with synthetic contact data and a blocked-path example.
5. The user clarified they wanted two UIs: a simple place to message the agent and a visually rich separate workflow page over the exact same run. We selected React + TypeScript + Vite for those pages and retained the Streamlit screen as fallback. FastAPI exposes run creation, snapshots, and SSE events.
6. The user requested animated circular nodes that show each stage's message and action, especially Veil protection and the actual tool-bound data. A reference exhibit table was supplied as inspiration only. The final six-node timeline makes the real artifacts visible, highlights token strings, shows helpdesk capture and trusted restoration, and handles blocked egress visibly.
7. At the 2026-10-09 checkpoint, a synthetic deterministic browser rehearsal showed the same run across chat and workflow. The latest 2026-10-10 check found that the currently open browser backend is stale and leaves some supported formats unprotected; consult the exact current checkpoint above before relying on any older rehearsal. The live Gemini and clean-clone/judging-machine rehearsals remain unverified.

## Agent workflow and user preferences

- Start by reading `context.md`, `implementation-plan.md`, `README.md`, and any actual `AGENTS.md`/IDE instruction files. Confirm current files/state before editing.
- The user expects plain-language explanations and practical steps. The user's main criterion is a working and judge-understandable workflow; visual polish supports that demonstration.
- Before proposing or implementing a feature, stress-test the idea against the settled requirements: same workflow run on both pages, real event/artifact evidence, local simulated helpdesk, Gemini only for user-authorized synthetic prompts, clear blocked path, and data protection. Ask only if an unresolved choice materially changes the implementation.
- For behavior/code changes, write a focused test first, observe the expected failure, implement the smallest vertical slice, then run focused checks and the full relevant suite. After each change, update this file with what passed and the next action.
- The user-provided project instructions require a stress-test of the plan before implementation (`$grill-me`/the available grilling skill), TDD for feature work, Python 3.12+, Pydantic v2, and `uv run pytest --last-failed` after every change. `uv` was unavailable in the prior environment; use `.\.venv\Scripts\python.exe -m pytest ...` as the documented fallback and record when a suite stalls.
- Gemini mode is an approved exception to the previous local-only plan: use only synthetic data, locally tokenize before model calls, and keep its key in backend-only ignored configuration. Do not send real personal or confidential data. Do not output raw synthetic contact values unnecessarily.
- Keep existing work. The checkout currently contains uncommitted and untracked implementation files. Inspect `git status` and diffs before editing; never reset/clean them as a shortcut.
- Do not claim the human browser rehearsal, clean-clone install, or fresh benchmark passed unless actually completed.

### Suggested skills for an incoming agent

- Use the TDD skill for any application behavior or bug fix.
- Use systematic debugging for an observed broken run or integration issue.
- Use verification-before-completion before claiming a change or check is complete.
- Use writing-for-agents when changing this handoff or other instructions.
- Use plan/execution skills only if the next work grows beyond the single browser-rehearsal step.

## Ready-to-paste first prompt for a new IDE or chat

```text
We are continuing the existing Veil hackathon project. Start by reading `context.md`, `implementation-plan.md`, `README.md`, and any actual `AGENTS.md` instructions. The `Handoff snapshot — exact stop point` in `context.md` is authoritative; older checkpoints are history. Inspect `git status` and preserve every existing change. Do not rebuild the MVP or clean/reset the tree.

The current task is to complete a successful fresh browser rehearsal of the Gemini agent path after ticket-only intake validation. The React chat (`/`) and six-step CSS/SVG + Motion workflow page (`/runs/{run_id}`) must show evidence from the same run. The app already includes a deterministic offline agent, Gemini adapter, FastAPI replayable SSE API, Veil detector/token vault/gateway, local simulated helpdesk, response restoration, Streamlit fallback, and tests. React Flow was an earlier proposal; do not migrate the current workflow page to it.

Exact stop point: the browser now rejects unknown `TICKET-1000` and explains that the only valid local ticket is `TICKET-DEMO-1042`. A valid synthetic request (`19757909a6b94fe4956e901053486356`) showed Gemini mode and tokenized synthetic name/email in Gemini's prompt, but Gemini returned `ServerError` before proposing a tool call; no helpdesk receipt or final answer exists for this run. A name regex regression for a name followed by “and” was fixed test-first. Focused Python/frontend tests and the frontend build pass; `pytest --last-failed` selected 72 tests and stalled at `tests/test_demo_ui.py`, so the full suite is not verified. The shell cannot see the running browser backend, so do not start a duplicate listener. Read the latest results and blockers in `context.md` before acting.

The ticket-only intake rule is implemented and browser-verified. Continue the live Gemini rehearsal with a valid `TICKET-DEMO-1042` request containing synthetic selected-pattern data. The latest valid run tokenized the synthetic name/email but Gemini returned `ServerError` before proposing a tool call. The user has supplied a replacement key; it is not recorded here. Restart the API from the user's project terminal so it loads that replacement from ignored `.env`, then retry. Verify one run shows Gemini mode, tokenized model input, validated lookup proposal, successful egress, exact protected helpdesk receipt, protected model context, trusted local restoration, and final answer. Do not claim success unless every stage is visible in that same run. The invalid-ticket case is already browser-verified.

Use only synthetic data. The user has authorized Gemini network requests for synthetic prompts; the simulated helpdesk remains local. Never print or paste the API key, log raw PII, or send real personal/confidential data. Detection is selected-pattern and limited; tokens are reversible pseudonyms, not encryption. User-provided workflow rules: stress-test a plan before implementation (`$grill-me`/available grilling skill), use TDD for feature work, use `uv` for dependency commands and `pytest`; after a change run `uv run pytest --last-failed`. In the last environment `uv` was unavailable, so use `.\.venv\Scripts\python.exe -m pytest` and report any hang rather than claiming the full suite passed. Keep explanations concise and give exact Windows/PowerShell commands when useful.
```
