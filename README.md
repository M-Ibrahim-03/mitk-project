# Veil — Privacy Middleware for Agent Tools

Veil is a local-first demo of a privacy layer between an agent and its tools. The React chat accepts a synthetic free-form ticket request, but it only processes tickets present in the local helpdesk. The current valid ticket is `TICKET-DEMO-1042`. Gemini mode uses a real Gemini agent to propose the allowlisted ticket lookup. Before Gemini receives a prompt, Veil tokenizes selected values locally. Veil validates the proposal, protects it before egress, and routes it through the offline simulated helpdesk. Gemini receives protected context; Veil restores known tokens locally after the model drafts its answer.

## What the judging demo shows

- One synthetic free-form ticket request, with no separate contact-details form.
- The selected agent preparing a lookup for the valid local ticket `TICKET-DEMO-1042`.
- Veil scanning, replacing selected detected values with reversible task-scoped tokens, and checking the exact outgoing payload.
- The simulated helpdesk receiving the ticket lookup and message with selected details tokenized.
- A tokenized helpdesk response restored by Veil before the agent answers.
- A blocked-path example where egress verification stops the request before the helpdesk is called.
- An expandable proof panel showing **What the helpdesk actually received**.
- A separate Streamlit example that sends nested synthetic JSON through the reusable gateway and displays the exact captured tool receipt. It does not relax the React chat's valid-ticket intake.

Veil scans text and JSON payload content for selected patterns: email, phone, contextual names, supported synthetic IDs, labeled Aadhaar and bank-account numbers, checksum-valid payment cards and IBANs, PAN, and IFSC. Detection is limited and can miss arbitrary, misspelled, or obscured secrets. Use fictional data only; do not enter real personal or confidential information. Gemini mode makes network requests, but the tool remains simulated and local. The legacy Streamlit fallback remains deterministic.

For the React ticket flow, a valid ticket must both match `TICKET-{CATEGORY}-{4 DIGITS}` and exist in the local simulated helpdesk. Only `TICKET-DEMO-1042` is currently seeded; malformed, unknown, missing, or ambiguous ticket IDs are rejected before an agent or tool call.

## Setup

Install Python 3.12, then open PowerShell in the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py` is unavailable, install Python 3.12 and use `python -m venv .venv`. If the environment is already prepared, you can run the commands below directly with the project venv. The default deterministic mode needs no API key or network access.

### Optional Gemini mode

After installing requirements, copy `.env.example` to `.env`, set `VEIL_AGENT_MODE=gemini`, and set `GEMINI_API_KEY` in that ignored local file. The backend loads the key; the browser never receives it. Gemini mode sends locally tokenized synthetic prompts to Google's hosted API. If the provider is unavailable, the key is rejected, the quota is exhausted, or the key is missing, that run continues with a clearly labeled deterministic local fallback. Never enter real personal or confidential data; revoke any key that is exposed after the demo.

## Run the main React demo

Open two PowerShell terminals in the project folder. Start the API in the first:

```powershell
.\.venv\Scripts\python.exe -m uvicorn veil.api:app --host 127.0.0.1 --port 8000
```

Start the frontend in the second:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/`. The backend's selected agent mode appears in the chat and same-run workflow evidence.

## Run the Streamlit fallback

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints, usually `http://127.0.0.1:8501`. The demo does not need the optional FastAPI server or any external service.

## Two-minute judge walkthrough

1. Enter a made-up ticket request containing `TICKET-DEMO-1042` and synthetic sensitive values. This intake remains limited to known local tickets.
2. Click **Send message**. Follow the agent proposal, Veil scan and egress check, local helpdesk call, and response restoration. Use the deterministic mode for a repeatable offline walkthrough. Describe Gemini as a live optional path only after one fresh run visibly completes every stage through the final answer.
3. Open **Show the proof from this workflow** and point to **What the helpdesk actually received**. The ticket ID remains available on the lookup path; detected contact and identifier values are tokens.
4. In the Streamlit fallback, click **Run synthetic structured payload**. Show the nested request and the exact payload recorded by the generic simulated tool to demonstrate gateway reuse outside the ticket route.
5. Click **Show blocked example**. The egress check blocks an intentionally missed synthetic value; the timeline marks the helpdesk as not reached.
6. If asked about measured detection or latency, run the synthetic benchmark:

   ```powershell
   .\.venv\Scripts\python.exe -m veil.evaluation
   ```

   It reports separate development and held-out synthetic results, per-type TP/FP/FN, precision, recall, F₂, receipt leakage, restoration, and repeated middleware-only latency. Explain that the held-out corpus is still a small fixed synthetic set, not a general or blinded PII benchmark.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --last-failed
.\.venv\Scripts\python.exe -m veil.evaluation
```

## Architecture

```text
One synthetic ticket request with a known local ID
  → deterministic offline agent, or optional Gemini agent using a locally tokenized prompt
  → Veil recursive detector/tokenizer
  → egress verification (fail closed)
  → local simulated helpdesk captures its exact request
  → tokenized response
  → Veil restores known task tokens
  → selected agent drafts an answer from tokenized tool context
  → Veil restores known tokens locally for the user-facing answer
```

Every tool call passes through `VeilGateway`. A short-lived in-memory token vault is cleared at the end of the workflow. Generated tokens are reversible pseudonyms, not encryption. Audit receipts contain detection metadata and timing, not the original contact values.

The development benchmark is [`data/benchmark.json`](data/benchmark.json); the separate fixed synthetic held-out set is [`data/benchmark-heldout.json`](data/benchmark-heldout.json). [`benchmark-results.md`](benchmark-results.md) records per-type scores, exact receipt scanning, latency methodology, and known false positives. Name recognition has limited coverage, and numeric values can be ambiguous. The egress scan is a second detection pass, not a guarantee against every unknown or obfuscated value.

For project decisions and the current implementation status, see [`context.md`](context.md). For the staged implementation and judge checklist, see [`implementation-plan.md`](implementation-plan.md).
