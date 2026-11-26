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


def _crop_horizontal_span(
    base_pad: np.ndarray,
    cur_pad: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int]:
    """Find active horizontal bounds so wide empty viewport margins do not shrink panel text."""
    _, w = base_pad.shape[:2]
    if w < 900:
        return 0, w

    bg_color = base_pad[0, 0].astype(np.int16)
    base_diff = np.max(np.abs(base_pad.astype(np.int16) - bg_color), axis=2) > 6
    cur_diff = np.max(np.abs(cur_pad.astype(np.int16) - bg_color), axis=2) > 6
    active_cols = np.where(np.any(base_diff | cur_diff, axis=0))[0]

    if active_cols.size == 0:
        return 0, w

    x0 = int(active_cols[0])
    x1 = int(active_cols[-1]) + 1
    for bx, _, bw, _ in boxes:
        x0 = min(x0, bx)
        x1 = max(x1, bx + bw)

    x0 = max(0, x0 - 32)
    x1 = min(w, x1 + 32)
    if w - (x1 - x0) < 160:
        return 0, w
    return x0, x1


def _ssim_rose_lut_bgr() -> np.ndarray:
    """Build a clean, single-hue white -> rose-coral -> deep-crimson LUT in BGR."""
    # Avoids yellow/grey khaki muddiness and harsh rainbow transitions:
    # 0: #ffffff, 55: #fecdd3 (soft blush), 120: #fb7185 (clean coral-rose),
    # 190: #e11d48 (vivid crimson), 255: #7f1d1d (deep ruby)
    stops_idx = np.array([0, 55, 120, 190, 255], dtype=np.float32)
    stops_bgr = np.array(
        [
            [255, 255, 255],
            [211, 205, 254],
            [133, 113, 251],
            [72, 29, 225],
            [29, 29, 127],
        ],
        dtype=np.float32,
    )
    xs = np.arange(256, dtype=np.float32)
    lut = np.zeros((256, 1, 3), dtype=np.uint8)
    for ch in range(3):
        lut[:, 0, ch] = np.clip(np.interp(xs, stops_idx, stops_bgr[:, ch]), 0, 255).astype(
            np.uint8
        )
    return lut


_SSIM_LUT = _ssim_rose_lut_bgr()


