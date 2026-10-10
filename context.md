# Veil — Project Context and Agent Handoff

Last verified: 2026-10-10 (Gemini fallback implementation)
Project root: `C:\Users\Muhammed Ibrahim\Documents\Codex\2026-10-09\mitk-project`
Status: The core Veil middleware, deterministic agent, optional Gemini path, FastAPI replayable run API, React chat and six-step workflow, Streamlit fallback, synthetic benchmark, and local simulated helpdesk are implemented. React accepts only the seeded local ticket `TICKET-DEMO-1042`. Gemini requester contact restoration and same-run deterministic fallback for provider/network/configuration availability failures are implemented and covered by focused tests; a fresh successful live Gemini browser run is not verified. The full Python suite is also not verified in the current Codex shell because Windows asyncio socket-pair setup stalls in AppTest/HTTP tests. See the authoritative exact stop-point snapshot below.

> **Start here when opening this repository in another IDE, agent, or chat.** Read this file first, then `implementation-plan.md` and `README.md`. Treat this file's **Current state** and **Next action** as the freshest checkpoint. The plan preserves the original design and implementation sequence; some early Phase 7 paragraphs describe React Flow as the intended graph, while the implemented page uses an accessible vertical CSS-connected evidence flow, animated connector particles, and Motion. Do not rebuild already working features because a plan paragraph is historical.

## Quick handoff

Veil is a local-first hackathon prototype of middleware between an AI agent and a tool. A user submits a synthetic helpdesk message to either the default deterministic offline agent or an explicitly configured Gemini agent. Gemini mode sends only a locally tokenized prompt to Google's hosted API; its proposed call is schema-checked and must still pass through Veil before the offline simulated helpdesk. Gemini sees a protected tool result, and Veil restores known tokens locally after the draft answer. The React chat and workflow pages share the same backend run.

The Python workflow, API, React pages, and tests are already implemented. Keep the middleware and local simulated tool as the core; the UI is evidence of that workflow. Gemini is optional and server-configured. Do not replace the tested privacy path or send real personal/confidential data to Gemini.

## Current state and next action

### Handoff snapshot — exact stop point (authoritative, 2026-10-10; updated after Gemini fallback work)

This is the current continuation point. Older checkpoints below preserve history and may describe earlier states; follow this section and the newest detailed checkpoint first.

#### Architecture and workflow in words

1. The user enters one synthetic helpdesk message in the React chat (`/`). FastAPI accepts it only if it names a ticket that exists in the local simulated helpdesk; the only seeded ticket is `TICKET-DEMO-1042`.
2. FastAPI creates one `run_id` and starts the workflow. The deterministic offline agent builds the allowlisted lookup request locally. In Gemini mode, Veil first tokenizes selected values in the message, then sends that protected prompt to Gemini. Gemini may propose `lookup_helpdesk_ticket`; SDK auto-execution is disabled, and the application validates the proposal and its arguments. Provider/network/configuration availability failures use the local agent and emit an `agent_fallback` event in the same run.
3. Both modes send the prepared call through `VeilGateway`. The gateway recursively scans and tokenizes the payload, verifies the exact outgoing payload and tool name, then either fails closed or dispatches to the simulated helpdesk. The helpdesk is local and captures the exact receipt it received.
4. The helpdesk returns a tokenized reply. Veil restores the trusted local reply using the task-scoped in-memory token vault. For Gemini, Veil also checks and sends only protected tool-result context to Gemini; after Gemini drafts its answer, Veil restores known tokens locally. If Gemini cannot finish its final answer, the deterministic agent uses that same restored tool result without a second helpdesk call.
5. FastAPI records ordered workflow events and artifacts for that run. The chat displays the answer and links to `/runs/{run_id}`. The six-step CSS/SVG + Motion workflow page loads a snapshot and replayable SSE for the same `run_id`, including the exact helpdesk receipt and fallback event when used. Fallback is not reported as a successful Gemini call. If egress is blocked, the helpdesk has no call or receipt.

The local boundary contains FastAPI, the agents' orchestration, Veil, the run registry, token vault, and simulated helpdesk. Gemini is an optional external provider and receives only the protected prompt/result context. Tokens are reversible pseudonyms, not encryption; detection is limited to selected patterns.

