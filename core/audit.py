"""JSONL audit logger, event loader, Markdown summary and heal-budget CLI."""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """Per-process JSONL event recorder with append-only update support."""

    def __init__(self, directory: str | Path = "reports/heal_events") -> None:
        """The target directory is ensured and the per-process JSONL file path is assigned."""
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = self.directory / f"events_{os.getpid()}.jsonl"

    def record(self, event: dict[str, Any]) -> dict[str, Any]:
        """A UTC ISO-8601 timestamp is added to event, appended as one JSON line, and returned."""
        event["ts"] = datetime.now(timezone.utc).isoformat()
        with self.file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
        return event

    def update(self, event: dict[str, Any]) -> dict[str, Any]:
        """An updated event is appended again so the latest line wins during deduplicated load."""
        with self.file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
        return event


def load_events(directory: str | Path = "reports/heal_events") -> list[dict[str, Any]]:
    """Read every events_*.jsonl; merge by (test, logical_name, tier); last line wins."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    merged: dict[tuple[Any, Any, Any], dict[str, Any]] = {}
    for file_path in sorted(dir_path.glob("events_*.jsonl")):
        with file_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                ev: dict[str, Any] = json.loads(raw)
                key = (ev.get("test"), ev.get("logical_name"), ev.get("tier"))
                merged[key] = ev
    return list(merged.values())


def summary_markdown(events: list[dict[str, Any]]) -> str:
    """A Markdown summary table is built from a list of merged audit events."""
    lines = [
        "| element | class | tier | old selector | new selector | score | visual severity |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for ev in events:
        element = str(ev.get("logical_name") or "")
        f_class = str(ev.get("failure_class") or "")
        tier = str(ev.get("tier") if ev.get("tier") is not None else "")
        old_sel = str(ev.get("old_selector") or "").replace("|", "\\|")
        new_sel = str(ev.get("new_selector") or "-").replace("|", "\\|")
        scores = ev.get("scores") or {}
        total = scores.get("total")
        score_str = f"{float(total):.4f}" if total is not None else "-"
        visual = ev.get("visual") or {}
        vis_sev = str(visual.get("severity") or "-")
        lines.append(
            f"| {element} | {f_class} | {tier} | `{old_sel}` | `{new_sel}` "
            f"| {score_str} | {vis_sev} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI: write reports/heal_summary.md, print class counts, enforce budget."""
    parser = argparse.ArgumentParser(description="Self-healing audit summary and budget gate.")
    parser.add_argument(
        "--dir",
        default="reports/heal_events",
        help="Directory containing events_*.jsonl audit files.",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=0,
        help="Maximum allowed NATIVE_FALLBACK + LOCATOR_DRIFT_HEALED events.",
    )
    args = parser.parse_args()

    events = load_events(args.dir)
    summary_path = Path("reports/heal_summary.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary_markdown(events), encoding="utf-8")

    counts = Counter(str(ev.get("failure_class") or "UNKNOWN") for ev in events)
    for cls, count in sorted(counts.items()):
        print(f"{cls}: {count}")

    healed_count = counts.get("NATIVE_FALLBACK", 0) + counts.get("LOCATOR_DRIFT_HEALED", 0)
    print(f"healed_total={healed_count} budget={args.budget}")
    sys.exit(1 if healed_count > args.budget else 0)


if __name__ == "__main__":
    main()
