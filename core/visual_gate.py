"""Post-heal visual regression and DOM occlusion verification gate is implemented here."""

from playwright.sync_api import Page

from core.healer import SelfHealingLocator
from core.vision_diff import VisualResult, compare, is_occluded, shoot


def verify_after_heal(
    page: Page,
    healer: SelfHealingLocator,
    baseline_png: bytes,
    name: str,
) -> VisualResult | None:
    """Post-heal SSIM comparison and center-point occlusion checks are executed and recorded."""
    if not healer.heals:
        return None

    res = compare(baseline_png, shoot(page), name)
    last_heal = healer.heals[-1]
    occluded = is_occluded(page.locator(last_heal["new_selector"]).first)

    last_heal["visual"] = {
        "ssim": round(float(res.ssim), 4),
        "severity": res.severity,
        "diff": res.diff_path,
        "occluded": occluded,
    }

    if res.severity == "MAJOR" or occluded is True:
        raise AssertionError(
            f"Visual gate failed for '{name}': severity={res.severity}, "
            f"ssim={res.ssim:.4f}, occluded={occluded}, diff={res.diff_path}"
        )

    return res