#### At-a-glance status

| Area | Current evidence | Status |
|---|---|---|
| Privacy gateway | Recursive scanning, task-scoped reversible tokens, fail-closed egress verification, exact simulated-tool receipt, and trusted restoration are in source. | Implemented; focused tests and synthetic evaluation exist. |
| Ticket workflow | React accepts only a known local ticket; currently only `TICKET-DEMO-1042` is seeded. Unknown or malformed IDs are rejected. | Implemented; keep this rule. |
| Agent modes | Deterministic offline agent and optional Gemini agent. Gemini proposes the allowlisted call; the application validates and dispatches it through Veil. Provider/API/network/configuration availability failures during proposal or final answer continue through the deterministic local agent in the same run. Invalid proposals and Veil blocks do not fall back. | Implemented; focused flow/API/UI checks pass. |
| Gemini contact answer | Selected `PERSON`, `EMAIL`, and `PHONE_NUMBER` values from a Gemini request are protected in the tool payload and restored on the trusted answer path. Government/financial identifiers are not copied to requester fields or the final answer. | Focused synthetic flow tests pass; fresh live browser proof remains outstanding. |
| Benchmark / second example | Development and held-out corpora cover all 11 advertised types. The evaluation reports per-type metrics, exact receipt leakage, blocked-path zero calls, restoration, and warmed gateway-only latency. Streamlit has a separate generic nested-JSON example. | Implemented; see `benchmark-results.md` for the recorded results and limits. |
| Python suite | This change: flow/Gemini tests — 23 passed; focused missing-key and safe-protocol API tests — 2 passed. `uv run pytest --last-failed` could not start because `uv` is unavailable. The `.venv` fallback selected `tests/test_demo_ui.py` and stalled for about 40 seconds without output; it was interrupted. | Full suite is not verified; rerun from normal PowerShell. |
| Live Gemini | The known browser run ended with a final-answer `ServerError` before the retry update. A later direct provider smoke attempt failed at DNS/network setup. The source now configures retries and omits deprecated sampling parameters, but there is no fresh complete run proving the key/provider request succeeds. | Unverified; don't claim Gemini success. |
| Browser/API processes | The browser still has the earlier failed-run tab open. Current shell checks to localhost ports 8000 and 5173 failed; no listener information was returned. | A live UI rehearsal could not be run from this shell. Check service health and owning PIDs before starting anything; don't kill an unidentified process. |

#### What was changed recently, and why

- Gemini provider/API errors (including 401/429/5xx), transport failures, and missing local Gemini configuration now trigger a labeled deterministic fallback. Proposal failure falls back before the tool call; final-answer failure uses the already restored result and never repeats the helpdesk call. The same run records an `agent_fallback` event. Invalid proposals and Veil egress blocks do not fall back.
- The React chat identifies a fallback answer as offline, and the six-step workflow shows fallback mode, event, and answer source without an error banner. A Gemini-selected API run can now start without a local key and complete through fallback.
- Verification for this change: `.venv` flow/Gemini tests — 23 passed; focused missing-key and safe-protocol API tests — 2 passed; frontend chat/workflow tests — 11 passed; `npm run build` passed. Full `--last-failed` is not verified: it stalled in Windows AppTest. `uv` is unavailable in this shell.

- The benchmark was expanded with a held-out synthetic set, per-entity metrics, receipt scans against the actual captured tool payload, blocked-path zero-call proof, and repeated middleware-only timing. This addresses the problem statement's detection, leakage, restoration, and performance criteria. Coverage is selected-pattern and limited; the results are not a universal PII guarantee.
- The separate Streamlit nested-JSON example demonstrates that `VeilGateway` can protect structured payloads beyond the ticket UI, while the React demo remains constrained to a valid local ticket for a predictable judging workflow.
- The Gemini ticket path was strengthened so supported contact details can travel through the protected tool receipt and be restored for the trusted final answer. This is the central demonstration: protected values at tool egress and useful restored information for the user. Deterministic payload shape was kept stable.
- Gemini calls no longer send the deprecated `temperature` option, and the SDK client configures bounded retries after the earlier final-answer `ServerError`. These source fixes still need a live retest.
- Streamlit AppTest expectations now inspect the correct Streamlit element collections (`caption` and `header`). Message-derived requester extraction is Gemini-only so it does not add an unexpected `requester` field to deterministic requests.
- This handoff is text-only. The next IDE task is Python-suite verification and the live Gemini rehearsal; presentation work is excluded.

