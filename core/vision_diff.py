"""SSIM visual regression comparison, heatmap diff rendering, and DOM occlusion check."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from playwright.sync_api import Locator, Page
from skimage.metrics import structural_similarity


@dataclass
class VisualResult:
    """SSIM similarity score, diff boxes, severity classification, and diff image path."""

    ssim: float
    boxes: list[tuple[int, int, int, int]]
    severity: str
    diff_path: str | None


def shoot(page: Page) -> bytes:
    """A full-page PNG screenshot is captured with animations disabled and caret hidden."""
    return page.screenshot(full_page=True, animations="disabled", caret="hide")


def _decode_png(png_bytes: bytes) -> np.ndarray:
    """Raw PNG bytes are decoded into a BGR uint8 OpenCV image array."""
    buf = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode PNG buffer.")
    return img


def _pad_bottom_right(img: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """An image is padded with white pixels on the bottom and right edges only."""
    h, w = img.shape[:2]
    pad_b = max(0, target_h - h)
    pad_r = max(0, target_w - w)
    if pad_b == 0 and pad_r == 0:
        return img
    return cv2.copyMakeBorder(
        img,
        0,
        pad_b,
        0,
        pad_r,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )


def compare(
    base_png: bytes,
    cur_png: bytes,
    name: str,
    out_dir: str = "reports/visual",
    ssim_pass: float = 0.985,
    ssim_major: float = 0.95,
    heat_thr: int = 40,
    min_area: int = 120,
) -> VisualResult:
    """Two PNG screenshots are compared with SSIM, contours, and a side-by-side diff image."""
    base_img = _decode_png(base_png)
    cur_img = _decode_png(cur_png)

    h1, w1 = base_img.shape[:2]
    h2, w2 = cur_img.shape[:2]
    sizes_differed = (h1, w1) != (h2, w2)

    target_h = max(h1, h2)
    target_w = max(w1, w2)
    base_pad = _pad_bottom_right(base_img, target_h, target_w)
    cur_pad = _pad_bottom_right(cur_img, target_h, target_w)

    gray_base = cv2.cvtColor(base_pad, cv2.COLOR_BGR2GRAY)
    gray_cur = cv2.cvtColor(cur_pad, cv2.COLOR_BGR2GRAY)

    score_val, sim = structural_similarity(gray_base, gray_cur, full=True, data_range=255)
    ssim_score = float(score_val)

    heat = ((1.0 - sim) * 255.0).clip(0, 255).astype(np.uint8)
    _, thresh = cv2.threshold(heat, heat_thr, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []
    for cnt in contours:
        if cv2.contourArea(cnt) >= min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((int(x), int(y), int(w), int(h)))

    if ssim_score < ssim_major or sizes_differed:
        severity = "MAJOR"
    elif ssim_score < ssim_pass or len(boxes) > 0:
        severity = "MINOR"
    else:
        severity = "NONE"

    diff_path: str | None = None
    if severity != "NONE":
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        cur_annotated = cur_pad.copy()
        for x, y, w, h in boxes:
            cv2.rectangle(cur_annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)

        heat_color = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
        composite = np.hstack([base_pad, cur_annotated, heat_color])

        file_path = out_path / f"{name}_diff.png"
        cv2.imwrite(str(file_path), composite)
        diff_path = str(file_path)

    return VisualResult(
        ssim=ssim_score,
        boxes=boxes,
        severity=severity,
        diff_path=diff_path,
    )


def is_occluded(locator: Locator) -> bool:
    """DOM hit-testing at the element centre is performed via document.elementFromPoint."""
    return bool(
        locator.first.evaluate(
            """el => {
                const r = el.getBoundingClientRect();
                const cx = r.left + r.width / 2;
                const cy = r.top + r.height / 2;
                const top = document.elementFromPoint(cx, cy);
                return top === null || (top !== el && !el.contains(top));
            }"""
        )
    )
