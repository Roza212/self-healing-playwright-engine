"""Pytest CLI options, session audit hooks, HTML report UI, and self-healing fixtures."""

from pathlib import Path
from typing import Any, Generator

import pytest

from core.audit import AuditLog, load_events, summary_markdown
from core.config import HealConfig
from core.embedder import Embedder
from core.healer import SelfHealingLocator
from core.report_ui import (
    REPORT_THEME_CSS,
    build_executive_summary_html,
    build_row_badge,
    build_test_detail_html,
)

try:
    from pytest_html import extras as _html_extras
except ImportError:
    _html_extras = None

_AUDIT_DIRS = ("reports/bench_events", "reports/heal_events")
_STANDALONE_DIFFS = {
    "test_overlay_render_produces_major_severity_and_diff": Path(
        "reports/visual/overlay_diff.png"
    ),
    "test_subpixel_noise_exceeds_half_pixels_but_keeps_high_ssim": Path(
        "reports/visual/noise_diff.png"
    ),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """The --heal CLI toggle is registered with choices 'on' and 'off'."""
    parser.addoption(
        "--heal",
        choices=("on", "off"),
        default="on",
        help="Enable ('on') or disable ('off') the self-healing locator engine.",
    )
    if _html_extras is None:
        # Absorb pytest.ini addopts (--html / --self-contained-html) when pytest-html is absent.
        parser.addoption("--html", action="store", default=None)
        parser.addoption("--self-contained-html", action="store_true", default=False)


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


@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(report: Any) -> None:
    """Set a descriptive executive title on reports/report.html."""
    if _html_extras is None:
        return
    report.title = "Self-Healing Playwright Engine — Test & Telemetry Report"


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells: list[str]) -> None:
    """Rename the trailing Links column header to Telemetry & Gate."""
    if _html_extras is None:
        return
    if len(cells) >= 4:
        cells[3] = "<th>Telemetry &amp; Gate</th>"


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report: Any, cells: list[str]) -> None:
    """Populate the Telemetry & Gate column with per-test healing and visual badges."""
    if _html_extras is None:
        return
    badge = getattr(report, "_sh_badge_html", "")
    if badge and len(cells) >= 4:
        cells[3] = f'<td class="col-links">{badge}</td>'


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_summary(
    prefix: list[str],
    summary: list[str],
    postfix: list[str],
    session: pytest.Session,
) -> None:
    """Inject modern CSS theme, executive KPI cards, and session healing ledger."""
    if _html_extras is None:
        return
    prefix.append(REPORT_THEME_CSS)
    all_events = load_events("reports/bench_events") + load_events("reports/heal_events")
    total = len(session.items)
    failed = int(getattr(session, "testsfailed", 0))
    passed = max(0, total - failed)
    summary.append(build_executive_summary_html(total, passed, failed, all_events))


def _suite_kind(item: pytest.Item) -> str:
    """Determine the primary marker category for a pytest test item."""
    for name in ("heal", "visual", "unit", "live"):
        if item.get_closest_marker(name) is not None:
            return name
    return "other"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[None],
) -> Generator[None, Any, None]:
    """Attach healing score cards and inline 3-panel SSIM visual diffs to report.html rows."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or _html_extras is None:
        return

    event: dict[str, Any] | None = None
    all_events = load_events("reports/bench_events") + load_events("reports/heal_events")
    matching = [ev for ev in all_events if ev.get("test") == item.nodeid]
    if matching:
        event = matching[-1]

    standalone_diff: Path | None = None
    for fn_name, diff_path in _STANDALONE_DIFFS.items():
        if fn_name in item.nodeid:
            standalone_diff = diff_path
            break

    report._sh_badge_html = build_row_badge(_suite_kind(item), event, standalone_diff)
    detail_html = build_test_detail_html(event, standalone_diff)
    if detail_html:
        report_extras = list(getattr(report, "extras", []))
        report_extras.append(_html_extras.html(detail_html))
        report.extras = report_extras


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
