# Veil synthetic benchmark results

## Latest run

Run date: 2026-10-10
Command: `.venv\Scripts\python.exe -m veil.evaluation`
Runtime: Python 3.12.14, Windows 11 10.0.26200, AMD64

| Split | Cases | Negative controls | Planted spans | TP | FP | FN | Precision | Recall | F₂ | Literal leaks at tool | Restoration | Timed samples | Warmups | p50 / p95 added latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Development | 33 | 3 | 49 | 49 | 2 | 0 | 96.08% | 100% | 99.19% | 0 | 100% | 3,300 | 660 | 0.129 / 0.349 ms |
| Held out | 26 | 3 | 26 | 26 | 2 | 0 | 92.86% | 100% | 98.48% | 0 | 100% | 2,600 | 520 | 0.117 / 0.251 ms |

Per-entity results are exact-span matches. Each cell is **TP / FP / FN; precision / recall / F₂**.

| Entity type | Development | Held out |
| --- | --- | --- |
| AADHAAR | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| BANK_ACCOUNT | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| EMAIL | 12 / 0 / 0; 100% / 100% / 100% | 4 / 0 / 0; 100% / 100% / 100% |
| IBAN | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| IFSC | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| PAN | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| PAYMENT_CARD | 2 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| PERSON | 8 / 0 / 0; 100% / 100% / 100% | 3 / 0 / 0; 100% / 100% / 100% |
| PHONE_NUMBER | 8 / 2 / 0; 80% / 100% / 95.24% | 3 / 2 / 0; 60% / 100% / 88.24% |
| STUDENT_ID | 6 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |
| UPI_ID | 3 / 0 / 0; 100% / 100% / 100% | 2 / 0 / 0; 100% / 100% / 100% |

The independent canary scan searched every exact captured simulated-tool receipt recursively, including object keys and values, for planted originals. It found zero literal leaks in both splits. A separate fault-injected blocked-path check missed one synthetic email on the first scan, then confirmed the egress check blocked dispatch: **0 tool calls, 0 receipts**.

Latency measures the gateway's sanitize and egress-verification interval only. Each case received 20 warm-up calls and 100 measured calls. It excludes the simulated tool, response restoration, Gemini, and network time. Payload sizes ranged from 29–171 bytes (development; median 59) and 36–135 bytes (held out; median 48.5). Re-run on the judging machine for its own latency figures.

The two phone false positives per split come from benign numeric lookalikes, including a 10-digit reference and an invalid card-shaped number. This is the expected trade-off of broad phone patterns and is a known failure case. The held-out data is a fixed synthetic corpus checked into the repository, not an external or blinded judge benchmark. A 100% recall result applies only to these planted spans and formats; it does not imply universal PII detection.

## Previous snapshot

The earlier 8-case snapshot on 2026-10-10 measured 22/22 planted spans, zero false positives, zero planted originals at the mock tool, 22/22 restored occurrences, and p50/p95 0.490/1.206 ms from 8 timing samples. That small run covered only EMAIL, PERSON, PHONE_NUMBER, STUDENT_ID, and UPI_ID. The expanded run above supersedes its coverage and latency methodology; timings are machine- and run-dependent.
