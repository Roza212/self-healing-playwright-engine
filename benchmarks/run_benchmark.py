"""Deterministic multi-variant self-healing benchmark runner and report generator."""

import argparse
import importlib.metadata
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from core.config import HealConfig
from core.embedder import Embedder
from core.healer import HealingRefused, SelfHealingLocator
from mockbench.bench_app import MUTATIONS, render
from pages.mock_pages import MockCheckoutPage

_REWORD_CHOICES = [
    "Pay Now",
    "Confirm and Pay",
    "Pay",
    "Make Payment",
    "Complete Purchase",
    "Place Order",
]


def variants(n: int, seed: int) -> list[dict[str, Any]]:
    """Generate n deterministic UI drift mutation dictionaries using random.Random(seed)."""
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    for _ in range(n):
        kw: dict[str, Any] = {}
        if rng.random() < 0.60:
            kw["submit_id"] = f"btn-{rng.randrange(16**6):06x}"
        if rng.random() < 0.50:
            kw["submit_class"] = f"c-{rng.randrange(16**4):04x} action"
        if rng.random() < 0.40:
            kw["submit_text"] = rng.choice(_REWORD_CHOICES)
        if rng.random() < 0.40:
            kw["wrap"] = rng.randint(1, 3)
        if rng.random() < 0.30:
            kw["reverse"] = True
        if rng.random() < 0.30:
            kw["submit_tag"] = "a"
        if not kw:
            kw = {"submit_id": "btn-fallback1"}
        out.append(kw)
    return out


