# Self-Healing Playwright Engine (Lite)

A deterministic, three-tier self-healing locator engine for Playwright (Python Sync API) with MiniLM semantic scoring, hard safety gates, and post-heal SSIM visual and occlusion verification.

## Tier Ladder & Post-Heal Gate

```text
T1: Primary CSS/attribute selector (wait visible)
    └── Hit -> capture baseline fingerprint (role, accessible name, text, bounding box, attr tokens)
    └── Miss -> proceed to T2

T2: Playwright get_by_role(role, name=accessible_name, exact=True)
    └── Single visible match passing hard gates -> emit NATIVE_FALLBACK
    └── Miss / rejected -> proceed to T3

T3: Multi-signal candidate scoring across interactive DOM elements
    ├── Signals: MiniLM cosine (0.55) + ARIA role (0.15) + Gaussian spatial (0.20) + attribute Jaccard (0.10)
    ├── Hard gates: hidden, disabled, role_mismatch, opposite_action, moved_far (spatial < 0.10)
    ├── Acceptance: score >= threshold (0.70 normal / 0.85 high-risk) AND margin >= 0.08
    └── Pass -> synthesize unique selector & emit LOCATOR_DRIFT_HEALED
    └── Fail -> raise HealingRefused (AssertionError) with top-3 candidates (ELEMENT_REMOVED or AMBIGUOUS)

Post-Heal Gate (after any T2 or T3 heal):
    └── Full-page SSIM comparison vs. pre-drift screenshot (ssim_pass=0.985, ssim_major=0.95)
        + DOM center-point hit test (document.elementFromPoint occlusion check)
```

Real pay/delete buttons should use `risk="high"` (threshold `0.85`) while the mock bench uses normal risk.

![Overlay diff](docs/img/overlay_diff.png)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
playwright install chromium

# Lint and run offline test suite (unit, mutation heal/refuse, visual SSIM, audit)
ruff check .
pytest -m "not live" -q

# Enforce heal budget on recorded events
python -m core.audit --dir reports/heal_events --budget 3

# Run synthetic drift benchmark (healing enabled vs. disabled)
python -m benchmarks.run_benchmark --n 60 --seed 99
python -m benchmarks.run_benchmark --n 60 --seed 99 --heal off

# Optional: run live SauceDemo end-to-end tests
pytest -m live -q
```

## Benchmark Results (`--n 60 --seed 99`)

| Metric                                                | `--heal on` | `--heal off` |
| ----------------------------------------------------- | ----------- | ------------ |
| Drift cases (`drift_cases`)                           | 60          | 60           |
| Heal success rate (`heal_success_rate`)               | 91.67%      | 0.00%        |
| Wrong heals (`wrong_heals`)                           | 0           | 0            |
| False refusals (`false_refusals`)                     | 5           | 0            |
| Broken locators (`broken`)                            | 0           | 60           |
| False heals on negatives (`false_heals_on_negatives`) | 0           | 0            |
| Tier split (`T2` / `T3`)                              | 41 / 14     | 0 / 0        |
| Median heal latency (`median_heal_ms`)                | 321.13 ms   | 0.0 ms       |
| p95 heal latency (`p95_heal_ms`)                      | 331.21 ms   | 0.0 ms       |

> Note: Reported heal latency (`median_heal_ms` and `p95_heal_ms`) includes the 300 ms Tier 1 probe timeout before fallback tiers execute.

False refusals (5 of 60): the label was reworded to "Place Order" (2 cases) or "Complete Purchase" (3 cases); 4 of the 5 also changed the tag to `<a>`. The engine refused rather than guess. No thresholds were tuned. Only 2 negative controls were used, so "0 false heals" means 0 of 2.

## Limitations

- **English-only embedding model**: Semantic similarity relies on `sentence-transformers/all-MiniLM-L6-v2` and English opposite-action lexicons.
- **No Shadow DOM or iframes**: Candidate extraction queries the top-level document only and does not pierce open/closed shadow roots or cross-frame trees.
- **Single synthetic page benchmark**: The offline mutation benchmark evaluates drift permutations on a single synthetic checkout page (`mockbench/bench_app.py`).
- **Moved-far elements refuse by design**: Any candidate whose normalized center distance drops spatial proximity below `0.10` is rejected by the `moved_far` hard gate rather than risked on a distant decoy.

## What This Does Not Do

- **No assertion healing**: Self-healing resolves _which_ element is matched after UI drift, never _what_ a test asserts about business state or text.
- **No auto-commit of new selectors**: Healed selectors are logged to JSONL audit files (`reports/heal_events/`) and enforced against a CI heal budget rather than silently rewriting repository source code.
