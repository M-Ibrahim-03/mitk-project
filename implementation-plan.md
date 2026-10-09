# Veil MVP — Implementation Plan and AI IDE Prompts

Read `context.md` first. It is the source of truth for scope, constraints, architecture, status, and decisions. This plan provides the staged prompts and checklists.

## Authoritative next direction: two coordinated screens

The user-facing product now has **two distinct pages over one real workflow run**. This section is the authoritative next implementation target. The previous Streamlit single-screen implementation remains a working fallback while the new path is built; do not rewrite or remove it until the new end-to-end path passes.

### Decision and options considered

| Option | What it would mean | Decision |
| --- | --- | --- |
| Keep everything in Streamlit | Make two Streamlit pages and share Streamlit session state. | Not selected. It keeps the existing UI framework, but makes a polished interactive node graph and a separately openable live viewer harder to build and test. |
| Keep Streamlit chat and add a separate React viewer | Run two frontends, add browser-to-browser coordination and CORS concerns. | Not selected. It splits the user's interaction and proof across different UI systems. |
| **React single-page app with two routes + existing FastAPI/Python workflow** | Chat at `/`; workflow viewer at `/runs/{runId}`; both attach to one local API run. | **Selected.** It gives the visualizer a real graph UI while preserving the tested Python privacy gateway and gives both pages one source of truth. |
| Rewrite the privacy gateway in JavaScript | Replace Python middleware and tool flow as well as the UI. | Not selected. It adds unnecessary security-critical porting work and discards tested behavior. |