#### Exact stop point and next actions

The current source includes the Gemini availability fallback described above. The frontend regression tests and production build pass. No fresh live browser run has verified either the successful Gemini path or the fallback UI against the running services. The required `.venv` `--last-failed` command stalled at `tests/test_demo_ui.py`; focused relevant tests pass.

1. Preserve the existing dirty tree. At the start of this handoff, `git status --short` showed modifications to `context.md`, `tests/test_demo_flow.py`, `tests/test_demo_ui.py`, `tests/test_gemini_agent.py`, `veil/demo_flow.py`, and `veil/gemini_agent.py`, plus existing untracked files under `outputs/`. Preserve all of them; do not revert, clean, or overwrite changes. Presentation work is outside the next task.
2. Re-run the Python suite in the user's normal PowerShell. Prefer `uv` only if it is available and working; the user previously had trouble with it. Otherwise use the project venv. Record hangs/errors accurately; a stalled Windows socket-pair setup is not a passing suite.
3. Check whether the existing API and Vite servers are healthy before launching or restarting them. Port 8000 was previously occupied, so identify the owning project process and reuse its terminal or restart that known process. Do not kill an unknown PID.
4. Ensure the backend is actually configured for Gemini without printing or opening the API key value. The user authorized use of the project's existing server-side credential for synthetic prompts and plans to revoke it after the project. The credential was pasted into chat: never reproduce it, write it into files/prompts, or show it in logs.
5. After the backend and frontend are restarted from this checkout, submit one fresh synthetic request for `TICKET-DEMO-1042`. Follow the workflow link and inspect one `run_id`. If Gemini is reachable, verify tokenized input, validated proposal, egress, exact protected receipt, protected model context, trusted restoration, and final Gemini answer. If unavailable, verify `agent_fallback`, successful protected egress, the same local helpdesk receipt, trusted restoration, and deterministic answer. Use no real personal/confidential data.
6. If any supported planted value reaches the helpdesk, add a failing regression first, then make the smallest responsible fix and rerun focused checks plus `uv run pytest --last-failed` (or the documented venv fallback). Update this snapshot with actual commands, results, run ID, and remaining blockers. Do not claim the live Gemini flow passed until every required stage is visibly present in the same run.

The current open browser state is the earlier failed workflow. This shell could not reach localhost ports 8000 or 5173, so no fresh trace was obtained. The immediate stop point is: source changes and focused regression evidence are present, but the full Python suite, live fallback UI, and successful live Gemini call remain unverified.

#### Latest Gemini check (2026-10-10)

