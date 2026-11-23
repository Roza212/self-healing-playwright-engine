"""Unit tests for pure scoring functions and hard gates are defined here."""

import pytest

from core.config import HealConfig
from core.models import Candidate, ElementSpec
from core.scoring import (
    combine,
    conflicts,
    reject_reason,
    role_score,
    spatial_score,
    tokens,
)

pytestmark = pytest.mark.unit


def test_conflicts_detects_opposite_actions() -> None:
    """Opposite action words are flagged while non-conflicting action words are allowed."""
    want = tokens("Submit Payment")
    assert conflicts(want, tokens("Cancel Payment")) is True
    assert conflicts(want, tokens("Pay Now")) is False


def test_role_score_cases() -> None:
    """Exact, compatible, and mismatched ARIA roles are scored as specified."""
    assert role_score("button", "button") == 1.0
    assert role_score("button", "link") == 0.5
    assert role_score("button", "textbox") == 0.0


def test_spatial_score_near_and_far() -> None:
    """Identical bounding boxes score above 0.99 while distant boxes score below 0.1."""
    box_a = [100.0, 200.0, 120.0, 40.0]
    box_far = [1000.0, 200.0, 120.0, 40.0]
    assert spatial_score(box_a, box_a, (1280, 720)) > 0.99
    assert spatial_score(box_a, box_far, (1280, 720)) < 0.1


def test_combine_renormalises_missing_signals() -> None:
    """Weights are renormalized over present signals when spatial and attr are None."""
    cfg = HealConfig()
    score = combine(sem=0.80, role=1.0, spatial=None, attr=None, cfg=cfg)
    expected = (0.80 * cfg.w_sem + 1.0 * cfg.w_role) / (cfg.w_sem + cfg.w_role)
    assert score == pytest.approx(expected)


def test_reject_reason_moved_far_and_opposite_action() -> None:
    """Hard gates return moved_far for low spatial score and opposite_action for Cancel."""
    cfg = HealConfig()
    spec = ElementSpec(
        name="checkout.submit",
        primary="#submit",
        role="button",
        accessible_name="Submit Payment",
    )
    want = tokens("Submit Payment")

    far_cand = Candidate(
        tag="button",
        role="button",
        name="Pay Now",
        text="Pay Now",
        attrs={},
        box=[1000.0, 600.0, 100.0, 40.0],
        css_path="button.pay",
        visible=True,
        enabled=True,
    )
    assert reject_reason(spec, far_cand, want, spatial=0.05, cfg=cfg) == "moved_far"

    cancel_cand = Candidate(
        tag="button",
        role="button",
        name="Cancel Payment",
        text="Cancel Payment",
        attrs={},
        box=[100.0, 200.0, 100.0, 40.0],
        css_path="button.cancel",
        visible=True,
        enabled=True,
    )
    assert reject_reason(spec, cancel_cand, want, spatial=0.95, cfg=cfg) == "opposite_action"
