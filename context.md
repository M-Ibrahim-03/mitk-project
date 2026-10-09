# Veil — Project Context and Agent Handoff

Last verified: 2026-10-09
Project root: `mitk-project`
Status: Working local Python workflow + React chat page + animated workflow evidence page. The next task is a human browser rehearsal and any small fixes it uncovers.

> **Start here when opening this repository in another IDE, agent, or chat.** Read this file first, then `implementation-plan.md` and `README.md`. Treat this file's **Current state** and **Next action** as the freshest checkpoint. The plan preserves the original design and implementation sequence; some early Phase 7 paragraphs describe React Flow as the intended graph, while the implemented page uses an accessible CSS-connected node timeline plus Motion. Do not rebuild already working features because a plan paragraph is historical.

## Quick handoff

Veil is a local-only hackathon prototype of middleware between an AI agent and a tool. A user submits a synthetic helpdesk message to a deterministic local agent. The agent prepares a tool request. Veil detects selected sensitive values, replaces them with temporary reversible tokens, checks the exact outgoing request, and only then passes it to an offline simulated helpdesk. Veil restores known tokens on the trusted response path, and the agent returns an answer. The React chat and workflow pages share the same backend run; the workflow page displays the actual recorded payload at each stage so judges can see what the tool received.

The Python workflow, API, React pages, and tests are already implemented. Keep the middleware and local simulated tool as the core of the project; the UI is evidence of that workflow. Do not recreate the MVP, add an external LLM/tool, or replace the tested privacy path.

## Current state and next action

- **Completed:** pure-Python PII detection and tokenization; recursive JSON/text support; `VeilGateway`; fail-closed egress check; offline helpdesk; deterministic agent; ticket lookup and general support-intake paths; response restoration; synthetic benchmark; Streamlit fallback; FastAPI run API with bounded in-memory run history and replayable SSE; React chat route `/`; React workflow route `/runs/:runId`.
- **Workflow visualization:** six connected circle-led steps show the original user message, agent's prepared tool request, Veil's protected outgoing payload and egress result, the exact payload captured by the helpdesk and its tokenized reply, Veil's restored response, and the agent's final answer. Tokens are highlighted. A blocked run stops at Veil and marks later tool stages as not reached. Motion respects reduced-motion preferences. Actual backend events are replayed at a readable display pace; the backend is not artificially slowed.
- **Recent local acceptance check:** a synthetic API run completed with 14 events; audit reported 3 protected values; the helpdesk payload did not contain the planted email; the agent returned an answer. Frontend returned HTTP 200 and backend `/health` returned `ok`. The live workflow view was opened in the Codex browser panel. This confirms the service/data path, but not a person-reviewed visual click-through.
- **Next action:** open `/` in the local browser, submit a synthetic message, confirm the answer appears, follow **View animated workflow**, and verify that it shows the very same run and clear per-node proof. Fix any visual or integration issue found, test-first, then update this file with exact results. The current page/run ID may have expired; create a fresh run from the chat page.
- **Current limits:** no clean-clone setup rehearsal has been recorded; browser automation with Edge failed in the sandbox due to browser profile/temp-folder permissions. Do not claim full browser acceptance until the human click-through succeeds. PII recognition is limited and is not guaranteed for arbitrary unknown or obfuscated secrets.

## Project origin and decisions

### Original problem

The hackathon brief shared by the user (Moodlakatte Institute of Technology, Department of CSE) asks for middleware that intercepts agent-to-tool payloads, detects selected PII in text and structured data, replaces values with reversible tokens, blocks leakage, restores values in trusted responses, and demonstrates detection, leakage prevention, restoration, and processing time. The challenge's fairness note requires synthetic personal data only.

### Product purpose

**Veil** is a privacy firewall for local agent tool calls. The judging story is: “The agent can work with a tool while Veil controls which sensitive values cross the tool boundary, and the audience can inspect what the tool actually received.” The prototype is designed for a 24-hour hackathon and should be easy to run and explain.

### Decisions made with the user

1. Keep the complete demonstration local and deterministic. Do not use a paid model, hosted LLM, external tool, cloud service, or external telemetry.
2. Keep three real workflow components: user-facing local agent, Veil middleware/gateway, and offline simulated helpdesk. A polished UI alone is not the deliverable; the Python request/response path is the MVP.
3. Provide two coordinated user surfaces: a simple chat page for sending a request and seeing the agent's answer, and a separate visual workflow page that proves how that exact run moved through the system.
4. The user may type a free-form synthetic prompt and supply synthetic contact fields. Current automatic detection is limited to selected patterns. Users can explicitly list exact synthetic values in the legacy Streamlit flow when needed; do not imply that the React UI detects every possible secret.
5. The workflow view should be visual-first. The user provided a three-exhibit comparison image as inspiration only and explicitly said not to copy it. They requested connected circular nodes, with each node showing the message/payload and what that stage did. The implementation uses a distinctive six-step timeline rather than the image's exhibit-card layout.
6. Keep the existing Streamlit demo as a fallback while the React path is rehearsed. The React frontend and the Streamlit fallback use the same Python workflow code; the React UI calls the FastAPI run API.
7. Preserve test-first development for behavioral changes. Keep `context.md` updated after meaningful steps. Explain instructions simply and give concrete Windows/PowerShell commands.

