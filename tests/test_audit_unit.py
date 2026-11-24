"""Unit tests for AuditLog JSONL persistence, deduplicated loading, and CLI budget enforcement."""

import sys
from pathlib import Path

import pytest

from core.audit import AuditLog, load_events, main

pytestmark = pytest.mark.unit


def test_record_then_load_returns_event(tmp_path: Path) -> None:
    """Recording an event persists it with a UTC timestamp and load_events returns it."""
    audit = AuditLog(tmp_path)
    event = {
        "test": "tests/test_mutations.py::test_mutation_bench[id_renamed]",
        "logical_name": "mock.submit",
        "failure_class": "LOCATOR_DRIFT_HEALED",
        "tier": 3,
        "old_selector": "#submit-payment",
        "new_selector": 'role=button[name="Submit Payment"]',
        "scores": {"total": 0.95},
    }
    recorded = audit.record(event)
    assert "ts" in recorded

    loaded = load_events(tmp_path)
    assert len(loaded) == 1
    assert loaded[0] == recorded


def test_update_overwrites_earlier_version_on_load(tmp_path: Path) -> None:
    """Updating an event appends a new line and load_events returns only the updated version."""
    audit = AuditLog(tmp_path)
    event = {
        "test": "tests/test_mutations.py::test_mutation_bench[id_renamed]",
        "logical_name": "mock.submit",
        "failure_class": "LOCATOR_DRIFT_HEALED",
        "tier": 3,
        "old_selector": "#submit-payment",
        "new_selector": 'role=button[name="Submit Payment"]',
        "scores": {"total": 0.95},
    }
    audit.record(event)

    event["visual"] = {"ssim": 1.0, "severity": "NONE", "diff": None, "occluded": False}
    audit.update(event)

    loaded = load_events(tmp_path)
    assert len(loaded) == 1
    assert loaded[0]["visual"]["severity"] == "NONE"


def test_main_budget_gate_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI main() exits 1 when heal events exceed --budget and exits 0 when within budget."""
    monkeypatch.chdir(tmp_path)
    events_dir = tmp_path / "events"
    audit = AuditLog(events_dir)
    audit.record(
        {
            "test": "tests/test_mutations.py::test_mutation_bench[id_renamed]",
            "logical_name": "mock.submit",
            "failure_class": "LOCATOR_DRIFT_HEALED",
            "tier": 3,
            "old_selector": "#submit-payment",
            "new_selector": 'role=button[name="Submit Payment"]',
            "scores": {"total": 0.95},
        }
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["core.audit", "--dir", str(events_dir), "--budget", "0"],
    )
    with pytest.raises(SystemExit) as exc_fail:
        main()
    assert exc_fail.value.code == 1

    monkeypatch.setattr(
        sys,
        "argv",
        ["core.audit", "--dir", str(events_dir), "--budget", "5"],
    )
    with pytest.raises(SystemExit) as exc_pass:
        main()
    assert exc_pass.value.code == 0