The selected frontend stack is **React + TypeScript + Vite**, **React Router** for the two routes, **`@xyflow/react` (React Flow)** for the connected node graph, **Motion for React (`motion`)** for node transitions and restrained status animation, **Vitest + React Testing Library** for UI tests, and **Playwright** for the judge-flow browser test. React Flow edges support an animated state, and its node model supports custom node UIs; Motion supplies React-native animation and reduced-motion support. See the official [React Flow edge API](https://reactflow.dev/api-reference/types/edge), [Motion for React docs](https://motion.dev/docs/react), and [Motion reduced-motion hook](https://motion.dev/docs/react-use-reduced-motion). These packages are free to use for this local prototype; no paid API or hosted animation service is required.

This means the two judge-facing pages will both be React routes, while the existing Streamlit workflow remains a fallback during the transition. The chat route itself stays simple; React is used there to make the run handoff reliable, and React Flow/Motion are used primarily on the separate visual route. Both routes call the same FastAPI backend.

Keep the backend **Python 3.12 + FastAPI + the current `VeilGateway`, `run_ticket_demo`, simulated helpdesk, and pytest suite**. Use FastAPI's `EventSourceResponse` and `ServerSentEvent` for event delivery with event IDs and replay via `Last-Event-ID`; the official support was added in FastAPI 0.135, so update the minimum FastAPI requirement if the implementation uses this API. See [FastAPI Server-Sent Events](https://fastapi.tiangolo.com/tutorial/server-sent-events/). Vite's current guide requires Node 20.19+ or 22.12+, so use Node 22.12+ on the Windows judging machine and npm. See [Vite's setup guide](https://vite.dev/guide/).

### Product contract

1. **Chat page (`/`)** is the clean user surface: synthetic-only notice, one message box, one **Send** button, conversation, and the local agent's final answer. It has no separate contact or custom-secret fields and does not display internal JSON by default. Veil checks selected patterns in the message before dispatch; the notice must state that detection is limited. A ticket ID continues to select the existing ticket lookup; other text uses the existing support-intake path.
2. A send creates **one** run through `POST /api/runs`. The API returns one `run_id` immediately and starts the existing Python flow once. The chat page subscribes to that run and shows the final answer only when the actual agent-answer event arrives.
3. In the same user gesture, the chat submit action opens the workflow page in another tab and points it to `/runs/{run_id}`. Pre-open the tab synchronously on click to avoid popup blockers; after the API returns, navigate that tab to the run URL. If the browser blocks the tab, show an explicit “Open workflow view” link. The viewer never creates a second run.
4. **Workflow page (`/runs/{runId}`)** is the judge surface. It loads the current run snapshot, subscribes to its event stream, and draws the actual progression as animated nodes. If opened after completion or reloaded, it replays the stored event sequence for that same ID. The final answer shown on the chat page and the artifacts shown here must come from the same run record.
5. “Real-time” means the server publishes actual callbacks as the workflow executes and a viewer already open follows them. Since this deterministic local flow can finish faster than a human can watch, the viewer may animate the ordered, **recorded** events at a readable display pace after receiving them. This is presentation playback of real events, not fake backend work or fabricated success. Label completed history as replay when relevant; never add sleeps to `VeilGateway` or the helpdesk to make the demo look busy.

### Shared workflow and diagram

```text
Chat page ──POST once──> FastAPI run service ──> run_ticket_demo
   │                         │                        │
   │ answer from SSE         │ event history + SSE   ├─ local agent prepares call
   │                         │                        ├─ Veil detects/tokenizes
   └── opens /runs/{id} ─────┘                        ├─ egress gate verifies
                              │                        ├─ simulated helpdesk captures payload
                              │                        ├─ Veil restores trusted response
                              └── same run_id ───────> └─ agent creates final answer
```

The workflow canvas uses a fixed, judge-friendly topology with an outbound lane and a return lane:

```text
USER INPUT → LOCAL AGENT → VEIL SCAN/TOKENIZE → EGRESS GATE → SIMULATED HELPDESK
USER ANSWER ← LOCAL AGENT ← VEIL RESTORE      ← TOOL RESPONSE ←──────────────┘
```

Use custom React Flow nodes for **User input**, **Local agent**, **Veil middleware**, **Egress safety gate**, **Simulated helpdesk**, **Tokenized tool response**, **Veil restoration**, and **Agent answer**. Edges highlight only when events establish that information crossed that boundary. Clicking a node opens a readable detail panel: the user/agent input, detection types and counts, tokenized payload, the exact helpdesk capture, tokenized reply, restored reply, or final answer. The primary canvas shows short summaries, not giant JSON blocks. Make the canvas fit a 1366×768 judging screen and remain usable on narrower screens with zoom/pan and a stacked/scrollable fallback.

### API and run lifecycle contract

Add a focused run service/registry; keep endpoint functions in `veil/api.py` thin and preserve `/health` and `/tool-call`.

| Endpoint | Contract |
| --- | --- |
| `POST /api/runs` | Accept a validated `message`, optional structured requester details, optional exact synthetic `additional_sensitive_values`, and an explicit demo-only mode for the blocked example. Create a run exactly once, return `202` with `{run_id, status}`, and schedule the real workflow. Do not return a fabricated result. |
| `GET /api/runs/{run_id}` | Return status, last sequence number, ordered event snapshot, result receipt, and final answer if the corresponding stage actually happened. Unknown/expired ID returns `404`; it must not start another run. |
| `GET /api/runs/{run_id}/events` | Stream ordered SSE records. Every record has a numeric sequence/event ID, `run_id`, `stage`, `status`, plain-language message, server timestamp, and an optional allowlisted artifact. Support reconnect/replay from `Last-Event-ID`; close after a terminal event. |

Implement a `RunRegistry` (suggested `veil/run_registry.py`) with an in-memory `RunRecord`, monotonic event sequence numbers, an event history, subscriber queues, terminal status, and expiration. Add a narrow service (suggested `veil/run_service.py`) that invokes the existing `run_ticket_demo` once and publishes its actual `on_event` callback. Keep the existing workflow and gateway as the only business path; do not copy detection/tokenization into the API or React code.

The existing workflow is synchronous. Do not call it directly inside an `async def` route because it would block the event loop and stall the SSE page. Run it in a worker thread (`asyncio.to_thread`/Starlette threadpool), bridge each callback back onto the event loop with a thread-safe handoff, and publish the terminal result only after every callback is recorded. Keep event order stable even when the browser subscribes before, during, or after the worker finishes. A new subscriber first receives all records after its cursor, then live records; deduplicate by sequence if reconnect races produce repeats. Use one in-process worker/registry for the hackathon demo; explicitly document that run history is volatile and not shared between multiple server processes.

### Data handling and failure rules

- Bind both servers to loopback (`127.0.0.1`). Vite proxies `/api` to FastAPI in development; do not enable broad CORS when the proxy gives a same-origin browser path. The browser, chat page, API, and simulated tool remain on the judging machine. Do not add a hosted LLM, analytics, CDN runtime dependencies, external tool, or telemetry.
- Use synthetic examples only. The displayed input may show the synthetic values entered by the judge. The **tool proof must always use the deep copy captured by `SimulatedHelpdeskTool.received`**, never a reconstructed or pre-gateway payload.
- Store run snapshots/events in memory for a short configured TTL (for example 10 minutes) and cap both active runs and retained history. Expiration deletes the associated raw request/artifacts. Do not persist run data to JSON, SQLite, browser local storage, logs, or analytics. Never store the token vault or original-to-token mapping in the run registry.
- UI event artifacts must be explicitly allowlisted. Keep raw user input and agent-prepared request only for the local live visual story; mark them “before Veil.” For Veil/helpdesk stages show the sanitized payload actually dispatched, detections without original-value fields, actual tool reply with tokens, and the trusted restored reply. Render user strings as React text; do not use `dangerouslySetInnerHTML`.
- Avoid request-body logging and exception strings that could contain input. Bound request/message/extra-value length; sanitize validation errors so the server does not echo submitted values. Audit/run logs record run ID, stage, counts, and timing only. The demo's local UI is allowed to show synthetic input, but server logs must not.
- Fail closed: a blocked egress event marks helpdesk, tool response, restoration, and agent answer “not reached.” A helpdesk error cannot display a successful answer. A missing/expired run produces a clear recovery button back to chat, never a new implicit execution.
- Use careful claims: show that the helpdesk received no **recognized/planted protected values** for this run, based on its captured payload and configured ground truth. Do not say “all PII is protected”; automatic detection covers selected recognizers and user-listed exact values.
- Respect `prefers-reduced-motion` through Motion's reduced-motion support. Preserve keyboard navigation, accessible labels/live status text, readable contrast, and a non-animated status indicator.

### Phase 7 implementation sequence — tests before every behavior

Each task follows: add the test first; run it and record the expected failure; implement only that task; run its focused checks; then run `.venv\Scripts\python.exe -m pytest --last-failed` and `npm test -- --run` where the frontend exists. Fix all failures before proceeding. Never mark a later task started while an earlier gate is red. The estimates below total about 18 hours, leaving roughly 6 hours in the 24-hour window for environment issues, visual refinements, and judging-machine rehearsal.

#### 7.0 Environment and baseline (about 45 minutes)

1. Read `context.md`, this plan, and the repo before editing. Confirm the Python venv and existing 37-test baseline using `.venv\Scripts\python.exe -m pytest -q`.
2. Check `node --version` and `npm --version`; install Node 22.12+ if Vite's current requirement is not met. Confirm the install is only for open-source dependencies; no prompt or PII is sent to npm.
3. Sketch the actual current event artifacts from `veil/demo_flow.py` and `veil/gateway.py` so the API exposes real values, not display-only inventions. No app behavior change in this setup task.

**Gate:** existing Python tests pass; Node/npm versions are recorded; current workflow contract and event stages are understood.

#### 7.1 Scaffold the React app and route shells (about 1.5 hours)

1. Create `frontend/` with Vite React TypeScript, React Router, `@xyflow/react`, and `motion`; commit the npm lockfile. Add Vitest, React Testing Library, and Playwright as development dependencies.
2. Create routes `/` and `/runs/:runId`; add a branded but simple chat shell and a workflow canvas placeholder. Add a Vite `/api` proxy to `http://127.0.0.1:8000`.
3. Write route tests first: `/` is chat, a valid run URL is viewer, an invalid/missing ID renders a safe not-found state. No page may create a demo run merely by mounting.

**Files:** `frontend/package.json`, `package-lock.json`, `index.html`, `vite.config.ts`, `tsconfig*.json`, `src/main.tsx`, `src/App.tsx`, `src/pages/ChatPage.tsx`, `src/pages/WorkflowPage.tsx`, initial tests.

**Gate:** `npm test -- --run` and `npm run build` pass; routes never trigger a network run on mount.

#### 7.2 Define and test the run API and event shapes (about 2 hours)

1. Add Pydantic request/response models for `POST /api/runs`, run snapshots, and serialized events. Make a free-form message sufficient; requester details and exact additional secrets are optional.
2. Test request validation: empty/oversized message, oversized custom values, non-string values, and blocked-demo mode allowed values. Assert error responses contain no submitted sentinel values.
3. Test endpoint contracts through FastAPI `TestClient`/HTTPX: one run submission creates one ID; snapshot reports queued/running/terminal status; unknown/expired IDs return `404`; existing endpoints still work.
4. Test serialization of `WorkflowEvent` stages and artifacts, including dataclass records and nested dictionaries. Assert event metadata contains no original PII field and no token vault.
5. Add a regression test for a plain prompt with **no structured requester form**. Make requester details optional through `AgentRequest` and the agent/helpdesk payload contract; omit empty requester fields rather than inserting hidden synthetic values. The existing synthetic sample may still prefill optional name/email/phone fields.

**Files:** `veil/api.py`, proposed `veil/run_models.py`, `tests/test_run_api.py`, optional extensions to `tests/test_setup.py`.

**Gate:** API schema tests pass before any React component depends on it; no endpoint calls the helpdesk directly.

#### 7.3 Implement the in-memory registry, worker, and replayable SSE (about 3 hours)

1. Add tests in `tests/test_run_registry.py` for event IDs starting at one, stable order, two simultaneous subscribers, replay from zero and a later `Last-Event-ID`, subscribe-after-completion, terminal closing, TTL expiry, and capacity bounds.
2. Add a service test proving a run invokes `run_ticket_demo` exactly once, bridges callback events in source order, stores the terminal result after the last callback, and returns the same `run_id` in every event. Extend `run_ticket_demo` with an optional caller-supplied run ID (keeping its current generated default) so the API-created registry ID is the ID in the workflow events and visual-page URL.
3. Implement `RunRegistry` and `RunService`; worker-thread callbacks must publish safely into the event loop. Use the official FastAPI SSE types only after upgrading the minimum FastAPI version to one that supports them. Implement heartbeat comments only if needed by the browser/proxy; do not invent stage events.
4. Exercise the real helpdesk path in integration tests. Use a gated test dependency only to assert event-loop responsiveness and connection/replay races; keep the core privacy, tool capture, and restoration test on the real local components.

**Files:** `veil/run_registry.py`, `veil/run_service.py`, `veil/run_models.py`, `veil/api.py`, `requirements.txt`, `tests/test_run_registry.py`, `tests/test_run_api.py`.

**Gate:** an SSE client can subscribe before or after a real run and observe one ordered trace; reloading a page does not repeat the tool call; no event loop blocking; registry bounds and expiry pass.

#### 7.4 Connect the chat page to the one real run (about 2 hours)

1. Write tests for the API client and chat form before implementation. Submitting a message calls `POST /api/runs` once, uses its returned ID, opens/navigates the viewer tab from the click gesture, subscribes to that same ID, and displays the agent answer only after the `agent_response` event or completed snapshot.
2. The form has a prefilled synthetic example, one editable message, a clear **Send** action, and a “Synthetic data only / selected detectors are not universal” notice. Avoid separate structured PII or custom-secret fields. Preserve the use of a ticket ID for the known demo ticket and free-form support intake for other prompts.
3. Show calm states for sending, waiting, completed, blocked, failed, reconnecting, and missing/expired viewer; disable duplicate submit while a run is being created. Do not echo technical JSON or detector jargon in the chat by default.
4. If popup creation fails, preserve the chat run and reveal a link to `/runs/{runId}`; do not resubmit when the link is clicked.

**Files:** `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/pages/ChatPage.tsx`, `frontend/src/components/ChatComposer.tsx`, `frontend/src/components/Conversation.tsx`, tests.

**Gate:** UI test proves exactly one backend run/tool call and a final answer sourced from the same run. A second click cannot create a duplicate run while the first submission is pending.

#### 7.5 Build the animated graph from real events (about 3.5 hours)

1. Write reducer/mapping tests first: every current backend stage maps to a named node and edge; active/completed states follow event order; a blocked gate marks all downstream nodes not reached; failures stop at the real failure point; repeated sequence IDs are ignored.
2. Implement deterministic node positions and custom React Flow node types for the eight named stages. Lock user editing/dragging of graph connections; provide `fitView`, zoom controls, and readable details.
3. Use Motion for node entry, active-stage glow, status/checkmark transitions, token count changes, and optional packet movement along the current edge. Do not animate values changing from raw to token unless a real sanitization event contains the tokenized artifact. Prefer one coherent restrained motion system over continuous particle effects.
4. Buffer arriving event records and animate their visual states in sequence at a readable cadence; persist the full sequence in the page state so it can be replayed after navigation/reconnect. Do not delay the Python workflow to slow the judges' view. Provide a `Replay this run` control that only replays this run's stored events and does not call `POST /api/runs`.
5. Add a details drawer with sections for **What the user sent**, **What the agent prepared**, **What Veil sent**, **What the helpdesk actually received**, **What the helpdesk returned**, **What Veil restored**, and **What the agent answered**. Derive all sections from event/result artifacts. Hide unsafe/unreached sections on block.
6. Display the run receipt from actual result fields: egress allowed/blocked, detections, token count, helpdesk call count, restoration count, Veil latency, and total workflow latency. Qualify leakage claims to the planted/configured values in this run.

**Files:** `frontend/src/workflow/graph.ts`, `frontend/src/workflow/reducer.ts`, `frontend/src/components/WorkflowCanvas.tsx`, `frontend/src/components/nodes/*.tsx`, `frontend/src/components/RunDetails.tsx`, `frontend/src/components/RunReceipt.tsx`, styles and tests.

**Gate:** frontend tests cover success, blocked, failed, replay/reconnect, and reduced-motion behavior. The helpdesk card displays the exact captured request; it cannot use agent input or a fixture as a substitute.

#### 7.6 Prove both screens observe one run end to end (about 2.5 hours)

1. Add Playwright happy-path test using synthetic values: submit in chat, verify a second page uses the same `run_id`, follow event progression, inspect the captured helpdesk payload for tokenized contact/custom values, verify the tool response contains tokens, and verify Veil's restored response and the visible agent answer contain the right synthetic originals.
2. Add blocked-path browser test using the explicitly labeled demo-only fault mode: egress gate is blocked, the helpdesk is not reached, no tokenized tool response or agent answer is fabricated, and the receipt says zero calls because the captured call count is actually zero.
3. Add an API request counter or test spy only in test code to prove chat submit and viewer open/reload call `POST /api/runs` once total. Verify the visual page uses `GET`/SSE only.
4. Test SSE reconnect after a simulated disconnect and ensure sequence replay does not duplicate nodes or create another run.

**Files:** `frontend/e2e/workflow.spec.ts`, Playwright config, backend integration tests as needed.

**Gate:** `npm run e2e` and the complete Python suite pass; manual browser inspection confirms the two-page handoff is clear and the actual helpdesk receipt is visible without scrolling through raw JSON.

#### 7.7 Polish, launch instructions, and judging rehearsal (about 2.5 hours)

1. Add consistent typography, contrast, empty/loading/error states, responsive layout, accessibility labels, keyboard support, and reduced-motion handling. Keep the first page uncluttered and the second page visually distinctive.
2. Update `README.md` to make React chat the main entry point. One-time setup: create/activate the existing Python venv, install `requirements.txt`, `cd frontend`, run `npm ci`. Add exact VS Code terminal commands:

   ```powershell
   # Terminal 1, project root
   .\.venv\Scripts\python.exe -m uvicorn veil.api:app --reload --host 127.0.0.1 --port 8000

   # Terminal 2, project root
   cd frontend
   npm run dev -- --host 127.0.0.1
   ```

   Open the Vite URL shown in Terminal 2 (normally `http://127.0.0.1:5173`). Keep both terminals open. The Vite proxy sends `/api` requests to the local Python server. For a judging machine, run both commands in VS Code terminals on that machine; do not rely on a server started in a different Codex/remote process environment.
3. Keep `veil/demo.py` and its current tests as an available fallback until the React flow passes all gates. README should identify it as legacy/fallback only; do not make judges choose between it and the new primary flow.
4. Rehearse one free-form message, one ticket lookup, and the blocked example. Confirm the browser opens the second page, that both pages share a run, and that repeated refresh/replay does not create a second helpdesk call.
5. Run the synthetic evaluation CLI and preserve its limits. Record the browser, backend, frontend, and benchmark commands/results in `context.md` only after they were actually run.

**Gate:** the project starts from a fresh clone with no paid credentials; the user knows which local URL to open; both pages work on the judging computer; the Python and frontend suites pass; benchmark values are described as limited synthetic evidence.

### Phase 7 final acceptance checklist

- [ ] Chat page has a simple free-form message input and displays the actual local-agent answer.
- [ ] Sending creates one run and passes every agent-to-tool request through `VeilGateway`.
- [ ] Workflow opens as a genuinely separate page and uses the same run ID, events, snapshot, captured payload, and answer as the chat page.
- [ ] The visual graph uses `@xyflow/react` nodes/edges and Motion transitions driven by workflow event state; reduced-motion preference is honored.
- [ ] Live viewer receives events; late viewer/reload replays the recorded same run without dispatching a second tool call.
- [ ] The visualization shows the exact helpdesk-captured protected payload, tokenized response, restored response, and final agent answer.
- [ ] Blocked/failed paths accurately stop at their boundary and never display later stages as complete.
- [ ] Run records expire and remain in memory only; no vault is stored; raw values are absent from logs and never leave localhost.
- [ ] UI claims are limited to selected/planted synthetic values; detector limits are visible.
- [ ] Full Python tests, frontend unit/component tests, Playwright end-to-end checks, and manual VS Code launch rehearsal pass.

### Copy/paste prompts for each implementation step

Use the master prompt below, then append only one task prompt at a time. Do not let an IDE agent jump to the visualizer before the backend run API and replay contract pass.

#### Task 7.1 prompt — frontend shell

```text
Implement only Phase 7.1 in implementation-plan.md. First add Vitest/React Testing Library route tests and demonstrate they fail. Scaffold `frontend/` as React + TypeScript + Vite with React Router, `@xyflow/react`, and `motion`; create the `/` and `/runs/:runId` route shells and `/api` dev proxy. Mounting either route must not submit a workflow. Do not change Python workflow behavior yet. Run `npm test -- --run` and `npm run build`; report exact results. Keep the existing Streamlit app intact and update context.md with the next task.
```

#### Task 7.2 prompt — API contract and optional prompt-only agent input

```text
Implement only Phase 7.2. Add Python tests first for run request validation, response/event serialization, unknown IDs, existing endpoint compatibility, and a plain free-form message without structured requester fields. Then add typed Pydantic v2 run models and make requester details optional through the current agent/helpdesk contract without injecting hidden sample PII. Keep endpoint handlers thin and do not yet add the concurrent run worker or UI integration. Verify validation responses never echo a synthetic sentinel value. Run focused pytest, then `.venv\Scripts\python.exe -m pytest --last-failed`; report the exact outputs and update context.md.
```

#### Task 7.3 prompt — registry, worker, and SSE

```text
Implement only Phase 7.3. First write failing tests for event sequence/order, multiple subscribers, `Last-Event-ID` replay, reconnect, subscribe-after-completion, terminal close, expiry/capacity, one workflow call per run, matching API/workflow/event run IDs, and event-loop responsiveness. Then implement the in-memory RunRegistry and RunService. Execute the existing synchronous run_ticket_demo in a worker thread; bridge its real callbacks to the event loop without reordering; pass the registry's run ID into run_ticket_demo while preserving its standalone generated-ID default. Use FastAPI's native SSE types only if requirements.txt is upgraded to FastAPI 0.135+. Do not add fake stage events or persist raw input. Run focused tests and `.venv\Scripts\python.exe -m pytest --last-failed`; update context.md.
```

#### Task 7.4 prompt — chat page

```text
Implement only Phase 7.4. Add frontend tests first proving one chat submission makes exactly one POST to `/api/runs`, uses the returned run ID for the workflow page, subscribes to that run, and displays the agent answer only when the real answer is present. Then build the uncluttered synthetic-only chat form, optional exact-values field, conversation, waiting/error states, duplicate-submit guard, and popup-blocked fallback link. Keep the chat technical proof hidden by default. Do not call `/tool-call`, invoke Python locally, or start a run when the route mounts. Run all frontend tests and build plus `.venv\Scripts\python.exe -m pytest --last-failed`; update context.md.
```

#### Task 7.5 prompt — animated workflow viewer

```text
Implement only Phase 7.5. Before UI code, add reducer/component tests mapping the actual workflow event stages to the user, agent, Veil, egress, helpdesk, token reply, restoration, and answer nodes; include blocked, failed, duplicate, replay, reconnect, and reduced-motion cases. Build the separate `/runs/:runId` screen with @xyflow/react custom nodes/edges and Motion. Fetch the run snapshot and subscribe to its SSE stream. Render the actual helpdesk-captured payload, not a copy of the agent call. The viewer must never POST/create a run. Animate the stored event sequence at readable speed without delaying the backend; show a replay indicator when the run is already complete. Run frontend tests/build and `.venv\Scripts\python.exe -m pytest --last-failed`; update context.md.
```

#### Task 7.6 prompt — one-run browser proof

```text
Implement only Phase 7.6. Add Playwright tests before fixing any integration issue. Prove the chat page creates one run and the second page displays that same ID and actual trace. On the success case, inspect captured tool payload for absence of synthetic planted originals and presence of tokens, tokenized helpdesk response, restored response, and final agent answer. On the blocked case, prove the helpdesk was not called and no response/answer was invented. Prove reload/reconnect/replay never sends a second POST. Use test fixtures and synthetic values only. Run Playwright and the full Python suite, report exact results, update context.md.
```

#### Task 7.7 prompt — polish and judge-machine launch

```text
Implement only Phase 7.7. First test any behavior changes. Refine responsive layout, readability, keyboard/screen-reader labels, reduced motion, and helpful connection errors without changing the workflow semantics. Update README to make the React chat and animated proof page the primary demo, document Python/Node/npm setup and the exact two-terminal VS Code launch commands, and label Streamlit as fallback. Run Python tests, frontend tests/build, Playwright, synthetic benchmark, and manual browser rehearsal only when available; report exact commands and outcomes. Update context.md with completed/remaining work. Do not claim a browser rehearsal or test that was not performed.
```

### Copy/paste prompt for implementation agents

```text
Read context.md and implementation-plan.md fully before editing. Continue the existing Veil MVP; do not recreate its Python privacy gateway or helpdesk workflow. The new target is Phase 7: two separate React pages over one local run. Page `/` is a simple synthetic user chat that submits once to `POST /api/runs` and shows the real local agent answer. Page `/runs/{runId}` is an animated workflow evidence view of that exact run. Every circle-led node must show the actual message/payload it received and the operation it performed: original user request; agent's prepared tool request; Veil's protected copy, detection count, and egress decision; exact helpdesk-captured payload and tokenized reply; trusted-path restoration; agent answer. Put the real data in clear visual evidence panels and highlight reversible tokens; avoid relying on prose alone. Both pages must share a run ID, actual event sequence, actual helpdesk-captured tokenized payload, tokenized tool reply, Veil-restored reply, and final answer. Keep Python 3.12, FastAPI, `VeilGateway`, `run_ticket_demo`, and the offline helpdesk. Use React + TypeScript + Vite, React Router, Motion for React, and Vitest/React Testing Library; use an accessible connected node rail with reduced-motion support. Use synthetic data only; never send user messages or PII to external services; never log raw values; do not store the token vault; keep run history in memory with TTL/capacity limits; fail closed. The workflow is synchronous today, so run it in a worker thread and safely bridge actual callbacks to replayable SSE with event IDs. The viewer must never start a new run on mount/reload. No fake backend delays or fabricated stages; the frontend may animate actual ordered stored events at readable speed. For each Phase 7 task, write tests first, show the expected failure, implement only that task, run its focused checks, then run `.venv\Scripts\python.exe -m pytest --last-failed` and the frontend tests. Report exact commands/results and update context.md with status, tests, limitations, and next task. Keep Streamlit as a fallback until the new browser workflow passes acceptance.
```

## Recommended way to work

Use **Codex in this workspace as the primary coding agent** because this chat and files already share the project directory. Antigravity or Claude Code can also work, but use one writer at a time to avoid conflicting edits. Before switching tools, save the latest status and next action in `context.md`; the next agent must read that file first.

Do not ask an agent to build the whole product in one pass. Give it one phase prompt, inspect the diff and run the checklist, then proceed.

### Current handoff status

Phases 0–5 and the Phase 6 Python workflow plus single-page Streamlit implementation are present. Phase 7.1 adds the React chat shell and connected node preview. Phase 7.2 adds `POST /api/runs`, `GET /api/runs/{run_id}`, and replayable SSE with event IDs and `Last-Event-ID` resume. The chat now creates one run and shows the answer; the workflow page opens the same run and displays actual per-node evidence, including the Veil-protected copy and exact tool-bound payload. It animates actual event history for readability; no operation is delayed or fabricated. Next: rehearse the complete browser workflow and fix end-to-end issues. Do not rerun the scaffold or remove the tested Streamlit fallback until the replacement passes. Prior synthetic benchmark results are historical and were not rerun for this UI update. Browser end-to-end acceptance remains open.

```text
Read context.md and implementation-plan.md before editing. The Veil MVP is already implemented. Inspect the current files and run the documented checks first. Do not recreate the scaffold or replace working files. Report the current test/benchmark status, then make only the specific follow-up change requested by the user. Keep synthetic-only data, no external services, and update context.md at the end.
```

## Phase 6 — Existing user-driven workflow and first Streamlit proof (historical baseline)

This phase records the Python workflow and first Streamlit screen that already exist. Keep its tested agent/gateway/helpdesk behavior. Phase 7 above supersedes its single-screen UI direction and is the current implementation target. Phases 0–5 describe the earlier MVP; do not recreate the scaffold or replace working gateway components.

### Outcome and fixed decisions

- A judge enters or edits one **synthetic** free-form request plus sample contact details. A ticket ID selects lookup; otherwise the agent submits a general support request. The judge can list exact extra synthetic values to protect when they fall outside automatic recognizers.
- A deterministic local agent selects a helpdesk action, prepares its tool call, and later formats an answer from the tool response. It must be labeled as a local demo agent; it is not a hosted LLM.
- Every agent-to-tool call goes through `VeilGateway`. The agent cannot call `SimulatedHelpdeskTool` directly.
- Veil replaces supported PII in the outgoing tool arguments with request-scoped tokens, checks the exact egress payload, and blocks before dispatch if anything unsafe remains.
- The offline helpdesk either looks up the synthetic ticket by its non-PII ticket ID or accepts a general support request. It echoes tokenized message/contact context so the return path can be demonstrated.
- Veil restores the response only on the trusted path back to the agent. The agent produces the answer the UI shows to the user.
- The primary screen presents exactly one workflow. Do not put the generic PII playground or a benchmark dashboard beside it. Keep benchmark evaluation available through the existing CLI and display only metrics from this run in the workflow receipt.
- Use Python, Streamlit, the existing gateway, pytest, and the current `.venv`; do not add uv, a hosted model, cloud service, real helpdesk, or external API.

**Security language:** call this reversible tokenization or pseudonymization, not encryption. The in-memory vault maps tokens back to originals. The helpdesk sees tokens and the ticket ID, not the protected original values. A tool that must query using an original email would need a different trusted-service design; a token cannot substitute for a value the tool must use.

### Target run, in execution order

```text
Synthetic user request
  → local agent chooses ticket lookup or general support intake
  → agent prepares tool arguments containing message and contact context
  → Veil detects and tokenizes selected PII
  → Veil verifies the exact tool name and payload
  → local helpdesk captures only the verified tokenized payload
  → helpdesk looks up the synthetic ticket and echoes tokens in its reply
  → Veil restores the response before returning it to the agent
  → agent formats the answer shown to the user
```

All components may run in one local process for this milestone. Keep their interfaces separate and inject the gateway/tool into the agent workflow so tests can prove that the boundary is mandatory. Do not add multiple server processes just to make the diagram look distributed. The captured `SimulatedHelpdeskTool.received` call is the ground truth for what the tool saw.

### Event contract for the animated screen

The animation must be driven by events emitted by completed workflow operations, not by a prewritten story or arbitrary sleeps. Add a small typed event/trace contract in `veil/demo_flow.py` (or a focused `veil/demo_events.py` if the flow module becomes too large):

- `run_id`: unique identifier for this single run.
- `stage`: stable identifier such as `request_received`, `agent_planning`, `tool_call_prepared`, `veil_scan_complete`, `egress_verified`, `tool_received`, `tool_replied`, `response_restored`, `agent_answered`, `blocked`, or `failed`.
- `status`: queued, active, complete, blocked, or failed.
- `message`: short plain-language explanation safe to show in the UI.
- `artifact`: optional actual artifact for that stage, such as the agent call, detections, exact captured tool payload, tokenized tool response, restored response, or final answer.

Emit each event only after the operation it describes has actually happened. For example, do not emit `tool_received` until the helpdesk captured the request. A blocked run must end at the egress gate and contain no tool-received, tool-response, restored-response, or success-answer event. Exceptions must produce an honest failed stage, never fabricated success evidence.

Do not store the token vault or its original-to-token mapping in the UI trace. The vault stays scoped to the active run and is cleared after restoration or failure. The trace may hold the original synthetic request for the local screen, but never write it to logs or disk. Display user-controlled text with normal Streamlit text/code widgets; do not interpolate it into raw HTML.

### One-screen visual design

Build a single, focused Streamlit story screen for one run at a time:

1. **Request panel:** editable synthetic user message, structured contact fields, and an optional list of exact extra synthetic values to protect. A ticket ID selects ticket lookup; without one, use general support intake. Clearly label all values as synthetic and explain the automatic detector limits.
2. **Run control:** one primary `Run workflow` button. Clear stale run artifacts when input changes. Disable or guard duplicate submissions while a run is active.
3. **Live journey:** show the ordered stages as responsive step cards: User → Agent → Veil → Safety check → Helpdesk → Veil restoration → Agent answer. Update each card from the event callback while the synchronous workflow executes. Mark prior stages complete, the active stage visibly active, and future stages waiting. Use a pulse only while a real operation is active, with reduced-motion support; do not add artificial sleeps or a frontend framework.
4. **Boundary evidence:** at the Veil/helpdesk boundary, show the exact payload captured by the helpdesk, with detected PII represented as tokens. Beside it, show the helpdesk’s tokenized reply and Veil’s restored reply. These must come from the current `WorkflowRun`, not constants or reconstructed display data.
5. **User result:** show the final answer returned by the local agent only after the restored response reached it.
6. **Run receipt:** show run ID, egress pass/block, tool-call count, protected detection count, original-PII leakage count, restored-value count, Veil-added latency, and total workflow latency. Derive all values from the current run and captured boundary. Do not label a blocked call as a zero-leak success if the tool was never called; show “blocked before tool call.”
7. **Reset:** allow one click to clear the previous request, event trace, and displayed artifacts; do not retain the vault.

The animation should communicate movement across trust boundaries without pretending a network request occurred. Use no fake delays. A modest pulse/highlight on the active step is enough; respect reduced-motion preferences and maintain readable contrast. Render a blocked run by stopping the visual path at “Safety check,” marking the helpdesk and later stages “not reached.” Keep the existing first-scan-miss example as a clearly labeled second run mode only if it can reuse the same event/receipt presentation.

### Implementation tasks — execute in order, test first for each behavior

**Progress:** Tasks 6.1–6.4 are implemented. The agent chooses ticket lookup or general support intake; users may supply exact extra synthetic secrets for tokenization. The current Streamlit fallback shows the actual request-driven timeline, exact helpdesk-captured payload, restored response, and final answer. Phase 7.1 React/Vite routes exist at `/` and `/runs/:runId`. Phase 7.2 implements asynchronous creation/read plus replayable SSE. Chat now submits once, receives the real answer, and links to the same run's workflow view. Six connected nodes reveal each operation and its actual artifact: original message, agent call, Veil protected payload/egress decision, helpdesk capture/tokenized reply, trusted restoration, and final answer. Tokens are visually highlighted, and blocked calls stop at Veil. The frontend replays actual recorded events with readable animation and no artificial backend delay. Run history remains local, bounded to 100, and expires terminal records after 15 minutes. Final regression: `.venv\Scripts\python.exe -m pytest --last-failed` → 44 passed in 5.51s (one Starlette/httpx deprecation warning); frontend `npm test -- --run` → 9 passed; `npm run build` → passed; `git diff --check` → clean. Next: verify the full run in a real local browser and do a judging rehearsal. Keep Streamlit as fallback until the browser run passes; do not claim universal PII detection.

#### 6.1 Specify and test the user-to-agent input

- Add tests before modifying `veil/demo_agent.py` for ticket requests, free-form messages, and supported synthetic requester details.
- Use explicit, typed inputs rather than hidden module constants. Have the agent select ticket lookup when the message has a supported ID, otherwise prepare general support intake; both calls include the message and structured requester context.
- Keep ticket parsing narrow and deterministic. Do not make the agent detector a second PII middleware; Veil remains responsible for automatic detection and optional exact user-marked values.
- Add agent unit tests proving the selected tool, extracted ticket ID, forwarded user context, and final-answer formatting from a supplied response.

**Gate:** agent logic accepts user data and prepares a tool call, but has no direct reference to the helpdesk implementation.

#### 6.2 Test and implement the end-to-end orchestrator

- Add integration tests first in `tests/test_demo_flow.py` for the successful and blocked event sequences.
- Update `veil/demo_flow.py` to accept the request and injected agent/gateway/helpdesk dependencies, execute the actual sequence, and return a run object containing final result plus emitted events/artifacts.
- Pass every tool call through `VeilGateway.call_tool`; never have the agent call the tool adapter directly.
- Ensure the success event order matches execution. Ensure the block event is emitted before any helpdesk call and stops the sequence.
- Preserve the actual helpdesk capture as the evidence source. Do not copy the pre-sanitized agent arguments into a field called “tool payload.”

**Gate:** a non-UI integration test proves originals are absent from `helpdesk.received`, tokens are present in the tool response, the restored response contains the correct originals, and the agent formats its answer from that restored response.

#### 6.3 Harden the trust boundary and cleanup

- Add tests for residual PII, detector/verifier exception, malformed/unsupported request, helpdesk failure, unknown token, and closed task context.
- Keep existing fail-closed behavior: verification errors or residual PII prevent dispatch. Confirm the helpdesk call count remains zero on every blocked case.
- Ensure audit records, Python logs, and exception messages do not include original values. UI display of the synthetic user’s own request is allowed; logs and helpdesk payload are not.
- Verify the vault clears in `finally` on success and failure. A new run must not be able to restore a previous run’s tokens.
- Measure Veil processing latency separately from total workflow latency; do not count Streamlit rendering time as Veil latency.

**Gate:** tests inspect captured tool calls, audit objects, logs, cleanup state, and event trace; no unsafe request reaches the helpdesk.

#### 6.4 Build the original event-driven single-workflow Streamlit UI

- Write/update Streamlit AppTests before changing `veil/demo.py`. Tests should submit custom synthetic input with and without a ticket ID, include an exact user-marked secret, click Run workflow, assert the restored answer, ordered stage labels, animation styling, and actual tool-bound payload stored for that run.
- Refactor the current two-tab page into one primary workflow view. Remove the PII playground tab from the judge-facing page; leave benchmark CLI and its documentation intact.
- Render events as they are emitted using a callback or iterator consumed by the Streamlit script. Keep orchestration logic independent of Streamlit so it remains unit-testable.
- Implement queued/active/complete/blocked/failed visuals. On success, the final answer appears after restoration and agent completion. On block, mark downstream steps “not reached,” show the reason in plain language, and report zero helpdesk calls.
- Put full JSON artifacts in clearly titled expandable panels, but make the simple timeline and final answer visible by default. The captured request label must say “What the helpdesk actually received.”
- Clear the prior trace on request edits and reset. Do not let the UI accidentally show stale artifacts as belonging to a new run.
- Do not add charts, extra workflows, benchmark dashboards, login, cloud hosting, network APIs, or arbitrary animation sleeps.

**Gate:** AppTests verify success and blocked screens against the run object. Manual review confirms the progress indicator advances only when the corresponding operation has completed.

#### 6.5 Complete judge rehearsal and project handoff

- Update README’s run instructions and judge script for the one-screen workflow; use direct Python/pip commands, not uv.
- Update `context.md` with new component behavior, decisions, exact checks, limitations, and next action.
- Run the focused tests after each task with `\.venv\Scripts\python.exe -m pytest --last-failed`; run the full suite with `\.venv\Scripts\python.exe -m pytest -q` before calling this milestone complete.
- Launch the app with `\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1` and rehearse one success and one blocked run from a clean reset.
- Record the synthetic benchmark separately; do not imply its small corpus proves complete detection.

### Phase 6 acceptance checklist

- [x] Judge can enter a synthetic request with or without a ticket ID and see the agent prepare a ticket or general support tool call.
- [x] Exact extra synthetic values listed by the user are tokenized in the request and restored in an echoed response.
- [ ] The only route from agent to helpdesk is through Veil.
- [x] The animated timeline is driven by actual workflow events, has no fake success step, and stops at the actual failure boundary.
- [x] The displayed helpdesk payload is the deep-copied payload captured at the helpdesk boundary.
- [ ] No protected originals occur in that captured payload; the synthetic ticket ID still finds its ticket.
- [ ] The tool response contains tokens; the agent receives the restored response and creates the visible final answer.
- [x] A blocked request produces zero helpdesk calls and no fabricated reply.
- [ ] Vault state is cleared on success and failure; run traces and logs contain no raw PII other than the synthetic request displayed locally.
- [x] The primary UI shows only this workflow and its run-specific proof/receipt; no competing playground or benchmark dashboard distracts from it.
- [x] Tests pass and the app starts with the documented direct Python command.
- [ ] Local browser access and the success/blocked judging rehearsal are verified on the actual judging machine (shell localhost probe was unavailable in this environment).

### Copy/paste prompt for the next implementation session

```text
Read context.md and implementation-plan.md first. Continue the existing Veil project; do not recreate the MVP. The Python agent/gateway/helpdesk workflow and Streamlit fallback already exist. The current target is Phase 7: React + TypeScript + Vite chat route `/` and animated workflow route `/runs/{runId}`, backed by the existing FastAPI and Veil workflow. The chat submits once; the viewer subscribes to and replays the same run. Use `@xyflow/react` and Motion for React. Keep automatic detection claims limited to selected types; exact extra synthetic secrets can be listed by the user. Never claim universal PII detection. Keep all examples synthetic and local; no hosted LLM, external tool, telemetry, or cloud service. Do not bypass the gateway, interpolate user text into raw HTML, add fake backend delays, or fabricate success. Fail closed on residual PII or gateway errors. Keep raw values out of logs, do not retain the token vault, and expire in-memory traces. For each Phase 7 behavior, write tests first, implement, run focused frontend/backend checks and `.venv\Scripts\python.exe -m pytest --last-failed`, and report exact results. Keep Streamlit as a fallback until the React end-to-end run passes. Update context.md after each task.
```

## Initial setup

The current shell does not have a normal `python` or `git` command available on PATH. The Codex workspace has a bundled Python 3.12.14 and pip, and a project `.venv` already exists. A normal venv creation tried to use unavailable `ensurepip`; it was created with `--without-pip`, then pip was installed into it. If using another IDE's terminal, install a normal Python 3.12 interpreter and Git for Windows, or configure that IDE to use the bundled paths.

From PowerShell in the project directory, a virtual environment can be created with the bundled Python:

```powershell
$pythonExe = 'C:\Users\Muhammed Ibrahim\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pythonExe --version
& $pythonExe -m venv --without-pip .venv
$env:TEMP = (Join-Path (Get-Location) 'work\pip-tmp')
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path .\work\pip-tmp, .\work\pip-cache | Out-Null
& $pythonExe -m pip --python .\.venv\Scripts\python.exe --cache-dir .\work\pip-cache install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then, in a new PowerShell session (or after activating the environment):

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation, call the virtual environment executable directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

`requirements.txt` is already present. Core dependencies are pure-Python or standard wheels. Do not make spaCy/Presidio mandatory: this environment's Application Control policy blocks spaCy's native extension. Keep all dependencies local and avoid any API keys or hosted services.

## Master prompt for any AI coding IDE

```text
You are helping build Veil, a local-first reversible PII privacy gateway for AI tool calls. Before editing, read context.md and implementation-plan.md completely. Treat context.md as the source of truth. Implement only the phase I name below; do not jump ahead or add unrelated features. Use synthetic data only. Do not call external APIs, use paid services, or transmit payloads. Keep raw PII out of logs. Preserve JSON structure and keys. Run the phase's requested checks and report their exact commands and results. At the end, update context.md: current status, next action, and an appended progress-log entry. Preserve existing context. Report files changed and any blockers.
```

Append the relevant phase prompt below to the master prompt.

## Phase 0 — Project scaffold

```text
Create the minimal project scaffold for the Veil MVP described in context.md. Add dependency metadata, a clean source layout for the FastAPI gateway, PII detection/tokenization, mock tool, Streamlit UI, synthetic fixtures, and tests. Add a README with local setup/run instructions. Do not implement the full feature set yet. Do not add real API integrations or secrets. Keep Python 3.11/3.12 compatibility. Use only dependencies needed for the planned MVP. Make the project runnable from a local virtual environment. Report the dependency install command and the first run command. Update context.md status and next action.
```

### Phase 0 checklist

- [ ] `context.md` and `implementation-plan.md` are present at the project root.
- [ ] Project source, UI, fixtures, and test directories have clear names.
- [ ] Dependency metadata installs in `.venv`.
- [ ] README setup commands match the actual files and shell.
- [ ] No API keys, external service URLs, or real PII are present.

## Phase 1 — Detection and reversible tokenization

```text
Implement only the core privacy engine. Recursively traverse JSON dictionaries/lists and inspect string values while preserving keys, types, and structure. Use pure-Python recognizers: regex plus normalization/validation for emails and phones, a custom recognizer for the synthetic student/account ID pattern, and context-aware name patterns plus a small fictional-name lexicon for person names. Do not import spaCy or Presidio in the baseline because this environment blocks spaCy's native extension. Keep detector code behind an interface so an optional Presidio adapter can be added later. For each detection, record entity type, confidence, and JSON path without logging the original value. Replace spans safely without offset corruption. Use random typed tokens and maintain a per-task reversible vault; repeated occurrences of the same original value within that task must reuse the same token. Add unit tests using synthetic values for nested fields, natural-language strings, duplicates, punctuation, unchanged non-string values, and round-trip restoration. Do not implement the UI or real tool integration yet. Report test commands/results and update context.md.
```

### Phase 1 checklist

- [ ] Emails, phone numbers, person names, and custom IDs are recognized in the agreed fixtures.
- [ ] Nested JSON strings are scanned; JSON keys and non-string values remain unchanged.
- [ ] Repeated values use the same token within a task.
- [ ] Tokens restore to the correct values.
- [ ] Logs/audit objects do not contain raw PII.
- [ ] Unit tests pass and their command/output is recorded.

## Phase 2 — Tool gateway, mock tool, and egress verification

```text
Implement the tool-call gateway around the Phase 1 privacy engine. Every tool call must pass through sanitization before dispatch. Add a local simulated tool that captures exactly the payload it receives and returns a response that includes one or more tokens. Before dispatch, run an egress guard over the sanitized payload and verify that no vault original remains; also run the configured residual PII check. If parsing, detection, or verification fails, fail closed and do not call the mock tool. After the mock response returns, restore tokens only on the trusted path back to the agent. Add integration tests proving the mock tool never sees planted original values, the returned response is restored correctly, and blocked calls do not reach the mock tool. Keep the mock tool offline. Update context.md with results.
```

### Phase 2 checklist

- [ ] Tool dispatcher cannot bypass the gateway in the demo path.
- [ ] Mock tool has a captured egress payload for inspection.
- [ ] Ground-truth synthetic originals are absent from captured egress.
- [ ] A simulated verifier failure blocks dispatch.
- [ ] Tool response tokens restore correctly only on the agent return path.
- [ ] Integration checks pass; no real network call is made.

## Phase 3 — Streamlit demo

```text
Build the Streamlit Privacy Lab for the existing engine/gateway. Provide one-click synthetic scenarios containing nested JSON and natural-language text, plus a safe way to enter a custom synthetic example. Display the original input only in the local demo view, detections with type/confidence/path, sanitized payload, exact payload captured by the mock tool, tokenized tool response, restored agent response, and a clear pass/block indicator. Show an audit receipt with counts and latency, never raw originals in logs. Keep the layout easy to explain in a 2-minute judging demo. Add helpful error messages and local run instructions. Do not add external APIs, cloud deployment, or accounts. Update context.md.
```

### Phase 3 checklist

- [ ] Demo starts with one documented command.
- [ ] One click runs the whole request → sanitize → mock tool → restore path.
- [ ] Screen clearly distinguishes what the agent submitted from what the tool received.
- [ ] Duplicate values visibly share tokens.
- [ ] Audit receipt contains no raw values.
- [ ] App works offline after dependencies/models are installed.

## Phase 4 — Benchmark and evaluation

```text
Implement the synthetic evaluation harness requested in context.md. Create a small labelled test corpus with known PII spans in structured and natural-language payloads, including common cases, nested values, repeated values, punctuation/spacing variations, and a few documented hard cases. Calculate detection recall, false positives/precision if the labels allow it, exact ground-truth leakage count at the mock-tool boundary, restoration accuracy, and p50/p95 added latency. Print a concise report and expose the key numbers in the UI. Keep all examples synthetic and do not present a limited corpus as proof of universal detection. Run the checks and document exact results and known misses in README/context.md.
```

### Phase 4 checklist

- [ ] Every planted example has a ground-truth label.
- [ ] Recall denominator is planted PII instances, not payload count.
- [ ] False positives are counted separately.
- [ ] Leakage is measured against the actual captured mock-tool payload.
- [ ] Restoration accuracy compares exact original/token pairs.
- [ ] Latency excludes model startup and reports the measured sample size.
- [ ] Known misses and benchmark limits are documented.

## Phase 5 — Presentation and final review

```text
Prepare the finished MVP for a hackathon judging demo. Review the full repo against context.md and all acceptance criteria. Fix only issues that affect correctness, safety, setup, evaluation, or the demo. Ensure setup works from a clean local environment using documented commands. Add a concise architecture explanation, limitations, and a 2-minute demo script to README.md. Run all requested tests/checks and the benchmark. Update context.md with final status, commands/results, remaining limitations, and final progress-log entry. Do not claim a check passed unless it was run.
```

### Phase 5 checklist

- [ ] A clean setup and run has been verified.
- [ ] All unit/integration/evaluation checks pass, with results recorded.
- [ ] Demo can be completed in two minutes without editing code live.
- [ ] Judges can inspect exactly what the mock tool received.
- [ ] README and `context.md` agree with the implementation.
- [ ] Limitations are stated accurately.

## Suggested 2-minute demo narration

1. Enter an arbitrary synthetic support message without a ticket ID. Add one exact synthetic secret to the custom-protection field and include it in the message; enter synthetic name, email, and phone values.
2. Click **Run workflow**. Follow the pulsing, event-driven stages: agent prepares the support call, Veil protects and verifies it, helpdesk receives tokens, and Veil restores the response.
3. Open **Show the proof from this workflow**. Point to **What the helpdesk actually received** and show that the custom secret and contact values are tokens. Then compare the tokenized reply with the restored message and the agent answer.
4. Click **Show blocked example**. Explain that the example intentionally injects a first-scan miss and Veil's egress check blocks before the helpdesk is called.
5. To show ticket lookup instead, reset the request and include `TICKET-DEMO-1042`. If judges ask about measured detection or latency, run the synthetic evaluation CLI and state its corpus limitations.