def _render_panel_header(
    width: int,
    title: str,
    accent_bgr: tuple[int, int, int],
    badge_text: str | None = None,
    badge_bgr: tuple[int, int, int] = (59, 130, 246),
) -> np.ndarray:
    """Render a supersampled 2x->1x anti-aliased header strip for razor-sharp typography."""
    scale = 2
    hh = 48 * scale
    ww = width * scale
    bar = np.full((hh, ww, 3), (42, 23, 15), dtype=np.uint8)  # #0f172a in BGR
    cv2.line(bar, (0, hh - 3), (ww, hh - 3), (71, 55, 38), 3)

    cv2.circle(bar, (28 * scale, 24 * scale), 7 * scale, accent_bgr, -1, cv2.LINE_AA)

    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.62 * scale
    cv2.putText(
        bar,
        title,
        (46 * scale, 31 * scale),
        font,
        font_scale,
        (248, 250, 252),
        2,
        cv2.LINE_AA,
    )

    if badge_text:
        (tw, th), _ = cv2.getTextSize(badge_text, font, 0.54 * scale, 2)
        pad_x = 14 * scale
        bx2 = ww - 20 * scale
        bx1 = max(46 * scale, bx2 - tw - 2 * pad_x)
        by1 = 10 * scale
        by2 = hh - 10 * scale
        cv2.rectangle(bar, (bx1, by1), (bx2, by2), badge_bgr, -1, cv2.LINE_AA)
        cv2.putText(
            bar,
            badge_text,
            (bx1 + pad_x, by1 + int((by2 - by1 + th) * 0.5) - 2),
            font,
            0.54 * scale,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    return cv2.resize(bar, (width, 48), interpolation=cv2.INTER_AREA)


def _render_panel_footer(width: int, text: str, show_scale: bool = False) -> np.ndarray:
    """Render a supersampled 2x->1x calm light-slate footer strip (with legend on Panel 3)."""
    scale = 2
    fh = 38 * scale
    ww = width * scale
    bar = np.full((fh, ww, 3), (249, 245, 241), dtype=np.uint8)  # #f1f5f9 in BGR
    cv2.line(bar, (0, 0), (ww, 0), (225, 213, 203), 3)

    font = cv2.FONT_HERSHEY_DUPLEX
    if not show_scale or width < 420:
        cv2.putText(
            bar,
            text,
            (22 * scale, 25 * scale),
            font,
            0.50 * scale,
            (105, 85, 71),
            1,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            bar,
            "SSIM diff:",
            (22 * scale, 25 * scale),
            font,
            0.50 * scale,
            (85, 65, 51),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            bar,
            "0% (Same)",
            (132 * scale, 25 * scale),
            font,
            0.46 * scale,
            (105, 85, 71),
            1,
            cv2.LINE_AA,
        )
        gx1 = 236 * scale
        gx2 = min(ww - 140 * scale, gx1 + 220 * scale)
        gy1 = 12 * scale
        gy2 = 26 * scale
        if gx2 > gx1 + 20:
            grad_idx = np.linspace(0, 255, gx2 - gx1, dtype=np.uint8)
            grad_row = _SSIM_LUT[grad_idx, 0, :]
            bar[gy1:gy2, gx1:gx2] = grad_row[None, :, :]
            cv2.rectangle(bar, (gx1, gy1), (gx2, gy2), (175, 158, 145), 2)
            cv2.putText(
                bar,
                "100% (Changed)",
                (gx2 + 12 * scale, 25 * scale),
                font,
                0.46 * scale,
                (55, 29, 190),
                1,
                cv2.LINE_AA,
            )

    return cv2.resize(bar, (width, 38), interpolation=cv2.INTER_AREA)


def _build_composite(
    base_pad: np.ndarray,
    cur_pad: np.ndarray,
    gray_base: np.ndarray,
    heat: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    ssim_score: float,
    severity: str,
) -> np.ndarray:
    """Build a crisp 3-panel visual diff with a clean rose-crimson SSIM map over baseline."""
    x0, x1 = _crop_horizontal_span(base_pad, cur_pad, boxes)
    base_view = base_pad[:, x0:x1].copy()
    cur_view = cur_pad[:, x0:x1].copy()
    g_base_view = gray_base[:, x0:x1].astype(np.float32)
    heat_view = heat[:, x0:x1]
    pw = base_view.shape[1]

    # Annotate Centre panel with subtle crimson wash + high-contrast haloed border
    tint_layer = cur_view.copy()
    shifted_boxes: list[tuple[int, int, int, int]] = []
    for x, y, w, h in boxes:
        sx = max(0, x - x0)
        ex = min(pw - 1, x - x0 + w)
        if ex > sx:
            shifted_boxes.append((sx, y, ex - sx, h))
            cv2.rectangle(tint_layer, (sx, y), (ex, y + h), (48, 38, 220), -1)
    cur_annotated = cv2.addWeighted(tint_layer, 0.08, cur_view, 0.92, 0)
    for sx, sy, sw, sh in shifted_boxes:
        cv2.rectangle(
            cur_annotated,
            (max(0, sx - 2), max(0, sy - 2)),
            (min(pw - 1, sx + sw + 2), sy + sh + 2),
            (255, 255, 255),
            5,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            cur_annotated,
            (sx, sy),
            (sx + sw, sy + sh),
            (38, 38, 220),
            3,
            cv2.LINE_AA,
        )

    # Panel 3: Single-frame crisp light-silver baseline wireframe (no double-exposure ghosting)
    # overlaid with a clean rose-to-crimson SSIM heat wash.
    silver = 176.0 + (g_base_view / 255.0) * 77.0
    blueprint = np.stack(
        [
            np.clip(silver + 4.0, 0, 255),
            np.clip(silver + 1.0, 0, 255),
            np.clip(silver - 2.0, 0, 255),
        ],
        axis=-1,
    )

    scaled_idx = np.clip((heat_view.astype(np.float32) - 4.0) * 1.45, 0, 255).astype(np.uint8)
    rose_color = cv2.LUT(
        cv2.merge([scaled_idx, scaled_idx, scaled_idx]),
        _SSIM_LUT,
    ).astype(np.float32)

    t = np.clip((heat_view.astype(np.float32) - 5.0) / 185.0, 0.0, 1.0)
    alpha = (0.78 * (t ** 0.80))[..., None]
    heat_panel = np.clip(blueprint * (1.0 - alpha) + rose_color * alpha, 0, 255).astype(np.uint8)

    for sx, sy, sw, sh in shifted_boxes:
        cv2.rectangle(
            heat_panel,
            (max(0, sx - 1), max(0, sy - 1)),
            (min(pw - 1, sx + sw + 1), sy + sh + 1),
            (255, 255, 255),
            4,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            heat_panel,
            (sx, sy),
            (sx + sw, sy + sh),
            (45, 25, 195),
            2,
            cv2.LINE_AA,
        )

    sev_bgr = (48, 48, 220) if severity == "MAJOR" else (18, 145, 235)
    h1 = _render_panel_header(pw, "1. BASELINE", (129, 185, 16), "CLEAN", (85, 130, 20))
    h2 = _render_panel_header(
        pw,
        "2. CURRENT (DIFF BOXED)",
        sev_bgr,
        f"{len(boxes)} REGION{'S' if len(boxes) != 1 else ''}",
        sev_bgr,
    )
    h3 = _render_panel_header(
        pw,
        f"3. SSIM HEATMAP  ({ssim_score:.4f})",
        sev_bgr,
        severity,
        sev_bgr,
    )

    f1 = _render_panel_footer(pw, "Pre-drift reference UI")
    f2 = _render_panel_footer(pw, "Changed contour regions boxed in red")
    f3 = _render_panel_footer(pw, "SSIM difference intensity", show_scale=True)

    p1 = np.vstack([h1, base_view, f1])
    p2 = np.vstack([h2, cur_annotated, f2])
    p3 = np.vstack([h3, heat_panel, f3])

    gutter = np.full((p1.shape[0], 12, 3), (42, 23, 15), dtype=np.uint8)
    joined = np.hstack([p1, gutter, p2, gutter, p3])
    return cv2.copyMakeBorder(
        joined,
        10,
        10,
        10,
        10,
        cv2.BORDER_CONSTANT,
        value=(42, 23, 15),
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
        composite = _build_composite(
            base_pad,
            cur_pad,
            gray_base,
            heat,
            boxes,
            ssim_score,
            severity,
        )
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
