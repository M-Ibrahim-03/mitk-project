# Veil — Privacy Gateway for Agent Tools

Veil is a local-first hackathon MVP that protects synthetic personal information in agent-to-tool payloads. It scans JSON string values, replaces selected PII with reversible task-scoped tokens, checks the exact tool-bound payload, sends it to an offline mock tool, and restores tokens only on the trusted response path.

## What the MVP demonstrates

- Email, formatted and unformatted phone numbers, a synthetic student ID pattern, and selected person names in natural-language strings and labelled name fields.
- Recursive scanning of JSON objects and arrays while preserving keys, non-string values, and payload shape.
- Reuse of the same token for repeated values inside one task.
- Egress verification of payload values, object keys, and tool name. A failed verification blocks the simulated tool call.
- A local mock tool that captures exactly what it receives and echoes a response for restoration.
- A Streamlit walkthrough and a labelled synthetic benchmark for detection, false positives, leakage, restoration, and latency.

Person-name recognition uses context patterns and a small fictional-name lexicon. It is less comprehensive than a full NLP NER model. The project keeps its baseline pure Python because the current Windows execution environment blocks spaCy's compiled extension under its Application Control policy. Veil does not bypass that policy.

## Setup

### Existing project workspace

The current workspace has a local `.venv` based on Python 3.12.14. In PowerShell, install/update dependencies with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### New machine or checkout

Install Python 3.10 or newer, then from the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the `py` launcher is unavailable but `python` is installed, use `python -m venv .venv` instead. If PowerShell blocks environment activation, invoke `.\.venv\Scripts\python.exe` directly.

## Run locally

Run the API in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn veil.api:app --reload --host 127.0.0.1
```

The API health check is `http://127.0.0.1:8000/health`. The local simulated tool endpoint is `POST http://127.0.0.1:8000/tool-call` with JSON such as:

```json
{
  "tool_name": "synthetic_demo_tool",
  "payload": {
    "recipient": "avery@example.test",
    "message": "Contact Avery Example at +91 00000 00000."
  }
}
```

Run the interactive demo in another terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1
```

Run automated checks and the synthetic benchmark:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m veil.evaluation
```

## Architecture

```text
Agent payload
   → recursive detector and tokenizer
   → egress guard (fail closed)
   → local simulated tool (captures tokenized request)
   → response token restoration
   → trusted agent response
```

The token map stays in memory in a task context and is cleared when the task ends. Audit records contain entity type, confidence, JSON path, token, status, and timing; they do not contain original values. The gateway supports multiple tool calls under one task context so repeated values keep the same token.

## Evaluation

The benchmark cases are in [`data/benchmark.json`](data/benchmark.json). Each PII occurrence is labelled by JSON path, exact synthetic value, and entity type. The benchmark calculates detection recall, false positives/precision, exact planted-value leakage at the mock-tool boundary, token restoration accuracy, and p50/p95 privacy-processing latency.

See the dated [benchmark snapshot](benchmark-results.md) for the latest recorded run.

Results apply only to this small synthetic dataset and do not establish universal PII detection. Digit-only phone values are ambiguous and may be false positives. Name recognition can miss names without supported context or lexicon coverage. The egress scan is a second detection pass; it is not a mathematical guarantee against every unknown or obfuscated value.

## Privacy and cost

Use synthetic values only. The MVP has no paid AI API or external tool integration. It runs locally and needs no account or hosting. Do not enter real personal or confidential information into the demo.

See [`context.md`](context.md) for the source of truth and agent handoff history. See [`implementation-plan.md`](implementation-plan.md) for the staged AI IDE prompts, verification checklists, and demo script.
