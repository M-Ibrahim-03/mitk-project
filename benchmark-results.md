# Veil synthetic benchmark snapshot

Run date: 2026-10-09  
Command: `python -m veil.evaluation`

| Measure | Result |
|---|---:|
| Synthetic cases | 7 |
| Planted PII instances | 20 |
| Detected instances | 20/20 (100%) |
| False positives | 0 (100% precision on this set) |
| Original values reaching the mock tool | 0 |
| Token occurrences restored correctly | 18/18 (100%) |
| Added privacy-processing latency, p50 | 0.100 ms |
| Added privacy-processing latency, p95 | 0.219 ms |
| Latency samples | 7 |

These results are a small, curated, synthetic snapshot from one local run. They measure the supported formats in [`data/benchmark.json`](data/benchmark.json); they do not establish universal PII detection. Person names use context patterns and a small fictional-name lexicon. Digit-only numbers can be ambiguous. Re-run the benchmark on the presentation machine for its latency numbers.
