# Veil MVP — Implementation Plan and AI IDE Prompts

Read `context.md` first. It is the source of truth for scope, constraints, architecture, status, and decisions. This plan provides the staged prompts and checklists.

## Recommended way to work

Use **Codex in this workspace as the primary coding agent** because this chat and files already share the project directory. Antigravity or Claude Code can also work, but use one writer at a time to avoid conflicting edits. Before switching tools, save the latest status and next action in `context.md`; the next agent must read that file first.

Do not ask an agent to build the whole product in one pass. Give it one phase prompt, inspect the diff and run the checklist, then proceed.

### Current handoff status

Phases 0–5 are implemented in this workspace. The prompts below document how the MVP was built and are useful for controlled changes or a fresh implementation. If continuing from this workspace, first use the handoff prompt below; do not rerun Phase 0 or overwrite the existing implementation.

```text
Read context.md and implementation-plan.md before editing. The Veil MVP is already implemented. Inspect the current files and run the documented checks first. Do not recreate the scaffold or replace working files. Report the current test/benchmark status, then make only the specific follow-up change requested by the user. Keep synthetic-only data, no external services, and update context.md at the end.
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

1. “This synthetic agent request contains an email, phone, name, and account ID in both text and nested JSON.”
2. Run Veil; point out detections and paths.
3. Show that repeated values map to the same temporary token.
4. Open the mock-tool receipt and show the exact sanitized payload; show the zero-leak result.
5. Show the mock response returning a token, then the trusted response restoring it.
6. Finish on the benchmark card: detection, leakage, restoration, and latency, plus one known limitation.