- A direct fresh synthetic workflow was executed from this checkout with `agent_mode="gemini"`, using `TICKET-DEMO-1042` and fictional contact values. Run ID: `2043be8518a24e429110433b234d35dc`.
- The workflow protected the model input, but the Gemini tool-proposal request raised an HTTPX `ConnectError`; the agent emitted `agent_fallback` at `tool_proposal`. This indicates the request could not establish its connection; it does **not** validate or invalidate the API key.
- The same run then completed its deterministic fallback path: Veil allowed egress, the local simulated helpdesk was called with protected values, all three synthetic contact fields were restored, and a final answer was produced. No Gemini-protected tool-result/model context was created because Gemini never proposed the call. This is a successful fallback, not a successful Gemini run.
- `tests/test_gemini_agent.py` plus `tests/test_demo_flow.py`: 23 passed. An attempted broader focused selection including `tests/test_run_api.py` printed 26 progress dots but did not return a summary before the command window yielded; do not count it as passing. The required `.\.venv\Scripts\python.exe -m pytest --last-failed` selected `tests/test_demo_ui.py` and emitted no result for 45 seconds; it was interrupted. The full suite is still unverified.
- The in-app browser opened the React chat at `http://127.0.0.1:5173/`; its status label said **Offline local agent**. It was not submitted, so there is no fresh same-run browser trace. The API was unreachable from this shell. A hidden Vite startup reported 5173 was already occupied and selected 5174; neither port was reachable from the shell. A direct Uvicorn attempt likewise did not expose a reachable API. Do not stop unknown browser-local processes.
- The ignored `.env` exists and the Gemini key is configured; the value was not read or displayed. Source model `gemini-3.8-flash` is listed as supporting function calling in Google's current [Gemini models documentation](https://ai.google.dev/gemini-api/docs/models). The observed failure is connection setup, so no source-model change is justified from this evidence.
- Next: restart the backend from the user's normal PowerShell in this checkout with `VEIL_AGENT_MODE=gemini`, after identifying the owner of port 8000 and confirming it is this project's stale API process. Then submit a fresh synthetic ticket in the browser and inspect one run through final answer. Until outbound Gemini connectivity succeeds, this credential's validity remains unknown. Preserve all existing dirty files and generated artifacts.

**Handoff-document verification:** no actual `AGENTS.md` file was found under the project; the user supplied workflow rules in the IDE instructions. `git diff --check` passed (Git printed normal LF-to-CRLF working-copy notices). `uv` is unavailable in this shell. The required fallback `.\.venv\Scripts\python.exe -m pytest --last-failed` selected the prior failure in `tests/test_demo_ui.py`, produced no further output for about 30 seconds, and was interrupted. This is recorded as a stall, not a pass.

**Last browser evidence to avoid confusing with a current pass:** run `61ea0f91295d450198f71d4d0ea2954a` reached Gemini's final-answer request but failed with a `ServerError` before the retry fix. Run `2a7c97b6a4b340909a1ed42baafc415a` came from a stale deterministic server and exposed supported-format misses; it is not valid proof for current source. Do not reuse either as successful Gemini evidence.

**Fast code orientation:** `veil/demo_flow.py` orchestrates agent choice and the user-facing workflow; `veil/gemini_agent.py` wraps Gemini function calls; `veil/gateway.py`, `veil/payload.py`, and `veil/token_vault.py` implement tool protection and trusted restoration; `veil/api.py` owns run creation/snapshots/SSE; `frontend/src/pages/ChatPage.tsx` and `WorkflowPage.tsx` render the two views over the run ID. Start with `tests/test_demo_flow.py`, `tests/test_gemini_agent.py`, `tests/test_run_api.py`, and `tests/test_gateway.py` when diagnosing these paths.

### Latest continuation checkpoint — 2026-10-10

**Latest retest fixes:** the user's rerun found two regressions. The UI assertion searched `app_test.markdown` for “Detected types”, although the app renders it via `st.caption`; the assertion now checks `app_test.caption`. Message-derived requester extraction was also being applied to deterministic runs, adding an unexpected `requester` key to the established API payload. Extraction is now Gemini-only; explicitly provided requester fields still work in deterministic runs. This retains the requested Gemini contact restoration without changing deterministic API payload shape.

**Verification:** `tests/test_run_api.py::test_message_only_run_protects_sensitive_text_before_helpdesk` and all `tests/test_demo_flow.py` tests passed together (**9 passed**). The corrected Streamlit AppTest and `pytest --last-failed` stall in this Codex execution shell during Windows asyncio socket-pair creation before their assertions; they must be rerun from the user's normal PowerShell, which previously ran AppTest successfully. `py_compile` and `git diff --check` passed. No full-suite pass is claimed.

**Contact restoration fix:** the React request has no separate requester form, so previously Gemini could propose only the required ticket/message/question fields and the helpdesk returned an empty requester object. In Gemini mode only, `run_ticket_demo()` uses locally detected selected `PERSON`, `EMAIL`, and `PHONE_NUMBER` values (or already supplied requester details), protects those requester values with the task vault before prepared-call evidence and gateway egress, and appends only those restored contact fields to the trusted Gemini answer. Government and financial identifiers are not copied into requester fields or the answer. Deterministic behavior and its API payload shape remain unchanged; the blocked-path fault injection keeps its intentional detector miss.

