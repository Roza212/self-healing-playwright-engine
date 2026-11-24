"""Visual regression SSIM comparison, noise resilience, and post-heal visual gate tests."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from playwright.sync_api import Page

from core.healer import SelfHealingLocator
from core.vision_diff import compare, shoot
from core.visual_gate import verify_after_heal
from mockbench.bench_app import render
from pages.mock_pages import MockCheckoutPage

pytestmark = pytest.mark.visual


def test_identical_renders_have_none_severity(page: Page) -> None:
    """Two identical renders produce severity NONE, zero diff boxes, and no diff artifact."""
    pg = MockCheckoutPage(page)
    pg.load_html(render())
    base_png = shoot(page)

    pg.load_html(render())
    cur_png = shoot(page)

    res = compare(base_png, cur_png, "identical")
    assert res.severity == "NONE"
    assert res.boxes == []
    assert res.diff_path is None


def test_overlay_render_produces_major_severity_and_diff(page: Page) -> None:
    """An overlay mutation produces severity MAJOR, at least one box, and a written diff PNG."""
    pg = MockCheckoutPage(page)
    pg.load_html(render())
    base_png = shoot(page)

    pg.load_html(render(overlay=True))
    cur_png = shoot(page)

    res = compare(base_png, cur_png, "overlay")
    assert res.severity == "MAJOR"
    assert len(res.boxes) >= 1
    assert res.diff_path is not None
    assert Path(res.diff_path).exists()


def test_subpixel_noise_exceeds_half_pixels_but_keeps_high_ssim() -> None:
    """Random -1/0/+1 noise alters >50% of pixels while keeping SSIM > 0.97 without a browser."""
    base_img = np.full((360, 640, 3), 180, dtype=np.uint8)
    cv2.putText(
        base_img,
        "Acme Pay Checkout",
        (60, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.4,
        (40, 40, 40),
        3,
        cv2.LINE_AA,
    )

    rng = np.random.default_rng(0)
    noise = rng.choice([-1, 0, 1], size=base_img.shape, p=[0.35, 0.30, 0.35])
    noisy_img = np.clip(base_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    differing_ratio = float(np.mean(np.any(base_img != noisy_img, axis=-1)))
    assert differing_ratio > 0.50

    ok_base, base_buf = cv2.imencode(".png", base_img)
    ok_noisy, noisy_buf = cv2.imencode(".png", noisy_img)
    assert ok_base and ok_noisy

    res = compare(base_buf.tobytes(), noisy_buf.tobytes(), "noise")
    assert res.ssim > 0.97


def test_heal_with_overlay_raises_in_visual_gate(
    page: Page,
    healer: SelfHealingLocator,
) -> None:
    """A healed button covered by an overlay is caught by verify_after_heal and raises."""
    pg = MockCheckoutPage(page, healer)
    pg.load_html(render())
    assert pg.el(pg.SUBMIT).get_attribute("data-truth") == "submit"
    baseline = shoot(page)

    pg.load_html(render(submit_id="btn-9f8e7d", overlay=True))
    healed_el = pg.el(pg.SUBMIT)
    assert healed_el.get_attribute("data-truth") == "submit"

    with pytest.raises(AssertionError):
        verify_after_heal(page, healer, baseline, "heal_overlay")


def test_heal_without_layout_change_passes_visual_gate(
    page: Page,
    healer: SelfHealingLocator,
) -> None:
    """A healed ID rename with no layout shift passes verify_after_heal without raising."""
    pg = MockCheckoutPage(page, healer)
    pg.load_html(render())
    assert pg.el(pg.SUBMIT).get_attribute("data-truth") == "submit"
    baseline = shoot(page)

    pg.load_html(render(submit_id="btn-9f8e7d"))
    healed_el = pg.el(pg.SUBMIT)
    assert healed_el.get_attribute("data-truth") == "submit"

    res = verify_after_heal(page, healer, baseline, "heal_no_layout_change")
    assert res is not None
    assert res.severity == "NONE"
    assert healer.heals[-1]["visual"]["occluded"] is False
