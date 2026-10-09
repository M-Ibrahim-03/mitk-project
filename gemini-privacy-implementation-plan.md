# Veil: Gemini Agent and Stronger Local Privacy Middleware

**Status:** In progress (2026-10-10). The Gemini adapter, input tokenization, fake-client workflow, server mode selection, and same-run UI evidence are implemented. Live Gemini/browser rehearsal and optional NLP remain outstanding.

### Current execution checkpoint

- Implemented `veil/gemini_agent.py`: one allowlisted helpdesk function proposal, strict argument validation, disabled SDK automatic function execution, bounded text/output size, server-only API key, and generic provider errors that omit prompt text.
- Implemented Gemini-mode workflow: Veil tokenizes the user message before Gemini, checks the generated proposal again through `VeilGateway`, scans/verifies the tokenized helpdesk response before Gemini continuation, then restores known tokens locally after Gemini's draft.
- FastAPI selects `VEIL_AGENT_MODE` from backend environment, requires `GEMINI_API_KEY` before queueing Gemini runs, and preserves the selected mode in run snapshots. `.env` is ignored; `.env.example` contains no key.
- React chat/workflow shows the selected mode, protected Gemini prompt, tokenized draft, and restored answer.
- Fake-client tests, Python regression suite, frontend tests/build pass as recorded in `context.md`. The latest user-supplied key is stored only in ignored local `.env` and should be revoked after the agreed temporary demo use. Live provider usage is not verified: `google.genai` is not installed in the current environment, and local API access is blocked by the sandbox.
- The optional Presidio/spaCy layer remains deferred because this Windows environment blocks spaCy native extensions. The active detector remains local and pattern-based with documented limits.

**Purpose:** Extend the existing Veil demo with a real model-driven agent while keeping Veil—not the model—in charge of privacy checks and tool execution.

## 1. Goal

Make the hackathon demonstration visibly match the problem statement:

1. A real AI agent interprets a synthetic user request and proposes a tool call.
2. Veil intercepts and validates the tool-bound request before dispatch.
3. The simulated helpdesk receives a protected request, never the planted originals covered by the test case.
4. Veil keeps a task-scoped reversible mapping and restores values only on the trusted, local response path.
5. Detection, leakage, restoration, and processing time have measurable, repeatable synthetic tests.

The project already has the chat page, six-stage evidence workflow, FastAPI run API, deterministic agent, Veil gateway, offline helpdesk, token vault, and evaluation harness. This plan extends those parts; it does not recreate the MVP or replace the simulated tool with a real service.

## 2. Proposed design decisions

These were proposed defaults and are now confirmed for implementation:

- **Gemini is an optional agent provider.** The existing deterministic agent remains available for fully offline runs. The selected mode is explicit; a missing key or failed Gemini call must not silently switch modes.
- **Gemini receives only locally protected synthetic content.** Veil scans and tokenizes the user message before any Gemini request. Never send original personal or confidential data to the model. This adds a model-input privacy boundary in addition to the required agent-to-tool boundary.
- **Detection stays local.** Do not ask Gemini or another hosted model to inspect raw text for PII. Use local deterministic recognizers, with an optional local NLP recognizer if it can be installed and run in the target environment.
- **All tools remain local and allowlisted.** Gemini may propose a declared helpdesk function, but FastAPI validates the function name and arguments and calls it through `VeilGateway`. Do not enable model-side automatic function execution or hosted search/tools.
- **The API key stays on the backend.** Read it from an environment variable or a local secret file excluded from Git. Never accept it in the React request, include it in frontend assets, log it, or ask the user to paste it into chat.
- **Synthetic data only for the hackathon demo.** A Gemini-mode run makes a network request, so the user-visible notice and README must say that only synthetic, tokenized input is sent to Gemini.
- **No universal-detection claim.** A stronger detector means broader measured coverage, not proof that all PII or secrets will be found.

Local pre-scanning cannot prove that arbitrary free-form input contains no PII: the detector itself has blind spots. Gemini mode must therefore remain explicitly synthetic-only for this hackathon. The plan's tokenization boundary protects known, detected values and reduces exposure; it is not permission to send real personal or confidential data to a hosted model.