**Tests:** `tests/test_demo_flow.py` now includes a synthetic contact restoration regression. It first failed because the tool returned an empty requester, then passed after the change. The existing Gemini flow test now expects the restored contact line. `tests/test_demo_flow.py tests/test_gemini_agent.py` — **18 passed**. The user's normal PowerShell run had **79 passed, 1 failed**; the failure was a Streamlit test looking for an `st.header` title in `app_test.markdown`. The test now checks `app_test.header`. In this execution shell, that focused AppTest and `pytest --last-failed` stalled before app assertions in Windows asyncio socket-pair creation. No full-suite pass is claimed; rerun the suite in the user's normal PowerShell environment.

**Live Gemini:** still unverified. A previous current-source provider attempt failed before a response because this execution environment could not resolve the Google API hostname. The React browser path also previously had `Failed to fetch`. Restart the API in Gemini mode from the user's project terminal and perform a fresh synthetic same-run browser workflow before claiming live success. The user's key was not read or copied during this work.

**Next action:** from the user's normal PowerShell, run `uv run pytest --last-failed` if uv works; otherwise run `.\.venv\Scripts\python.exe -m pytest --last-failed`. Then restart the API in Gemini mode if needed and verify the same-run workflow stages and final answer in the browser. Use synthetic values only.

**Goal:** complete the existing one-tool Gemini ticket path without changing the ticket intake, privacy gateway, helpdesk, or React workflow design.

**Code change:** Google’s Gemini 3.8 migration guidance deprecates sampling parameters such as `temperature`. `GeminiAgent.prepare_tool_call()` and `create_final_answer()` no longer send `temperature`; `tests/test_gemini_agent.py` now asserts that for both requests. The model ID, explicit function declaration, disabled SDK auto-execution, single-tool allowlist, validated ticket arguments, three-attempt client retry policy, Veil gateway, and local helpdesk dispatch are unchanged.

**Verification:** the new assertions first failed for both request configs, then `tests/test_gemini_agent.py tests/test_demo_flow.py` passed (**17 passed**). `py_compile` and `git diff --check` passed. The direct live smoke attempt used only the fictional ticket `TICKET-DEMO-1042`; it failed before a provider response because this execution environment could not resolve the Google API hostname (`ConnectError`, `getaddrinfo failed`). No key or provider exception text was printed intentionally.

**Browser/API status:** the React page at `127.0.0.1:5173` loaded. A synthetic valid-ticket submission failed with `Failed to fetch`, so it did not produce a run and no same-run Gemini claim is made. The initial page badge is only its default state; it is not proof of the backend mode. The backend must be restarted in Gemini mode and become reachable from Vite before the rehearsal can continue.

**Python suite limitation:** `.venv\Scripts\python.exe -m pytest --last-failed -q -o faulthandler_timeout=30` passed 12 tests, then stalled in the first Streamlit `AppTest`. The traceback is inside Windows Proactor event-loop initialization, waiting in `socket._fallback_socketpair` before the test reaches its app assertions. Excluding `tests/test_demo_ui.py` passed 39 tests, then stalled in `tests/test_gateway.py::test_http_tool_endpoint_runs_local_mock_gateway` at `asyncio.run`, with the same socket-pair stack. This indicates a socket restriction in the current execution runtime; it is not evidence of an application assertion failure, and the full suite is not verified here. Run the same pytest commands from the user's normal PowerShell environment to check whether that runtime permits the local socket pair.

**Next action:** restart the existing API from the user's project PowerShell terminal with `$env:VEIL_AGENT_MODE = "gemini"` so it loads the source update and ignored local key. Confirm `/health`, then submit one synthetic message naming `TICKET-DEMO-1042` from the React page. Follow that run's workflow link and verify tokenized model input, validated tool proposal, egress, exact protected receipt, protected result context, trusted restoration, and final answer. If the request fails, use only the stage and safe error category to separate API reachability, DNS/network, credential, model-config, and protocol errors. Keep the single simulated helpdesk tool; the existing generic gateway example already demonstrates reuse beyond the ticket flow.

