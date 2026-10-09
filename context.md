# Veil Project Context

Last updated: 2026-10-09
Project status: free-form helpdesk flow and event-driven animated proof implemented; next: verify browser access and rehearse on the judging machine
Timebox: 24-hour hackathon MVP

## 1. Project objective

Build **Veil**, a local-first privacy gateway for AI agent tool calls. Veil scans outgoing tool payloads, detects selected personally identifiable information (PII), replaces detected values with reversible, request-scoped tokens, prevents unredacted protected values from reaching a simulated external tool, and restores token values in a tool response only when returning that response to the trusted agent.

The implementation must be explainable, easy to demo, and evaluated with synthetic data. It does not need a paid API, hosted model, cloud service, or real external tool.

## 2. Original challenge and judging criteria

The hackathon problem asks for middleware or an SDK that intercepts outgoing agent-to-tool payloads, detects multiple PII types in structured and natural-language payloads, tokenizes values reversibly, and restores values in responses when needed. The judging criteria are detection, leakage prevention, restoration, and performance. Only synthetic personal data may be used.

## 3. Product idea

**Name:** Veil — a privacy firewall for AI tool calls.

**Pitch:** “Veil sits between AI agents and their tools, replacing personal data with temporary tokens and proving what the tool actually received.”

The MVP demo should show:

1. An agent request containing synthetic PII in natural language and nested JSON.
2. Detected entity type, confidence, and JSON path.
3. A tokenized payload captured by a local simulated tool.
4. A returned token restored before the response goes back to the trusted agent.
5. An audit receipt showing detections, leakage count, restoration accuracy, and added latency.

## 4. Scope and decisions

- **Local-only demo.** Use a simulated tool and synthetic fixtures; make no real tool or LLM API calls.
- **Stack:** Python, FastAPI, pure-Python local recognizers, Streamlit, and pytest. Presidio is a possible optional enhancement, not required by the runnable baseline.
- **PII scope:** email, phone number, person name, and a synthetic student/account ID pattern. Do not use real or valid personal identifiers in examples. Use regex/validation for structured IDs and contact details, plus context-aware patterns and a small fictional-name lexicon for names. Clearly document that person-name detection is the least reliable recognizer.
- **Payload scope:** JSON objects and arrays; recursively scan string values, including free text embedded in those values. Preserve keys, non-string values, types, and JSON shape.
- **Token mapping:** reuse the same token for duplicate values inside one task so cross-field relationships remain intact. Keep the map in memory for that task only and clear it at task completion.
- **Egress guard:** verify the sanitized outgoing payload before the mock tool receives it. Block on residual detections or gateway errors. The synthetic evaluation harness also checks outgoing payloads against planted ground-truth values.
- **Response restoration:** hydrate tokens only on the trusted return path to the agent, never in the payload sent to the simulated external tool.
- **Audit log:** store entity type, JSON path, confidence, token ID, decision, and timing. Do not log raw PII values.
- **Limitations:** this MVP protects the evaluated text/JSON payload scope. It does not promise detection of all PII, languages, encodings, images, audio, or obfuscation styles. A real tool that requires raw PII to perform its task needs a trusted service boundary; an opaque token alone cannot provide the original value to that tool.

## 5. Success criteria

- Every mock tool call goes through the gateway.
- Multiple PII types are detected in nested structured fields and natural-language strings.
- Replacements preserve payload shape and duplicate-value linkage.
- The mock tool receives no planted original values in the benchmark cases.
- A tokenized mock response can be mapped back to the correct original value on the trusted return path.
- The app reports detection recall, false positives, leakage count, restoration accuracy, and p50/p95 added latency.
- A reviewer can run the app and its documented checks locally without paid credentials.

## 6. 24-hour delivery plan

### Phase 0 — Scope and setup (hour 0–1)
- Confirm local Python setup and create the project scaffold.
- Freeze the PII types, synthetic fixtures, and acceptance criteria.
- Make `context.md` the project’s persistent source of truth.

### Phase 1 — Detection and token vault (hours 1–5)
- Implement pure-Python recognizers for email, phone, person-name patterns, and a custom synthetic ID.
- Implement recursive JSON traversal and span-safe replacement.
- Add a per-task reversible token map and metadata-only audit events.

### Phase 2 — Gateway, mock tool, and egress check (hours 5–8)
- Wrap the tool dispatcher so every call is sanitized.
- Add a local mock tool that records exactly what it received.
- Verify the sanitized request and block it if protected values remain.
- Implement trusted-path response restoration.

### Phase 3 — Demo interface (hours 8–11)
- Create a Streamlit page with sample scenarios, findings, outbound payload, mock-tool receipt, returned response, and metrics.
- Keep the original-value view limited to the synthetic demo input; never put raw values into audit logs.

