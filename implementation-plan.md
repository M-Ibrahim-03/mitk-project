# Veil MVP — Implementation Plan and AI IDE Prompts

Read `context.md` first. It is the source of truth for scope, constraints, architecture, status, and decisions. This plan provides the staged prompts and checklists.

## Recommended way to work

Use **Codex in this workspace as the primary coding agent** because this chat and files already share the project directory. Antigravity or Claude Code can also work, but use one writer at a time to avoid conflicting edits. Before switching tools, save the latest status and next action in `context.md`; the next agent must read that file first.

Do not ask an agent to build the whole product in one pass. Give it one phase prompt, inspect the diff and run the checklist, then proceed.

### Current handoff status

Phases 0–5 and Phase 6 tasks 6.1–6.4 are implemented in this workspace. The local agent now supports ticket lookup or free-form support intake; the user can list exact extra synthetic secrets for tokenization; the single-screen UI renders a responsive, pulsing timeline from actual workflow events. Do not rerun Phase 0 or overwrite the existing implementation. Latest full suite: 37 passed. Latest synthetic benchmark: 20/20 planted details detected, zero false positives, zero leakage, 20/20 token occurrences restored, p50 0.104 ms, p95 0.286 ms. Streamlit printed a startup URL at `http://127.0.0.1:8502`, but the shell's local HTTP probe could not connect; rehearse browser access on the actual judging machine before presenting.

```text
Read context.md and implementation-plan.md before editing. The Veil MVP is already implemented. Inspect the current files and run the documented checks first. Do not recreate the scaffold or replace working files. Report the current test/benchmark status, then make only the specific follow-up change requested by the user. Keep synthetic-only data, no external services, and update context.md at the end.
```

## Phase 6 — User-driven workflow with an animated proof screen

This is the next implementation milestone. Phases 0–5 describe the existing MVP; do not repeat them or replace their working components. The goal is to extend the fixed ticket example into one complete run driven by user input, then make the UI visualize that run as it actually happens. The workflow and boundary evidence are the product; the UI is its witness.

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

**Progress:** Tasks 6.1–6.4 are complete, including follow-up work aligned with the user's broader target. The agent chooses ticket lookup or general support intake; users may supply exact extra synthetic values for tokenization. The single-screen page shows a responsive pulse animation driven only by actual operation events, exact captured helpdesk payload, restored response, and final agent answer. Focused tests pass; full suite: 37 passed. Benchmark: 20/20 planted instances detected/restored, zero false positives/leakage, p50 0.104 ms and p95 0.286 ms (7 cases). Streamlit printed `http://127.0.0.1:8502`, but a shell HTTP probe could not connect in this environment. Next: task 6.5 verify browser access and rehearse both paths on the judging machine; do not claim universal PII detection.

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

#### 6.4 Build the event-driven single-workflow UI

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
Read context.md and implementation-plan.md first. Continue the existing Veil project; do not recreate the MVP. Phase 6 tasks 6.1–6.4 are implemented. Preserve the goal: user enters a free-form synthetic message; local agent selects ticket lookup or general support intake; every tool call passes through VeilGateway; the simulated helpdesk captures the exact protected payload and returns tokens; Veil restores known values for the trusted agent; and the single-screen UI animates only actual workflow events. Automatic detection covers selected types only; exact extra synthetic secrets can be listed by the user. Never claim universal PII detection. Keep the app local with synthetic data only; no uv, hosted LLM, external API, real helpdesk, or cloud service. Do not bypass the gateway, interpolate user text into HTML, add artificial sleeps, or fabricate success. Fail closed on residual PII or gateway errors. Keep raw values out of logs/audit events and clear the request-scoped vault on every exit. Next task is 6.5: verify browser access and rehearse both request paths on the judging machine; shell localhost access failed in the current environment although Streamlit printed its URL. For each behavior, write tests first, implement, run `.venv\Scripts\python.exe -m pytest --last-failed`, and report the exact result. Update context.md after each task.
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
