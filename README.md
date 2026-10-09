# Veil — Privacy Middleware for Agent Tools

Veil is a local-first demo of a privacy layer between an agent and its tools. The user enters a synthetic free-form request and contact details. A deterministic local agent chooses a ticket lookup when a supported ticket ID is present, or submits a general support request otherwise. Veil scans and tokenizes selected PII before dispatch, and a simulated helpdesk records exactly what it received. Veil restores known tokens only on the trusted response path back to the agent.

## What the judging demo shows

- User message plus structured synthetic name, email, and phone fields.
- The local agent preparing a ticket lookup or general support request from the user message.
- Veil scanning, replacing selected detected values with reversible task-scoped tokens, and checking the exact outgoing payload.
- The simulated helpdesk receiving either the ticket lookup key or general support request, with selected details tokenized.
- A tokenized helpdesk response restored by Veil before the agent answers.
- A blocked-path example where egress verification stops the request before the helpdesk is called.
- An expandable proof panel showing **What the helpdesk actually received**.

The local demo agent is deterministic rather than a hosted LLM. A supported ticket ID such as `TICKET-DEMO-1042` selects ticket lookup; any other message selects the general support-request tool. Veil scans arbitrary text/JSON payload content for its selected recognizers: email, phone number, supported synthetic IDs, and some person names. Enter any additional synthetic secret in **Other sensitive values to protect**, one exact value per line, and include it in your message. Name detection is limited, and Veil cannot guarantee discovery of every secret unless it is recognized or explicitly listed. The demo uses only fictional data; do not enter real personal or confidential information.

## Setup

Install Python 3.12, then open PowerShell in the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py` is unavailable, install Python 3.12 and use `python -m venv .venv`. If the environment is already prepared, you can run the commands below directly with the project venv. No API keys or hosted models are needed.

## Run the judge demo

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run veil/demo.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints, usually `http://127.0.0.1:8501`. The demo does not need the optional FastAPI server or any external service.

## Two-minute judge walkthrough

1. For the general-input path, enter a made-up request without a ticket ID. Add a synthetic custom secret in **Other sensitive values to protect** and include it in the message. Enter made-up name, email, and phone values in the structured fields. To show ticket lookup, include `TICKET-DEMO-1042` instead.
2. Click **Run workflow**. Follow the stages as they are emitted: agent preparation, Veil scan and egress check, helpdesk call, and response restoration.
3. Point out the answer the agent gives after receiving Veil's restored response.
4. Open **Show the proof from this workflow**. Compare the agent-prepared request with **What the helpdesk actually received**. The ticket ID remains available on the lookup path; selected contact values and any exact custom values are temporary tokens.
5. Click **Show blocked example**. Veil's egress check blocks an intentionally missed synthetic email; the timeline marks the helpdesk and later steps as not reached.
6. If asked about evaluation, run the synthetic benchmark from another terminal:

   ```powershell
   .\.venv\Scripts\python.exe -m veil.evaluation
   ```

   Explain that this is a small synthetic set, not proof of universal detection.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --last-failed
.\.venv\Scripts\python.exe -m veil.evaluation
```

## Architecture

```text
User message and synthetic contact fields
  → deterministic local agent chooses ticket lookup or support intake
  → Veil recursive detector/tokenizer
  → egress verification (fail closed)
  → local simulated helpdesk captures its exact request
  → tokenized response
  → Veil restores known task tokens
  → trusted agent formats the user-facing answer
```

Every tool call passes through `VeilGateway`. A short-lived in-memory token vault is cleared at the end of the workflow. Generated tokens are reversible pseudonyms, not encryption. Audit receipts contain detection metadata and timing, not the original contact values.

The benchmark source is [`data/benchmark.json`](data/benchmark.json), with the latest recorded snapshot in [`benchmark-results.md`](benchmark-results.md). Name recognition has limited coverage, and numeric values can be ambiguous. The egress scan is a second detection pass, not a guarantee against every unknown or obfuscated value.

For project decisions and the current implementation status, see [`context.md`](context.md). For the staged implementation and judge checklist, see [`implementation-plan.md`](implementation-plan.md).