### Phase 4 — Evaluation (hours 11–15)
- Add a labelled synthetic test set for common, nested, duplicate, punctuation, and selected hard cases.
- Calculate recall, false positives, leakage, restoration accuracy, and p50/p95 latency.
- Document known misses and false positives.

### Phase 5 — Polish and presentation (hours 15–18)
- Add setup instructions, architecture explanation, and a short demo script.
- Make the happy-path demo reliable and inspectable.

### Buffer and rehearsal (hours 18–24)
- Fix integration issues, rehearse on the actual demo machine, and keep the remaining time as contingency.

## 7. Development environment assumptions

- Host: Windows with PowerShell, using the shared project directory.
- Preferred primary IDE agent: Codex in this workspace. Antigravity or Claude Code may be used, but only one agent should modify the repository at a time.
- Python target: 3.11 if available; compatible Python 3.10+ is acceptable if dependency setup requires it.
- Run everything locally. Hosting is optional and outside the zero-cost MVP requirement.
- Environment note: the standard `python` launcher is unavailable. The Codex bundled Python 3.12.14 works and a project `.venv` was created. The installed spaCy native extension is blocked by the environment's Application Control policy, so the baseline must not require or import spaCy/Presidio. Keep all baseline detection in pure Python; revisit Presidio only if a supported interpreter/runtime can load it without changing security policy.

## 8. AI-agent continuity protocol

Every coding agent must:

1. Read this file before making changes.
2. Follow the current milestone and keep changes within MVP scope.
3. Use synthetic data only; never add real personal or confidential data.
4. Never make external API calls or send sample payloads to external services.
5. Run the checks explicitly requested for the current milestone and report exact commands/results; do not claim unrun checks passed.
6. At the end of a work session, update **Current status**, **Next action**, and the **Decision/progress log** below. Preserve the earlier context and append meaningful changes rather than replacing project history.
7. Report changed files, setup issues, tests/checks, and remaining blockers in plain language.

## 9. Current status

- User approved the Veil direction, requested a step-by-step 24-hour build plan, AI IDE prompts, checklists, and a persistent context file.
- The workspace initially contained only `outputs/` and `work/`; it now contains the working MVP source, docs, synthetic fixture set, and tests.
- A project `.venv` exists using Codex's bundled Python 3.12.14. `pip check` reports no broken requirements. Core imports succeed.
- Presidio/spaCy installation was explored but the environment's Application Control policy blocks spaCy's native extension. The shipped baseline is pure Python; the policy was not bypassed.
- Implemented recursive structured/text detection, reversible task-scoped tokenization, the gateway, mock tool, egress gate for values/keys/tool name, trusted-path restoration, FastAPI endpoints, Streamlit demo, and benchmark.
- `implementation-plan.md` has copy/paste prompts for each phase, setup instructions, verification checklists, and a demo narration.
- Final checks: `python -m pytest -q` → **18 passed**; `python -m pip check` → **No broken requirements found**; `python -m veil.evaluation` → 7 cases, 20/20 planted instances detected, 0 false positives, 0 leakage, 20/20 token occurrences restored, p50 0.163 ms, p95 0.322 ms. The Streamlit AppTest demo flow passed: egress allowed with zero leakage and the mock response restored exactly.
- Recorded evaluation snapshot: `benchmark-results.md`.
- User-facing source bundle is available at `outputs/veil-mvp-source.zip` (22 files; `.venv` and scratch files excluded; ZIP integrity checked).
- No decision is needed from the user before beginning local setup.
- The project folder is now `mitk-project` after the user renamed the root and cloned it to another system.
- Updated the Streamlit demo to guide reviewers through choosing a sample, protecting it, and reading a plain-language result. Technical request/response JSON is now optional in an expander; changing the sample clears stale results and loads that sample's own editable payload.
- Replaced the raw benchmark JSON view with readable metrics for detection, false alarms, originals sent, restoration, p50/p95 processing time, and sample count. The screen clearly states that this is a small synthetic test set.
- Added three UI behavior tests and `pytest.ini` (`testpaths = tests`) so pytest does not collect duplicate tests from the source bundle under `outputs/`.
- Verification after the UI update: `uv run --no-project --python .\\.venv\\Scripts\\python.exe python -m pytest -q` → **21 passed**; `python -m veil.evaluation` → 20/20 planted details detected, 0 false alarms, 0 leakage, 20/20 restored, p50 0.094 ms, p95 0.237 ms across 7 cases; `pip check` → no broken requirements.
- `uv` was installed into this workspace's ignored `.venv` for verification. In this restricted Windows environment, its cache must point to `work/uv-cache`; the regular `uv run pytest --last-failed` form is not usable without project metadata, so the verified invocation uses `--no-project` and the existing venv Python explicitly. `uv` is not installed globally on a fresh clone.