Google describes function calling as an application-mediated flow: the model returns a function name and arguments, and the application is responsible for executing the function. This is the seam where Veil must remain in control. See [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling). Google also recommends keeping API keys confidential and making calls through a backend rather than exposing keys in client code. See [Gemini API key security](https://ai.google.dev/gemini-api/docs/api-key).

## 3. Target architecture

```text
Browser: synthetic original message
  │
  ▼
FastAPI creates one run and one task-scoped TokenVault
  │
  ├─ Veil local input scan + tokenization
  │      └─ original remains local for the evidence view and final restoration
  │
  ├─ Gemini agent receives only the tokenized prompt
  │      └─ returns an allowlisted helpdesk function call with structured args
  │
  ├─ VeilGateway scans/tokenizes the proposed call, checks policy and verifies egress
  │      └─ block/error → stop; no helpdesk call
  │
  ├─ Offline simulated helpdesk captures exactly the protected payload and replies
  │
  ├─ Veil scans/tokenizes the tool response before returning it to Gemini
  │      └─ never restore originals before model continuation
  │
  ├─ Gemini drafts a final answer using only tokenized context
  │
  └─ Veil restores known tokens locally, then returns the answer to the browser
```

The same `run_id` must identify the request, model interaction, Veil decisions, exact captured helpdesk payload, model answer, restoration, and final response. The viewer must continue to read evidence for that run; it must never create another run on mount, reload, or reconnect.

### Why protect the prompt too?

If the original message is sent to Gemini first, Veil can still protect the simulated helpdesk call, but the original has already left the application. The proposed design therefore protects the message before Gemini sees it and independently checks the model's tool-call arguments before the helpdesk sees them. This gives the demo two clearly named boundaries:

- **Model-input boundary:** original → locally tokenized prompt → Gemini.
- **Tool-egress boundary:** agent-proposed arguments → Veil verification → simulated helpdesk.
- **Tool-response boundary:** helpdesk result → local scan/tokenization → Gemini continuation.

The first scan must not replace the gateway scan. Model output is untrusted: it can change, add, omit, or rearrange fields, so every proposed call still passes through Veil and a strict tool schema.

## 4. Data and token lifecycle

1. Start a new `TaskContext` before processing the message. Its vault is unique to that run.
2. Run the local detector on the input text and any structured fields. Replace detections with task-scoped typed tokens.
3. Keep the original only in local run state for the user-visible trace and eventual restoration. Do not put it in Gemini request content, model history, error messages, application logs, or analytics.
4. Pass the protected text to Gemini. Keep all conversation history tokenized; do not append the original message in a later turn.
5. Parse the model's proposed call as data. Validate its tool name and arguments against a Pydantic schema and the allowlist.
6. Pass the call through `VeilGateway`. The gateway scans for newly introduced sensitive values, checks known originals and token invariants, applies a second egress check, then dispatches only on success.
7. Scan the helpdesk response locally before it is returned to Gemini. Reuse the task vault for newly detected values, verify the protected response, and fail closed if inspection fails. This protects against a future tool returning un-tokenized sensitive data.
8. Pass only that protected tool response to Gemini. Do not use the current restored response field as model context.
9. Once Gemini returns the final answer, restore only exact tokens present in the run's vault, locally. Do not let arbitrary model-provided strings create mappings or trigger restoration of unknown tokens.
10. Clear the vault in `finally` on success, block, timeout, parsing error, model error, and tool error.
11. Keep the current short-lived, bounded in-memory run record for the local evidence view. Document that it contains the original synthetic request and expires; it is not a production data store.

Tokens remain reversible pseudonyms, not encryption. The vault must never be sent to Gemini, the helpdesk, logs, or the browser.

## 5. Detection and protection design

### 5.1 Preserve the current detector behind a stable interface

Keep `veil/detection.py` as the baseline and make the detector replaceable through a small interface returning spans, entity type, confidence, and source/recognizer metadata. Do not let the gateway depend on a specific detector library. Preserve existing recognizers and regression fixtures before expanding coverage.

### 5.2 Add layered local recognition

Use a hybrid, explainable pipeline rather than a single “AI detector”:

1. **Safe normalization for candidate matching:** detect common Unicode compatibility forms, separators, whitespace, punctuation, and zero-width characters. Preserve a reliable mapping to original character offsets so replacement does not corrupt surrounding text. Never normalize the actual payload destructively.
2. **Validated pattern recognizers:** format checks, checksums, contextual labels, and custom region-specific patterns for email, phone, government identifiers, payment data, bank routing/account values, and other chosen types. Add each type only with synthetic positive and negative fixtures.
3. **Context and field hints:** use surrounding words and JSON field names to raise or lower confidence. Scan nested JSON values and explicitly define policy for sensitive object keys. Since changing a key can break a tool schema, the safe default for a detected sensitive key is to block for review rather than silently rewrite it.
4. **Local NLP/NER adapter:** evaluate Microsoft Presidio Analyzer with a locally installed NLP engine for names, locations, and less structured entities. Presidio supports configurable recognizers combining patterns, rules, context, and NLP models; it still has false positives and false negatives. See [Presidio Analyzer documentation](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/index.md) and [recognizer guidance](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/developing_recognizers.md).
5. **Secret detection as a separate category:** consider common API-key/token and credential formats. These are sensitive secrets, not necessarily PII; report them separately in the benchmark and UI rather than inflating PII accuracy.
6. **Span merge and conflict policy:** merge duplicates and overlaps deterministically, preserve exact offsets, reuse a token for repeated exact values within a run, and report which recognizer produced each finding without logging the value.

### 5.3 Model-feasibility gate

The current project notes that this Windows environment blocked spaCy's native extension and says not to make Presidio/spaCy mandatory. Therefore:

- First run a small dependency/model feasibility spike in the existing `.venv` without changing the default installation path.
- Confirm the selected NLP model loads locally, has no runtime network dependency, and can process synthetic examples.
- If it works, expose it as an optional local detector extra/configuration and pin/document the model setup.
- If it does not work, retain the deterministic recognizer path and record the blocker. Do not fall back to a hosted PII detector or claim the NLP layer is active.

### 5.4 Policy and fail-closed egress

- Maintain an explicit allowlist of tool names and versioned input schemas. Never execute arbitrary model-selected names or arguments.
- Egress verification checks known originals, token-vault invariants, sensitive tool-name/argument fields, and supported recognizers. A detector or verifier exception blocks dispatch.
- Before any tool result is sent to Gemini, scan/tokenize the response and verify it using the same task context. The LLM must never receive the gateway's restored-response artifact.
- Distinguish **allowed**, **blocked**, and **failed** in the audit. A blocked request has zero tool calls; it is not a successful zero-leak tool call.
- Do not equate “second scan passed” with proof of absence. It is a guard against supported residual patterns and known originals.
- Validate response shape and bound model/tool call count, payload size, depth, and per-run duration. Add rate limits before any non-local deployment.

## 6. Gemini agent integration

### Provider contract

Define a small agent protocol so the flow can use either `LocalDemoAgent` or `GeminiAgent` without changing the gateway:

- `plan(protected_message, tool_declarations) -> AgentToolCall | AgentAnswer`
- `continue_after_tool(protected_history, tokenized_tool_result) -> AgentAnswer`

Adapt the exact method names to existing types after inspecting the current code. The Gemini adapter should use Google's supported Python GenAI SDK and structured function declarations. Return parsed tool-call data; do not hand Python callables to an automatic execution feature. The app validates and executes calls itself.

### Agent behavior and restrictions

- Declare only the simulated helpdesk functions and exact argument schemas.
- Allow one tool call for the initial MVP; reject unknown functions, invalid arguments, out-of-range values, extra fields, and repeated call loops.
- Pass tokenized user text and tokenized tool responses only. System instructions are not a security control; Veil's schema, policy, and egress checks are.
- Treat model text and tool results as untrusted input. Do not allow the model to enable web search, code execution, or additional tools.
- On missing credentials, timeout, quota error, malformed response, or provider error, fail visibly with no tool call. Offline deterministic mode is selected explicitly; there is no silent switch that makes a judge believe Gemini ran.
- Set request timeouts and bounded retries. Do not retry tool side effects automatically; the current mock is safe, but this rule matters if tools later change.

### Configuration and key handling

- Backend setting: `VEIL_AGENT_MODE=deterministic|gemini`.
- Backend secret: `GEMINI_API_KEY` (or the current Google-recommended authorization credential when required by the selected account/key type).
- Add `.env` to `.gitignore` if a local dotenv file is used; commit only `.env.example` with an empty placeholder and setup notes.
- Do not put keys in Pydantic request models, React state, Vite variables, browser storage, tests, screenshots, or logs.
- Avoid collecting provider payload dumps in exceptions. Log stage, status, duration, and safe error class only.
- Gemini mode requires network and may consume account quota or incur cost; deterministic mode remains available without network.

## 7. Workflow and UI changes

Keep the single-message chat page and current visual language. Do not add contact-detail forms, settings clutter, or a new dashboard. Make only changes required to explain the real agent and privacy boundaries:

- Show which agent mode ran: Gemini or offline deterministic.
- Add evidence for the tokenized prompt sent to the model, without showing raw content in network/debug logs.
- Show Gemini's actual prepared function name and arguments before the gateway check.
- Show Veil's protected payload, findings by category, and explicit egress decision.
- Show the exact payload captured by the simulated helpdesk and its tokenized response.
- Show the tokenized final agent response, then the locally restored answer.
- Add a blocked/failed explanation with later tool and response steps clearly marked “not reached.”
- Update connector/event mappings for any added stage while keeping all nodes visible and animations tied to actual events.
- Keep the original synthetic message only in local run evidence, with the existing 15-minute in-memory retention documented.

Suggested evidence sequence (combine adjacent cards if the current layout becomes too long):

1. User request (local synthetic original).
2. Veil input scan and protected model prompt.
3. Gemini agent plan and proposed function call.
4. Veil tool-call scan, protected payload, and egress decision.
5. Exact helpdesk receipt and tokenized reply, followed by Veil's response scan.
6. Gemini response using tokenized context.
7. Veil local restoration and final answer.

## 8. Test-first implementation sequence

Use vertical red → green slices. Each behavior change starts with a test at the public interface; never write a large batch of speculative tests before implementing the first slice. Unit tests use synthetic data and fake clients only. No test should call Gemini or the internet.

### Slice 0 — Baseline and configuration

- Record current git state and run the existing focused suites before touching code.
- Test explicit mode parsing, missing-key behavior, and safe redaction of configuration/errors.
- Add no real credentials. Verify `.env` cannot be staged accidentally by documented setup and tests/review.

### Slice 1 — Detector seam and one new detector layer

- Public seam: detector accepts text plus field hint and returns typed spans with valid offsets.
- Add one recognizer/normalization case at a time with synthetic positive and negative examples.
- Ensure overlapping recognizers do not duplicate replacements or damage adjacent text.
- Only after baseline tests pass, add the optional local NLP adapter and its offline smoke test.

### Slice 2 — Input tokenization and vault lifetime

- Public seam: starting a task and protecting a message returns protected text and detection metadata while retaining the mapping only in that task context.
- Test repeated values, punctuation, normalized variants, Unicode separators, and restoration of exact known tokens.
- Test that a second task cannot restore the first task's values and cleanup runs on exceptions.

### Slice 3 — Gemini adapter with fake client

- Public seam: agent adapter maps a fake provider function-call response to the app's validated `AgentToolCall` and maps a final tokenized response to `AgentAnswer`.
- Test no-function response, unknown function, malformed JSON/schema, multiple calls, provider exception, timeout, and prompt content containing tokens but not synthetic originals.
- Test that the adapter itself never dispatches the tool.

### Slice 4 — Gateway and tool boundary

- Public seam: gateway call against a capture tool records exactly what the tool received.
- Assert planted synthetic originals are absent, tokens survive in the expected fields, schema meaning is preserved, and restoration works.
- Inject a detector miss/error and assert blocked status plus zero mock calls.
- Assert arbitrary tool names, extra fields, and malformed nested payloads do not bypass the allowlist/schema.
- Preserve separate `tool_response` (tokenized for Gemini) and restored response (local/UI only); do not restore before model continuation.

### Slice 5 — End-to-end run and run evidence

- Public seam: workflow runner with fake Gemini client emits truthful events and returns one run ID.
- Assert all UI evidence belongs to that run and the exact mock-tool capture is shown.
- Success, blocked, failed, timeout, replay/reconnect, and missing-key states are covered.
- Assert the blocked trace does not contain a fabricated helpdesk result or final answer.

### Slice 6 — Frontend mode and workflow rendering

- Keep the message-only form.
- Test mode/status label, answer/error states, no duplicate submissions, same-run navigation, and all workflow stages.
- Do not expose or submit an API key from the browser.
- Verify blocked/failed branches stop connector animation at the real boundary.

### Slice 7 — Evaluation and presentation gate

- Run the expanded synthetic benchmark and record exact command, corpus revision, counts, category metrics, and machine/runtime.
- Rehearse with an explicitly configured key and synthetic text only. Inspect the tokenized Gemini prompt in a fake client test; inspect the actual payload captured by the mock tool in the real local run.
- Rehearse the offline deterministic path and one forced blocked path.
- Do not report browser or Gemini integration success unless performed in that environment.

## 9. Evaluation plan

Expand `data/benchmark.json` and the evaluator in controlled increments. Include both natural-language and structured payloads, nested values, repeated spans, valid/invalid checksums, context/no-context pairs, Unicode and spacing variants, positive and benign lookalikes, and explicit hard cases. Keep all content fictional and synthetic.

Report at least:

- **Detection recall:** correctly detected planted spans / all planted spans, by category and overall.
- **Precision:** correct detections / all detections; report false positives separately.
- **Exact leakage:** count of planted original occurrences in the exact payload captured by the simulated helpdesk, by category and case.
- **Restoration:** exact token-to-original matches / tokens expected to restore. Also report the raw numerator and denominator; do not compare against planted-instance count if some instances were never tokenized.
- **Latency:** local detector/tokenization/egress-check p50 and p95, sample count, payload size, and whether NLP model startup is excluded. Report Gemini network/model latency separately; never fold remote latency into Veil overhead.
- **Blocked behavior:** number of unsafe cases stopped before any helpdesk call.
- **Limits:** corpus size, language, supported country identifiers, and known misses.

Targets for the supported corpus should be agreed before tuning. A reasonable gate is zero planted-original leakage and 100% exact restoration for all allowed cases in that corpus, while reporting recall and false-positive rates honestly. These are test-set results, not a guarantee for arbitrary traffic. Keep a small holdout set out of detector tuning if time allows.

## 10. Proposed code and document touch points

Inspect current source before changing each file; these are expected seams, not a mandate to refactor everything:

- `veil/detection.py` — preserve current baseline and add/route recognizers behind a stable detector interface.
- `veil/payload.py` — normalization-aware span replacement, nested structured scanning, key policy, and egress verification.
- `veil/token_vault.py` — task-scoped map lifecycle and exact-token restoration.
- `veil/gateway.py` — allowlisted/schema-validated tool dispatch; retain tokenized response separately from local restored result.
- `veil/demo_agent.py` — agent protocol and deterministic implementation.
- `veil/gemini_agent.py` — new Gemini adapter; no direct tool execution.
- `veil/demo_flow.py` — local input protection, provider selection, gateway interaction, tokenized model continuation, final local restore, truthful events.
- `veil/api.py` — safe mode/config integration and bounded workflow errors; key never appears in request or response.
- `veil/run_registry.py` — keep same-run replay and current bounded in-memory policy; never store the vault.
- `frontend/src/pages/ChatPage.tsx` and `frontend/src/api.ts` — preserve message-only UI; display selected agent mode, no key field.
- `frontend/src/pages/WorkflowPage.tsx` — render actual added boundaries and artifacts for one run.
- `frontend/src/styles.css` — small scoped changes only where the evidence sequence needs them.
- `tests/` and `data/benchmark.json` — synthetic test cases and measurable acceptance evidence.
- `.gitignore`, `.env.example`, `requirements.txt`, `README.md`, and `context.md` — safe config/setup, accurate claims, and checkpoint.

Do not rewrite the existing MVP, change the chat page into a contact form, send data to a real helpdesk, or add unrelated UI features.

## 11. 24-hour execution schedule

This is a time-box suggestion, not a promise that model setup will be trivial. Keep a working demo at each gate.

| Window | Work | Exit gate |
|---|---|---|
| 0–1 h | Confirm data boundary, mode selection, tool schema, and test seams; capture baseline status/tests | Existing workflow remains reproducible; plan decisions settled |
| 1–4 h | Detector seam, selected recognizers, synthetic positive/negative fixtures | Focused detector tests pass; no claim of universality |
| 4–6 h | Local NLP feasibility spike in isolated environment | Model loads offline, or optional NLP is deferred with reason |
| 6–8 h | Input tokenization and vault lifetime | Original synthetic text is absent from prompts passed to the fake Gemini client |
| 8–11 h | Gemini function-call adapter and fake-client tests | Structured tool calls are parsed but never executed by adapter |
| 11–14 h | Gateway policy, tokenized tool-response continuation, local final restore | Capture tool proves no planted original crossed the tool boundary |
| 14–17 h | Run API and truthful workflow event/evidence updates | Chat and workflow use the same run, success and blocked cases display honestly |
| 17–19 h | Expanded benchmark and report | Detection, leakage, restoration, false positives, and latency are reported with denominators |
| 19–22 h | Fresh browser rehearsal with synthetic data; test offline fallback and blocked path | No stale API process; exact same-run payload inspected |
| 22–24 h | Fix only demo-blocking issues, update README/context, prepare judge narration | Setup and limitations documented; no unverified claims |

If time gets tight, the minimum credible result is Gemini tool selection plus server-side key configuration, the existing local detector, a fake-client test suite, the gateway capture proof, and clear disclosure of detector limits. Treat local NLP as a stretch goal unless it passes the feasibility gate early.

## 12. Risks and explicit non-goals

- **No universal PII detection:** hybrid NLP and rules still miss values and make mistakes. Fail closed for detection errors; measure false positives and misses.
- **Cloud boundary:** Gemini mode requires a network request. Only send locally tokenized synthetic content for this hackathon. If a future deployment needs real data, reassess provider terms, retention, consent, jurisdiction, and organization policy first.
- **Token semantics:** the mock helpdesk can demonstrate token pass-through and echo. A real helpdesk that must identify a person cannot use an opaque token unless a trusted mapping/lookup design is agreed.
- **Prompt injection/model behavior:** the model may propose unexpected calls or malformed arguments. Tool allowlists, schemas, per-run call limits, and Veil checks enforce policy; system prompts alone do not.
- **Key exposure/cost:** leaked keys can consume quota or incur charges. Server-only secrets, key restriction, usage limits, and no secrets in logs are required.
- **API access control:** the current local API is a demo and run IDs are not authentication. Do not expose it to a shared/public network without authentication, per-user run authorization, rate limits, and appropriate storage/transport controls.
- **Production hosting, real external tools, multi-tenant storage, durable vaults, encryption/key management, and legal/compliance certification are out of scope for this 24-hour prototype.**

## 13. Definition of done

- [ ] Gemini mode demonstrably produces a real model-selected helpdesk function call; provider mode is clearly visible.
- [ ] For every supported planted value in the acceptance corpus, the fake-client capture proves Gemini receives tokenized prompt/history and tokenized tool results with no original test value. This does not prove arbitrary text is PII-free.
- [ ] The adapter returns function-call data only; every tool call passes through the gateway and allowlist/schema checks.
- [ ] The mock helpdesk's captured payload contains tokens in place of all supported planted PII values for the acceptance corpus.
- [ ] A forced residual detection and detector exception both block before helpdesk dispatch.
- [ ] Gemini receives no restored originals; the user receives the correctly restored final answer locally.
- [ ] Vault state is cleared on all success and failure paths; different runs cannot cross-restore tokens.
- [ ] Fake Gemini tests run without network/API key; the deterministic offline mode still passes existing tests.
- [ ] Benchmark reports per-category detection, false positives, exact leakage, restoration numerator/denominator, local overhead percentiles, and corpus limitations.
- [ ] A fresh browser rehearsal proves chat and workflow pages show the same successful run, plus one blocked run.
- [ ] README and `context.md` identify Gemini mode as networked, deterministic mode as offline, synthetic-only data policy, setup, results, and known limitations.
- [ ] No API key, raw value, or provider request containing originals appears in source control, frontend assets, logs, or test output.

## 14. Confirmed implementation decisions

The user approved these choices by asking to execute the plan. Continue with the test-first sequence and do not ask for confirmation again unless a material new choice arises:

1. Gemini receives **only locally tokenized synthetic data**, and real personal/confidential data is never submitted.
2. Detection remains local and hybrid; Presidio/local NLP is optional if the environment can run it, with the current detector retained as fallback.
3. Gemini proposes calls, FastAPI validates them, and Veil alone dispatches the local simulated helpdesk; deterministic mode remains explicitly selectable.
4. Tests use four seams: detector output, exact mock-tool capture, fake Gemini adapter without network, and same-run API/workflow evidence.

## References

- [Gemini API function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini API key security](https://ai.google.dev/gemini-api/docs/api-key)
- [Presidio Analyzer](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/index.md)
- [Presidio recognizer development guidance](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/developing_recognizers.md)
