"""Offline deterministic mutation benchmark tests for heal and refuse scenarios are defined here."""

from typing import Any

import pytest
from playwright.sync_api import Page

from core.healer import HealingRefused, SelfHealingLocator
from mockbench.bench_app import MUTATIONS, render
from pages.mock_pages import MockCheckoutPage

pytestmark = pytest.mark.heal


@pytest.mark.parametrize(
    ("name", "case"),
    list(MUTATIONS.items()),
    ids=list(MUTATIONS.keys()),
)
def test_mutation_bench(
    name: str,
    case: tuple[dict[str, Any], str],
    page: Page,
    healer: SelfHealingLocator,
) -> None:
    """Baseline fingerprint is learned and each UI drift or refusal mutation is verified."""
    kwargs, expected = case
    pg = MockCheckoutPage(page, healer)
    pg.load_html(render())
    assert pg.el(pg.SUBMIT).get_attribute("data-truth") == "submit"

    pg.load_html(render(**kwargs))
    if expected == "heal":
        try:
            healed_el = pg.el(pg.SUBMIT)
        except HealingRefused as exc:
            print(f"Top-3 candidates for refused heal case '{name}': {exc.top}")
            raise
        assert healed_el.get_attribute("data-truth") == "submit"
        assert len(healer.heals) > 0
    else:
        with pytest.raises(HealingRefused):
            pg.el(pg.SUBMIT)