## How the application works

```text
User in React chat
  → POST /api/runs (one run_id)
  → FastAPI worker runs the local agent + VeilGateway + simulated helpdesk
  → agent prepares ticket lookup or support-intake call
  → Veil detects and tokenizes selected values
  → egress verifier checks the tool-bound payload; unsafe/error paths stop here
  → offline helpdesk captures the exact received payload and returns a tokenized reply
  → Veil restores known values on the trusted path back to the agent
  → agent creates the answer shown in chat
  → workflow page reads/replays this same run's events and artifacts
```

The deterministic agent selects ticket lookup when it finds a supported `TICKET-...` value; otherwise it submits a general support request. It is intentionally not a hosted AI model. Both tools are simulated locally. The helpdesk capture is the ground truth for what left the Veil boundary.

### API and run storage

- `GET /health` — local API health.
- `POST /api/runs` — accepts one message and requester fields, creates one run ID, and schedules the existing workflow.
- `GET /api/runs/{run_id}` — returns that run's status, ordered events, artifacts, tool payload/response, restored response, answer, and audit summary.
- `GET /api/runs/{run_id}/events` — replayable Server-Sent Events stream; numeric event IDs and `Last-Event-ID` support reconnect.
- Existing `/tool-call` endpoint and Streamlit application remain in the codebase; do not route the judge flow around `VeilGateway`.

Run records are held in a process-local, thread-safe store, capped at 100 runs, and terminal records expire after 15 minutes. A server restart clears them, and separate backend worker processes would not share them. The token vault is task-scoped and is not kept in the run store. Workflow evidence intentionally includes the synthetic original request for the local judge view; do not log raw PII or ever encourage entry of real data.

## Privacy scope and failure cases

- Baseline recognizers cover selected email, phone, synthetic ID, contextual/person-name patterns, and explicit exact custom values in flows that accept them. JSON objects/arrays are recursively scanned in the Python payload layer.
- Token strings are reversible **pseudonyms**, not encryption. The original-to-token map is held only for the active workflow and used to restore the trusted response.
- The gateway verifies the outgoing sanitized payload before calling the simulated tool and fails closed on residual detections or processing/tool errors. A blocked trace must not show a helpdesk receipt or fabricate a response.
- Name detection is the least reliable recognizer. Unknown secrets, ambiguous numbers, other languages, image/audio content, and obfuscation may be missed. A user-supplied exact value can cover an unsupported secret only where that feature is exposed.
- Do not describe Veil as a universal PII detector, as cryptographic encryption, or as production security. A real tool that needs the original value requires a trusted service boundary; a token alone cannot let an external system act on the hidden value.
- Keep all examples synthetic. Avoid putting raw values in logs, error details, test output, screenshots intended for public use, or external requests.

## Repository map

- `veil/detection.py`, `payload.py`, `token_vault.py` — local detection, recursive payload handling, and per-run reversible tokens.
- `veil/gateway.py` — mandatory sanitize/verify/tool/restore boundary and audit metadata.
- `veil/demo_agent.py`, `demo_flow.py`, `helpdesk.py`, `mock_tool.py` — deterministic agent, workflow orchestration/events, simulated helpdesk/tools.
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
.\.venv\Scripts\python.exe -m uvicorn veil.api:app --host 127.0.0.1 --port 8000 --reload
```

If `.venv` already exists, skip the venv creation and dependency installation. If the Python launcher `py` is unavailable, install Python 3.12 and use `python -m venv .venv` once. Do not start a second backend if port 8000 is already in use; check `http://127.0.0.1:8000/health`.

**Terminal 2 — React UI:**

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`, submit a fully synthetic request, read the agent answer, then click **View animated workflow**. The Vite dev server proxies `/api` to `127.0.0.1:8000`. No API keys or internet service are needed at runtime; npm dependency installation may need package access on a clean machine.

**Optional Streamlit fallback, in a third terminal from the repo root:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints, usually `http://127.0.0.1:8501`.

## Verification checkpoint

Most recent checks after the handoff update:

- `.venv\Scripts\python.exe -m pytest --last-failed` — **44 passed, 1 warning**; the warning is Starlette's deprecation notice about `httpx` in `TestClient`.
- In `frontend/`, `npm test -- --run` — **9 passed across 4 files**.
- In `frontend/`, `npm run build` — **passed** (TypeScript and Vite production build).
- `git diff --check` — clean after removing Markdown whitespace; Git may print a non-failing LF-to-CRLF warning for `veil/api.py`.
- Local integration rehearsal — frontend HTTP 200, API health `ok`, one synthetic run completed, the test email was absent from captured helpdesk payload, and the local agent answered.