### Next action

Phase 6 tasks 6.1–6.4 are implemented and tested. The local deterministic agent selects ticket lookup when a supported ticket ID is present and general support intake otherwise. Users may list exact additional synthetic secrets that the middleware tokenizes alongside detected email, phone, ID, and name patterns. Both routes pass through VeilGateway; the helpdesk records the exact tokenized request and echoes tokens; Veil restores them for the agent. The single-screen UI has a responsive pulsing timeline driven by real workflow events, a run-specific helpdesk proof panel, success/blocked states, and stale-result clearing. A token-format regression was fixed by adding a guaranteed alphabetic marker. Full suite: 37 passed; required `pytest --last-failed`: 37 passed; evaluation: 20/20 planted instances detected/restored, zero false positives/leakage, p50 0.104 ms, p95 0.286 ms over 7 synthetic cases. Streamlit printed `http://127.0.0.1:8502`, but PowerShell could not connect to loopback from this execution environment; AppTests cover both routes and the blocked flow. Next: verify browser access and rehearse success/blocked paths on the actual judging machine. Veil still cannot guarantee automatic discovery of every secret; exact custom values must be listed when outside its recognizers. Keep all data synthetic and call tokens reversible pseudonyms, not encryption.

## 10. Decision/progress log

- 2026-10-09: Chose Veil as a local-first reversible PII gateway with a mock tool, request-scoped token vault, egress verification, trusted-path restoration, and measurable synthetic evaluation.
- 2026-10-09: Chose Python + FastAPI + Streamlit to keep the MVP in one language and avoid paid services.
- 2026-10-09: Setup check found spaCy's compiled extension blocked by Application Control in this environment. Revised the runnable baseline to pure-Python recognizers and kept Presidio optional; do not weaken/bypass the system policy.
- 2026-10-09: Created `.venv` with bundled Python 3.12.14. Installing into the venv initially hit a restricted temp-folder issue; using `work/pip-tmp` and `work/pip-cache` resolved it. Installed base requirements; `pip check` and core imports pass.
- 2026-10-09: Completed the gateway, mock tool, egress verification, trusted-path restoration, Streamlit walkthrough, seven-case synthetic benchmark, README, and benchmark snapshot. Added structured name-field context support and egress checks for JSON keys/tool name. Final automated suite: 18 passed; no broken package requirements.
- 2026-10-09: Packaged the source and handoff docs in `outputs/veil-mvp-source.zip`; verified the ZIP opens and all 22 archived files pass integrity checks.
- 2026-10-09: Reworked the Streamlit screen for nontechnical reviewers: guided three-step flow, simpler sample names, optional advanced JSON/details, plain-language safety status, and a benchmark scorecard. Added tests for the result explanation, scorecard labels, and loading the correct sample after switching. Configured pytest to collect only the main `tests/` folder because the packaged source copy caused duplicate-module collection errors. Verification: 21 tests pass; the synthetic benchmark reports 20/20 detection/restoration and zero leakage/false alarms.
- 2026-10-09: Added a deterministic local agent and simulated campus helpdesk ticket lookup for the judging story. The tool receives the ticket ID and tokenized contact details; it echoes tokens in its response so Veil restores the synthetic name, email, and phone before the agent replies. Added a clearly labeled blocked-path demonstration with a test-only/demo-only injected first-scan miss, proving the egress verifier blocks before tool dispatch. Added the on-screen four-step timeline and tests for both the success and blocked paths. Updated README with uv setup/run commands and the two-minute judging script. Verification: `uv run --no-project --python .\.venv\Scripts\python.exe python -m pytest -q` → 26 passed; `uv run --no-project --python .\.venv\Scripts\python.exe python -m veil.evaluation` → 7 cases, 20/20 planted details detected, 0 false positives, 0 leakage, 20/20 token occurrences restored, p50 0.094 ms, p95 0.207 ms. Benchmark remains synthetic and limited.
- 2026-10-09: User requested that project setup and run instructions use standard Python/pip rather than uv. Updated README and benchmark instructions to use Python's built-in venv, pip, and direct Python commands. Verified using `.venv\Scripts\python.exe`: `-m pip install -r requirements.txt` completed, `-m pytest --last-failed` → 26 passed, benchmark → 20/20 detected, 0 leakage, 18/18 counted token occurrences restored, p50 0.100 ms, p95 0.219 ms, and Streamlit started locally at `http://127.0.0.1:8501`. These verification commands used Python/pip without uv. The clean `py -3.12 -m venv .venv` setup command was not run because this workspace already has a working `.venv`.
- 2026-10-09: Expanded Phase 6 in `implementation-plan.md` for a request-driven user → local agent → Veil → helpdesk → Veil restoration → agent answer workflow, with an event-driven animated single-screen UI. Specified the event contract, actual tool-boundary evidence, fail-closed presentation, vault cleanup, no-fake-delay rule, TDD tasks and gates, acceptance checklist, direct Python commands, and copy/paste implementation prompt. No application code was changed in this planning step. Verification: `.venv\Scripts\python.exe -m pytest --last-failed` → 26 passed; `git diff --check` → clean.
- 2026-10-09: Completed Phase 6 task 6.1 test-first. Added a typed request contract for a user message and structured contact details; made the local agent extract/normalize the ticket ID and prepare the lookup call from those values; added a safe missing-ticket-ID error and tests for answer formatting. The new test first failed on the absent interface, then passed after implementation. Verification: `.venv\Scripts\python.exe -m pytest -q tests/test_demo_agent.py` → 4 passed; `.venv\Scripts\python.exe -m pytest -q` → 30 passed. Next action is task 6.2 integration tests and flow wiring.
- 2026-10-09: Completed Phase 6 task 6.2 test-first. Added successful/blocked workflow tests and an observer callback test before wiring the flow. `run_ticket_demo` now accepts the typed user request, prepares the call using the request-driven agent, passes all arguments through `VeilGateway`, captures the actual payload received by the simulated helpdesk, and returns ordered events and final answer. `VeilGateway` now emits progress callbacks for scan, egress, helpdesk dispatch/response, and restoration; the blocked trace has no downstream tool events. Focused tests: 3 flow tests passed; full suite: 33 passed; `git diff --check` clean.\n- 2026-10-09: Completed Phase 6 task 6.3 test-first. Added detector-crash and helpdesk-crash tests first; both failed against the previous uncaught-exception behavior. Gateway now returns blocked/failed receipts, omits unsafe unverified payloads, avoids including exception text in results, emits failure stage events, and never fabricates a tool response. Focused gateway tests: 11 passed; full suite: 35 passed. One initial full-suite run had a transient Streamlit UI test status mismatch; the required `pytest --last-failed` rerun passed that test, and a fresh full run passed all 35. `git diff --check` clean. Next action: Phase 6 task 6.4 UI integration.

