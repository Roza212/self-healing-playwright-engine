"""Pytest CLI options and shared self-healing fixtures are configured here."""

import pytest

from core.config import HealConfig
from core.embedder import Embedder
from core.healer import SelfHealingLocator


def pytest_addoption(parser: pytest.Parser) -> None:
    """The --heal CLI toggle is registered with choices 'on' and 'off'."""
    parser.addoption(
        "--heal",
        choices=("on", "off"),
        default="on",
        help="Enable ('on') or disable ('off') the self-healing locator engine.",
    )


@pytest.fixture(scope="session")
def embedder() -> Embedder:
    """A session-scoped sentence embedder instance is shared across all tests."""
    return Embedder(HealConfig().model_name)


@pytest.fixture
def healer(request: pytest.FixtureRequest, embedder: Embedder) -> SelfHealingLocator:
    """A per-test SelfHealingLocator is configured from CLI options and test markers."""
    option = request.config.getoption("--heal")
    is_live = request.node.get_closest_marker("live") is not None
    cfg = HealConfig(
        enabled=(option == "on"),
        probe_timeout_ms=3000 if is_live else 400,
    )
    return SelfHealingLocator(cfg, embedder, test_id=request.node.nodeid)