These checks were run in the current working environment; no claim is made that a fresh clone has been tested. `uv run pytest --last-failed` was attempted after this update but failed because `uv` is not installed (`uv` is not recognized by PowerShell); the `.venv` interpreter fallback above passed. The user previously reported the same problem on a cloned machine and explicitly asked for a direct Python environment workflow, while the user-provided agent instructions request `uv`. Inspect the active IDE instructions and available tools in the new environment; use the verified `.venv` command here when `uv` is unavailable.

## Project history

This is the concise project history so a new session can continue without the original conversation:

1. The user shared the hackathon prompt and asked for an easy explanation, a free 24-hour MVP idea, and a winning demonstration concept. We chose Veil: local privacy middleware around agent-to-tool calls.
2. The user requested a persistent `context.md`, implementation plan, IDE prompts, checklists, and test-after-each-feature workflow. The project was built in Python using synthetic data only; paid APIs were excluded.
3. The core MVP added PII recognizers, recursive payload processing, reversible task-scoped tokens, gateway dispatch, egress checks, mock/simulated tools, response hydration, evaluation, and a Streamlit demonstration. Presidio/spaCy was not made a required dependency because the available environment blocked its native extension.
4. The user asked for an agent and helpdesk tool, not just a privacy dashboard. The app gained a deterministic local agent and a request-driven helpdesk scenario. It supports ticket lookup and general support intake, with synthetic contact data and a blocked-path example.
5. The user clarified they wanted two UIs: a simple place to message the agent and a visually rich separate workflow page over the exact same run. We selected React + TypeScript + Vite for those pages and retained the Streamlit screen as fallback. FastAPI exposes run creation, snapshots, and SSE events.
6. The user requested animated circular nodes that show each stage's message and action, especially Veil protection and the actual tool-bound data. A reference exhibit table was supplied as inspiration only. The final six-node timeline makes the real artifacts visible, highlights token strings, shows helpdesk capture and trusted restoration, and handles blocked egress visibly.
7. Current implementation is in place and automated checks pass. A local synthetic run verified API-to-tool leakage prevention; the outstanding handoff is a human visual rehearsal from chat submission through the same run's workflow page.

## Agent workflow and user preferences

- Start by reading `context.md`, `implementation-plan.md`, `README.md`, and any actual `AGENTS.md`/IDE instruction files. Confirm current files/state before editing.
- The user expects plain-language explanations and practical steps. The user's main criterion is a working and judge-understandable workflow; visual polish supports that demonstration.
- Before proposing or implementing a feature, stress-test the idea against the already-settled requirements: same workflow run on both pages, real event/artifact evidence, local-only behavior, clear blocked path, and data protection. Ask only if an unresolved choice materially changes the implementation.
- For behavior/code changes, write a focused test first, observe the expected failure, implement the smallest vertical slice, then run focused checks and the full relevant suite. After each change, update this file with what passed and the next action.
- Do not use external APIs or send payloads to web services. Do not use real personal or confidential data. Do not output raw synthetic contact values unnecessarily.
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
We are continuing the existing Veil hackathon project. First read context.md, implementation-plan.md, README.md, and any actual AGENTS.md instructions. Treat context.md's Current state and Next action as the live checkpoint; do not recreate the MVP or blindly follow an older plan section. Inspect git status and preserve all existing modifications.

The goal is a local-only demo: synthetic user message → deterministic local agent → Veil middleware/tokenization and fail-closed egress check → offline simulated helpdesk → trusted response restoration → agent answer. The React chat page and animated workflow page must represent the same backend run. The workflow page uses six connected circle-led steps and must show actual per-stage evidence, especially Veil's protected payload and the exact payload the helpdesk received. Motion is used for animation; the current graph is a responsive CSS-connected semantic timeline, not React Flow.

The Python workflow, FastAPI run API/SSE, React chat and evidence pages, Streamlit fallback, and tests already exist. The next task is the human browser rehearsal documented in context.md: run/open the local API and frontend, submit synthetic text from `/`, verify the answer, open that run's workflow page, and confirm that node contents and token/leak proof are understandable. The old run ID may have expired, so create a fresh run. If you find a defect, report the smallest useful fix, add a regression test first, implement it, run the relevant tests/build, and update context.md with exact results and next action.

Use synthetic data only. Keep all processing local; no hosted LLM, outside tool, external telemetry, or network submission of user data. Do not put raw PII in logs. Tokens are reversible pseudonyms, not encryption, and detection is limited rather than universal. Explain steps in simple terms and give exact Windows/PowerShell commands when useful.
```