- 2026-10-09: Completed Phase 6 task 6.4 test-first. Replaced the two-tab judge-facing UI with one request-driven helpdesk workflow, synthetic message/name/email/phone fields, a four-stage timeline updated by actual workflow callbacks, success/blocked states, reset and stale-result clearing, and an expandable proof panel labeled 'What the helpdesk actually received'. AppTests verify custom inputs, exact captured tokenized tool payload, event order, restored agent answer, and blocked flow with no helpdesk event. During full-suite verification, a random token occasionally matched the phone recognizer; added a deterministic failing regression test and a guaranteed alphabetic marker in generated tokens. Focused UI/payload tests: 8 passed; 200 workflow repetitions: 200 allowed; full suite: 33 passed. Next action: Phase 6 task 6.5 launch rehearsal and handoff.

- 2026-10-09: Expanded the demo to match the user's free-form workflow goal. Test-first changes add a generic support-intake tool path when there is no ticket ID, exact user-marked custom sensitive values, and an echoed response that Veil restores before the agent answers. The UI accepts any synthetic message and optional exact extra values. Added a responsive pulsing event timeline with reduced-motion support; events alone drive state and no delays were added. Updated README and implementation-plan judge instructions. Focused tests: 22 passed; full suite: 37 passed; `pytest --last-failed`: 37 passed; evaluation: 20/20 detected, 0 false positives, 0 leakage, 20/20 restored, p50 0.104 ms, p95 0.286 ms. Streamlit startup printed `http://127.0.0.1:8502`; shell loopback verification failed in this environment, so browser rehearsal remains for the judging machine.

- 2026-10-09: Responded to the user's broader target with a general support-request tool path for messages without a ticket ID, while preserving the existing ticket lookup path. Added optional exact synthetic-value protection: the user lists one value per line; Veil replaces it wherever it occurs and restores the echoed value on the trusted path. Added AppTests and unit/integration tests before implementation. The UI now uses a responsive gradient timeline with active-stage pulse, completed/blocked/failed states, and reduced-motion support; event callbacks drive each update without artificial delays. Updated README and the next-session prompt to describe actual scope and limits. Verification: focused 22 passed; full suite 37 passed; `pytest --last-failed` 37 passed; synthetic benchmark 20/20 detected/restored, 0 false positives/leakage, p50 0.104 ms, p95 0.286 ms. Streamlit starts and prints port 8502, but localhost probing from this shell failed; judging-machine browser rehearsal remains open.
