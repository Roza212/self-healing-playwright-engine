"""Pytest CLI options, session audit hooks, and shared self-healing fixtures are configured here."""

from pathlib import Path

import pytest

from core.audit import AuditLog, load_events, summary_markdown
from core.config import HealConfig
from core.embedder import Embedder
from core.healer import SelfHealingLocator

_AUDIT_DIRS = ("reports/bench_events", "reports/heal_events")


def pytest_addoption(parser: pytest.Parser) -> None:
    """The --heal CLI toggle is registered with choices 'on' and 'off'."""
    parser.addoption(
        "--heal",
        choices=("on", "off"),
        default="on",
        help="Enable ('on') or disable ('off') the self-healing locator engine.",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Stale events_*.jsonl files in both audit directories are deleted before a test session."""
    for d in _AUDIT_DIRS:
        dir_path = Path(d)
        if dir_path.exists():
            for old_file in dir_path.glob("events_*.jsonl"):
                old_file.unlink(missing_ok=True)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """The Markdown healing summary is generated from reports/bench_events at session end."""
    summary_path = Path("reports/heal_summary.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    events = load_events("reports/bench_events")
    summary_path.write_text(summary_markdown(events), encoding="utf-8")


@pytest.fixture(scope="session")
def embedder() -> Embedder:
    """A session-scoped sentence embedder instance is shared across all tests."""
    return Embedder(HealConfig().model_name)


@pytest.fixture
def healer(request: pytest.FixtureRequest, embedder: Embedder) -> SelfHealingLocator:
    """A per-test SelfHealingLocator is configured from CLI options and test markers."""
    option = request.config.getoption("--heal")
    is_live = request.node.get_closest_marker("live") is not None
    is_bench = (
        request.node.get_closest_marker("heal") is not None
        or request.node.get_closest_marker("visual") is not None
    )
    audit_dir = "reports/bench_events" if is_bench else "reports/heal_events"
    cfg = HealConfig(
        enabled=(option == "on"),
        probe_timeout_ms=3000 if is_live else 400,
    )
    return SelfHealingLocator(
        cfg,
        embedder,
        audit=AuditLog(audit_dir),
        test_id=request.node.nodeid,
    )