### Previous continuation checkpoint — benchmark improvements (2026-10-10)

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
8. The problem-statement comparison prioritized measurable detection, exact tool-boundary leakage proof, restoration, and isolated middleware timing. Those were implemented in the synthetic benchmark and structured JSON example. Gemini contact restoration and bounded retries were added to strengthen the optional live-agent path while preserving the deterministic fallback and local-only helpdesk.

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

## Current copy-paste prompt for a new IDE or window

Use this prompt when opening the project in another IDE or agent. The authoritative state is the handoff snapshot near the top of this file; older checkpoint material below it is history.

```text
Continue the existing Veil hackathon project from this checkout. Before acting, read `context.md`, `implementation-plan.md`, `README.md`, and any actual `AGENTS.md` instructions. Start with the section `Handoff snapshot — exact stop point` in `context.md`. Inspect `git status` and relevant diffs. Preserve every existing tracked and untracked change; do not reset, clean, replace, or rebuild the MVP.

Goal: finish the outstanding verification, especially the Python suite in the user's normal PowerShell and one fresh successful browser run of the optional Gemini path. The React chat `/` and six-step CSS/SVG + Motion workflow page `/runs/{run_id}` must prove the same run. React Flow was an old proposal; do not migrate the page. The local simulated helpdesk is the only tool; do not add another tool. Presentation/deck work is out of scope for this continuation.

Current source already includes the detector/token vault/Veil gateway, fail-closed egress check, deterministic offline agent, optional Gemini adapter, validated single-tool proposal, local helpdesk with exact receipt capture, trusted response restoration, replayable FastAPI SSE, React chat/workflow, Streamlit fallback, synthetic development/held-out benchmark, and tests. React intake accepts only the seeded local ticket `TICKET-DEMO-1042`. The separate Streamlit structured JSON demo shows generic gateway reuse.

Exact stop point: recent source work added Gemini-only extraction/protection/restoration of eligible contact fields, removed deprecated Gemini sampling parameters, configured bounded SDK retries after an earlier final-answer ServerError, and corrected two Streamlit AppTest element lookups. Focused runs recorded 9 passing API/demo-flow tests and 18 passing demo-flow/Gemini tests. The user's earlier full run had 79 passed and 1 UI-locator failure, which was corrected. The full Python suite is still unverified because this Codex Windows shell stalls in asyncio socket-pair setup before AppTest/HTTP assertions. A live provider smoke attempt also failed during DNS/network setup. No fresh same-run Gemini browser workflow has completed after the retry fix; do not claim the Gemini feature is live-verified.

First rerun Python tests from the user's normal PowerShell. Use `uv run pytest -q` and `uv run pytest --last-failed` if uv works there; otherwise run `.\.venv\Scripts\python.exe -m pytest -q` and `.\.venv\Scripts\python.exe -m pytest --last-failed`. Record any timeout/stall accurately. Do not claim the suite passed if it hangs.

Then inspect the current API/Vite health and ports before starting servers. Port 8000 was already occupied in a prior user report; identify the owning project process and reuse/restart only that process. Never kill an unknown PID or start a duplicate listener. Ensure the backend resolves to Gemini mode without printing or exposing the API key. The user has authorized use of the existing server-side project credential for synthetic prompts; it was pasted into chat, so never copy it into files or prompts, display it, or log it. The user intends to revoke it after the project.

Submit a new synthetic-only request for `TICKET-DEMO-1042`; use fictional contacts only. Follow that request's workflow link and verify from the same run ID: Gemini mode, tokenized model input, validated tool proposal, successful Veil egress, exact protected helpdesk receipt, protected tool-result context, trusted local restoration, and the final answer with eligible contact values restored. The simulated helpdesk stays local. If any supported value reaches it, write a failing regression first, then make the smallest fix and verify it. For code changes, stress-test the plan using the grilling skill and use TDD. After changes run `uv run pytest --last-failed` if uv works, otherwise use the project venv and report limitations. Update `context.md` with exact commands/results and the next stop point. Use no real personal/confidential data, and never claim a stage passed without same-run evidence.
```
