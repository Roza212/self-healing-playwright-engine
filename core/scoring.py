"""Pure multi-signal scoring and hard-gate functions are implemented here."""

import math
import re

import numpy as np

ATTR_KEYS = ("id", "name", "class", "data-test", "data-testid", "type")

OPPOSITES = [
    {"add", "remove", "delete"},
    {"submit", "cancel"},
    {"pay", "refund"},
    {"login", "logout"},
    {"accept", "decline", "reject"},
    {"open", "close"},
    {"next", "previous", "back"},
    {"save", "discard"},
    {"confirm", "cancel"},
    {"enable", "disable"},
]


def tokens(s: str | None) -> set[str]:
    """Lowercase word tokens are extracted after splitting camelCase, hyphens, and underscores."""
    if not s:
        return set()
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(s))
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    parts = re.findall(r"[a-z0-9]+", spaced.lower())
    return {t for t in parts if len(t) > 1}


def attr_tokens(attrs: dict | None) -> set[str]:
    """Tokens are aggregated across standard identifying HTML attributes."""
    if not attrs:
        return set()
    result: set[str] = set()
    for key in ATTR_KEYS:
        val = attrs.get(key)
        if val:
            if isinstance(val, (list, tuple, set)):
                val = " ".join(str(v) for v in val)
            result |= tokens(str(val))
    return result


def conflicts(want: set[str], have: set[str]) -> bool:
    """Action polarity conflict is detected when two token sets hit disjoint words in a group."""
    for group in OPPOSITES:
        if (want & group) and (have & group) and not (want & have & group):
            return True
    return False


def role_score(expected: str | None, actual: str | None) -> float:
    """Compatibility between expected and actual ARIA roles is scored in [0.0, 1.0]."""
    if expected is None:
        return 0.5
    if expected == actual:
        return 1.0
    if {expected, actual} in ({"button", "link"}, {"textbox", "searchbox"}):
        return 0.5
    return 0.0


def spatial_score(
    old_box: list[float],
    new_box: list[float],
    viewport_wh: tuple[float, float] = (1280.0, 720.0),
) -> float:
    """Gaussian proximity between normalized bounding-box centres is computed."""
    vw, vh = viewport_wh
    cx1 = old_box[0] + old_box[2] / 2.0
    cy1 = old_box[1] + old_box[3] / 2.0
    cx2 = new_box[0] + new_box[2] / 2.0
    cy2 = new_box[1] + new_box[3] / 2.0
    d = math.hypot((cx1 - cx2) / vw, (cy1 - cy2) / vh)
    return float(np.exp(-((d / 0.25) ** 2)))


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity is calculated over two token sets, returning 0.0 if both are empty."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def reject_reason(
    spec,
    cand,
    want: set[str],
    spatial: float | None,
    cfg,
) -> str | None:
    """Hard gates are evaluated in strict priority order to disqualify unsafe candidates."""
    if not cand.visible:
        return "hidden"
    if not cand.enabled:
        return "disabled"
    if spec.role is not None and role_score(spec.role, cand.role) == 0.0:
        return "role_mismatch"
    if conflicts(want, tokens(cand.name + " " + cand.text)):
        return "opposite_action"
    if spatial is not None and spatial < cfg.min_spatial:
        return "moved_far"
    return None


def combine(
    sem: float | None,
    role: float | None,
    spatial: float | None,
    attr: float | None,
    cfg,
) -> float:
    """Present signal scores are combined via renormalized weights from the configuration."""
    pairs = [
        (sem, cfg.w_sem),
        (role, cfg.w_role),
        (spatial, cfg.w_spatial),
        (attr, cfg.w_attr),
    ]
    present = [(float(val), float(weight)) for val, weight in pairs if val is not None]
    if not present:
        return 0.0
    vals = np.array([v for v, _ in present], dtype=np.float64)
    weights = np.array([w for _, w in present], dtype=np.float64)
    total_w = float(weights.sum())
    if total_w <= 0.0:
        return 0.0
    return float(np.dot(vals, weights) / total_w)