def _p95(values: list[float]) -> float:
    """Compute the 95th percentile from a non-empty list of floats."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return round(ordered[idx], 2)


def _format_markdown(summary: dict[str, Any]) -> str:
    """Render the benchmark summary as a Markdown report."""
    tier_split = summary["tier_split"]
    lines = [
        "# Self-Healing Benchmark Report",
        "",
        f"- **Seed**: `{summary['seed']}`",
        f"- **Requested Variants (`n`)**: `{summary['n']}`",
        f"- **Heal Mode**: `{summary['heal']}`",
        f"- **Playwright Version**: `{summary['playwright_version']}`",
        f"- **Browser Version**: `{summary['browser_version']}`",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| `drift_cases` | {summary['drift_cases']} |",
        f"| `heal_success_rate` | {summary['heal_success_rate']:.2f}% |",
        f"| `wrong_heals` | {summary['wrong_heals']} |",
        f"| `false_refusals` | {summary['false_refusals']} |",
        f"| `broken` | {summary['broken']} |",
        f"| `false_heals_on_negatives` | {summary['false_heals_on_negatives']} |",
        f"| `tier_split (T2 vs T3)` | T2: {tier_split['T2']}, T3: {tier_split['T3']} |",
        f"| `median_heal_ms` | {summary['median_heal_ms']:.2f} ms |",
        f"| `p95_heal_ms` | {summary['p95_heal_ms']:.2f} ms |",
        "",
    ]
    return "\n".join(lines)


def run_benchmark(n: int = 60, seed: int = 99, heal_mode: str = "on") -> dict[str, Any]:
    """Execute n drift variants and 2 negative cases, writing JSON and Markdown reports."""
    heal_enabled = heal_mode == "on"
    embedder = Embedder(HealConfig().model_name)
    embedder.encode(["warmup"])

    drift_cases_list = variants(n, seed)
    negative_cases_list: list[tuple[str, dict[str, Any]]] = [
        ("element_removed", dict(MUTATIONS["element_removed"][0])),
        ("decoy_far", dict(MUTATIONS["decoy_far"][0])),
    ]

    rows: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        browser_version = browser.version
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        all_cases: list[tuple[str, str, dict[str, Any]]] = [
            (f"variant_{idx:03d}", "drift", kw) for idx, kw in enumerate(drift_cases_list)
        ] + [(name, "negative", kw) for name, kw in negative_cases_list]

        for case_id, kind, kw in all_cases:
            cfg = HealConfig(probe_timeout_ms=300, enabled=heal_enabled)
            healer = SelfHealingLocator(cfg, embedder, test_id=case_id)
            pg = MockCheckoutPage(page, healer)

            # Learn baseline fingerprint on default render()
            pg.load_html(render())
            pg.el(pg.SUBMIT).wait_for(state="visible")

            # Load mutated HTML
            pg.load_html(render(**kw))

            tier: int | None = None
            elapsed_ms: float | None = None

            if page.locator(pg.SUBMIT.primary).count() == 1:
                outcome = "primary_still_valid"
            else:
                t0 = time.perf_counter()
                try:
                    loc = pg.el(pg.SUBMIT)
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    truth = loc.get_attribute("data-truth")
                    if truth == "submit":
                        outcome = "healed_correct"
                    else:
                        outcome = "healed_WRONG"
                    if healer.heals:
                        tier = healer.heals[-1].get("tier")
                except HealingRefused:
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    outcome = "refused"
                except PlaywrightTimeoutError:
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    outcome = "broken"

            rows.append(
                {
                    "id": case_id,
                    "kind": kind,
                    "kwargs": kw,
                    "outcome": outcome,
                    "tier": tier,
                    "heal_ms": elapsed_ms,
                }
            )

        browser.close()

    drift_rows = [
        r for r in rows if r["kind"] == "drift" and r["outcome"] != "primary_still_valid"
    ]
    neg_rows = [r for r in rows if r["kind"] == "negative"]

    drift_total = len(drift_rows)
    healed_correct_rows = [r for r in drift_rows if r["outcome"] == "healed_correct"]
    healed_correct_count = len(healed_correct_rows)
    wrong_heals = sum(1 for r in drift_rows if r["outcome"] == "healed_WRONG")
    false_refusals = sum(1 for r in drift_rows if r["outcome"] == "refused")
    broken = sum(1 for r in drift_rows if r["outcome"] == "broken")
    false_heals_on_negatives = sum(
        1 for r in neg_rows if r["outcome"] in ("healed_correct", "healed_WRONG")
    )

    t2_count = sum(1 for r in healed_correct_rows if r["tier"] == 2)
    t3_count = sum(1 for r in healed_correct_rows if r["tier"] == 3)

    heal_times = [float(r["heal_ms"]) for r in healed_correct_rows if r["heal_ms"] is not None]
    median_ms = round(float(statistics.median(heal_times)), 2) if heal_times else 0.0
    p95_ms = _p95(heal_times)

    heal_success_rate = (
        round((healed_correct_count / drift_total) * 100.0, 2) if drift_total else 0.0
    )
    pw_version = importlib.metadata.version("playwright")

    summary: dict[str, Any] = {
        "n": n,
        "seed": seed,
        "heal": heal_mode,
        "drift_cases": drift_total,
        "healed_correct": healed_correct_count,
        "heal_success_rate": heal_success_rate,
        "wrong_heals": wrong_heals,
        "false_refusals": false_refusals,
        "broken": broken,
        "false_heals_on_negatives": false_heals_on_negatives,
        "tier_split": {"T2": t2_count, "T3": t3_count},
        "median_heal_ms": median_ms,
        "p95_heal_ms": p95_ms,
        "playwright_version": pw_version,
        "browser_version": browser_version,
    }

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "benchmark.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "benchmark.md").write_text(_format_markdown(summary), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return {"summary": summary, "rows": rows}


def main() -> None:
    """Parse CLI arguments and run the self-healing mutation benchmark."""
    parser = argparse.ArgumentParser(description="Run offline self-healing locator benchmark.")
    parser.add_argument("--n", type=int, default=60, help="Number of random drift variants.")
    parser.add_argument("--seed", type=int, default=99, help="Deterministic RNG seed.")
    parser.add_argument(
        "--heal",
        choices=("on", "off"),
        default="on",
        help="Enable ('on') or disable ('off') self-healing.",
    )
    args = parser.parse_args()
    run_benchmark(n=args.n, seed=args.seed, heal_mode=args.heal)


if __name__ == "__main__":
    main()
