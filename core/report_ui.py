"""Modern CSS styling, KPI telemetry cards, and per-test diagnostics for pytest-html reports."""

import base64
from html import escape
from pathlib import Path
from typing import Any

REPORT_THEME_CSS = """
<style>
  :root {
    --bg: #f1f5f9;
    --surface: #ffffff;
    --surface-alt: #f8fafc;
    --ink: #0f172a;
    --ink-muted: #475569;
    --border: #cbd5e1;
    --navy: #0f172a;
    --accent: #2563eb;
    --pass-bg: #dcfce7;
    --pass-fg: #166534;
    --fail-bg: #fee2e2;
    --fail-fg: #991b1b;
    --warn-bg: #fef3c7;
    --warn-fg: #92400e;
    --t2-bg: #dbeafe;
    --t2-fg: #1e40af;
    --t3-bg: #ede9fe;
    --t3-fg: #5b21b6;
  }

  * { box-sizing: border-box; }

  body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
    font-size: 14px !important;
    line-height: 1.5;
    background: var(--bg) !important;
    color: var(--ink) !important;
    max-width: 1380px;
    margin: 0 auto !important;
    padding: 28px 28px 56px !important;
  }

  h1#title {
    margin: 0 0 6px 0 !important;
    padding: 26px 32px 10px !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #1d4ed8 100%);
    color: #ffffff !important;
    font-size: 26px !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    border-radius: 16px 16px 0 0;
  }

  body > p:first-of-type {
    margin: 0 0 22px 0 !important;
    padding: 0 32px 22px !important;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #1d4ed8 100%);
    color: #cbd5e1 !important;
    font-size: 13px !important;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.14);
  }

  body > p:first-of-type a {
    color: #93c5fd !important;
    font-weight: 600;
    text-decoration: none;
  }

  #environment-header {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 20px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }

  #environment-header h2 {
    margin: 0 !important;
    font-size: 15px !important;
    font-weight: 700;
    color: var(--ink) !important;
  }

  #environment {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 22px;
    font-size: 13px;
  }

  #environment td {
    padding: 9px 16px !important;
    border: 1px solid #e2e8f0 !important;
    color: var(--ink) !important;
  }

  #environment tr:nth-child(odd) {
    background-color: var(--surface-alt) !important;
  }

  .summary {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  }

  .summary__data {
    flex: 1 1 100% !important;
  }

  .summary__data > h2 {
    margin: 0 0 16px 0 !important;
    font-size: 18px !important;
    font-weight: 800;
    color: var(--ink) !important;
  }

  .summary__spacer {
    display: none !important;
  }

  p.run-count {
    font-size: 15px !important;
    font-weight: 700;
    color: var(--ink) !important;
    margin: 12px 0 4px !important;
  }

  p.filter {
    color: var(--ink-muted) !important;
    font-size: 13px !important;
    margin: 0 0 14px !important;
  }

  .controls {
    background: var(--surface-alt);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .filters {
    flex-wrap: wrap;
    gap: 6px;
    font-weight: 600;
    color: var(--ink);
  }

  .collapse button {
    background: #ffffff !important;
    color: var(--ink) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 700;
    text-decoration: none !important;
    transition: all 0.15s ease;
  }

  .collapse button:hover {
    background: var(--navy) !important;
    color: #ffffff !important;
    border-color: var(--navy) !important;
  }

  /* Executive KPI Grid */
  .sh-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 16px;
    margin: 8px 0 22px 0;
  }

  .sh-kpi-card {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-top: 4px solid var(--accent);
    border-radius: 14px;
    padding: 18px 20px;
  }

  .sh-kpi-card.kpi-pass { border-top-color: #16a34a; }
  .sh-kpi-card.kpi-heal { border-top-color: #2563eb; }
  .sh-kpi-card.kpi-refuse { border-top-color: #d97706; }
  .sh-kpi-card.kpi-visual { border-top-color: #7c3aed; }

  .sh-kpi-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-muted);
  }

  .sh-kpi-value {
    font-size: 30px;
    font-weight: 800;
    color: var(--ink);
    margin: 6px 0 6px;
    letter-spacing: -0.02em;
  }

  .sh-kpi-sub {
    font-size: 12.5px;
    color: var(--ink-muted);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }

  /* Badges */
  .sh-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }

  .sh-pill-t2 { background: var(--t2-bg); color: var(--t2-fg); }
  .sh-pill-t3 { background: var(--t3-bg); color: var(--t3-fg); }
  .sh-pill-refuse { background: var(--warn-bg); color: var(--warn-fg); }
  .sh-pill-pass { background: var(--pass-bg); color: var(--pass-fg); }
  .sh-pill-major { background: var(--fail-bg); color: var(--fail-fg); }
  .sh-pill-neutral { background: #e2e8f0; color: #334155; }

  /* Audit Ledger Table inside Summary */
  .sh-ledger-wrap {
    margin-top: 20px;
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    background: #ffffff;
  }

  .sh-ledger-title {
    background: var(--navy);
    color: #ffffff;
    padding: 12px 18px;
    font-size: 13.5px;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sh-ledger-title span {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
  }

  table.sh-ledger {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
  }

  table.sh-ledger th {
    background: #f8fafc;
    color: #334155;
    font-weight: 700;
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
  }

  table.sh-ledger td {
    padding: 10px 14px;
    border-bottom: 1px solid #e2e8f0;
    color: var(--ink);
    vertical-align: middle;
  }

  table.sh-ledger tr:last-child td {
    border-bottom: none;
  }

  table.sh-ledger code, .sh-code {
    font-family: "Cascadia Code", Consolas, "Courier New", monospace;
    font-size: 11.5px;
    background: #f1f5f9;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    padding: 2px 6px;
    border-radius: 5px;
  }

  .sh-bar-track {
    width: 84px;
    height: 8px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
    margin-right: 6px;
  }

  .sh-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #10b981);
    border-radius: 999px;
  }

  /* Main Results Table */
  #results-table {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px;
    overflow: hidden;
    color: var(--ink) !important;
    font-size: 13.5px !important;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  }

  #results-table-head th {
    background: var(--navy) !important;
    color: #f8fafc !important;
    padding: 13px 16px !important;
    border: none !important;
    font-size: 12.5px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  #results-table td {
    padding: 12px 16px !important;
    border-bottom: 1px solid #e2e8f0 !important;
    border-left: none !important;
    border-right: none !important;
    color: var(--ink) !important;
    vertical-align: middle;
  }

  tr.collapsible:hover td {
    background: #f8fafc;
  }

  .passed .col-result {
    color: var(--pass-fg) !important;
    font-weight: 800;
  }

  .failed .col-result, .error .col-result {
    color: var(--fail-fg) !important;
    font-weight: 800;
  }

  .col-testId {
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 12.5px;
    font-weight: 600;
  }

  .col-duration {
    font-variant-numeric: tabular-nums;
    color: var(--ink-muted) !important;
    font-weight: 600;
    width: 110px;
  }

  .col-links {
    min-width: 240px;
  }

  /* Per-test expandable diagnostic card */
  td.extra {
    background: #f8fafc !important;
    padding: 18px 22px !important;
  }

  div.media {
    display: none !important;
  }

  .sh-diag-card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  }

  .sh-diag-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding-bottom: 12px;
    margin-bottom: 14px;
    border-bottom: 1px solid #e2e8f0;
  }

  .sh-diag-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin: 12px 0;
  }

  .sh-metric-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 12px;
  }

  .sh-metric-box .lbl {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--ink-muted);
  }

  .sh-metric-box .val {
    font-size: 16px;
    font-weight: 800;
    color: var(--ink);
    margin-top: 2px;
  }

  .sh-diff-figure {
    margin-top: 14px;
    background: var(--navy);
    border-radius: 10px;
    padding: 12px;
  }

  .sh-diff-figure img {
    display: block;
    width: 100%;
    height: auto;
    border-radius: 6px;
  }

  .sh-diff-caption {
    color: #cbd5e1;
    font-size: 12px;
    margin-top: 8px;
    text-align: center;
  }

  .logwrapper {
    background: #0f172a !important;
    border-radius: 10px;
    border: 1px solid #1e293b;
  }

  .logwrapper .log {
    background: #0f172a !important;
    color: #e2e8f0 !important;
    border: none !important;
    font-family: "Cascadia Code", Consolas, monospace !important;
    font-size: 12px !important;
    padding: 14px !important;
  }

  .logwrapper .logexpander {
    background: #1e293b !important;
    color: #cbd5e1 !important;
    border-color: #334155 !important;
    font-size: 11px;
    font-weight: 700;
  }
</style>
"""


def _embed_png_data_uri(path_str: str | None) -> str | None:
    """Encode a local PNG diff artifact into a self-contained data URI if it exists."""
    if not path_str:
        return None
    p = Path(path_str)
    if not p.exists():
        return None
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _class_pill(f_class: str, tier: Any) -> str:
    """Format a color-coded pill for a healing or refusal event class."""
    if f_class == "NATIVE_FALLBACK":
        return '<span class="sh-pill sh-pill-t2">T2 NATIVE FALLBACK</span>'
    if f_class == "LOCATOR_DRIFT_HEALED":
        return '<span class="sh-pill sh-pill-t3">T3 ML DRIFT HEALED</span>'
    if f_class in ("ELEMENT_REMOVED", "AMBIGUOUS"):
        return f'<span class="sh-pill sh-pill-refuse">REFUSED ({escape(f_class)})</span>'
    return f'<span class="sh-pill sh-pill-neutral">T{escape(str(tier))} {escape(f_class)}</span>'


def _visual_pill(vis: dict[str, Any] | None) -> str:
    """Format a color-coded pill for a post-heal SSIM and occlusion check."""
    if not vis:
        return '<span class="sh-pill sh-pill-neutral">Not Invoked</span>'
    sev = str(vis.get("severity") or "NONE")
    ssim_val = vis.get("ssim")
    ssim_txt = f"{float(ssim_val):.4f}" if ssim_val is not None else "-"
    occluded = bool(vis.get("occluded"))
    if occluded:
        return f'<span class="sh-pill sh-pill-major">OCCLUDED • SSIM {ssim_txt}</span>'
    if sev == "MAJOR":
        return f'<span class="sh-pill sh-pill-major">MAJOR • SSIM {ssim_txt}</span>'
    if sev == "MINOR":
        return f'<span class="sh-pill sh-pill-refuse">MINOR • SSIM {ssim_txt}</span>'
    return f'<span class="sh-pill sh-pill-pass">CLEAN • SSIM {ssim_txt}</span>'


def build_row_badge(
    suite_kind: str,
    event: dict[str, Any] | None,
    standalone_diff: Path | None = None,
) -> str:
    """Render compact inline telemetry pills for the main test table row."""
    pills: list[str] = []
    if event:
        pills.append(_class_pill(str(event.get("failure_class") or ""), event.get("tier")))
        if event.get("visual"):
            pills.append(_visual_pill(event.get("visual")))
    elif standalone_diff and standalone_diff.exists():
        pills.append('<span class="sh-pill sh-pill-t3">SSIM Diff Artifact</span>')
    else:
        label_map = {
            "unit": ("Unit • Pure Math/Audit", "sh-pill-neutral"),
            "visual": ("Visual SSIM Gate", "sh-pill-pass"),
            "heal": ("Mutation Bench", "sh-pill-t2"),
            "live": ("Live SauceDemo E2E", "sh-pill-pass"),
        }
        txt, cls = label_map.get(suite_kind, ("Standard Test", "sh-pill-neutral"))
        pills.append(f'<span class="sh-pill {cls}">{escape(txt)}</span>')
    return " ".join(pills)


def build_test_detail_html(
    event: dict[str, Any] | None,
    standalone_diff: Path | None = None,
) -> str | None:
    """Build an expandable diagnostic card with signal scores and inline crisp diff PNG."""
    if event is None and (standalone_diff is None or not standalone_diff.exists()):
        return None

    parts = ['<div class="sh-diag-card">']
    diff_uri: str | None = None

    if event is not None:
        f_class = str(event.get("failure_class") or "")
        tier = event.get("tier")
        logical = escape(str(event.get("logical_name") or ""))
        old_sel = escape(str(event.get("old_selector") or ""))
        new_sel = escape(str(event.get("new_selector") or "None (Refused safely)"))
        scores = event.get("scores") or {}
        vis = event.get("visual")
        if vis and vis.get("diff"):
            diff_uri = _embed_png_data_uri(str(vis.get("diff")))

        parts.append(
            f'<div class="sh-diag-header">'
            f"<div><strong>Element:</strong> <span class=\"sh-code\">{logical}</span></div>"
            f"<div>{_class_pill(f_class, tier)} {_visual_pill(vis)}</div>"
            f"</div>"
            f'<div style="margin-bottom:10px">'
            f"<strong>Primary Selector:</strong> <span class=\"sh-code\">{old_sel}</span><br/>"
            f'<strong style="display:inline-block;margin-top:6px">Resolved Selector:</strong> '
            f'<span class="sh-code">{new_sel}</span>'
            f"</div>"
        )

        def _fmt(val: Any) -> str:
            return f"{float(val):.4f}" if val is not None else "—"

        parts.append(
            '<div class="sh-diag-grid">'
            f'<div class="sh-metric-box"><div class="lbl">Total Score</div>'
            f'<div class="val">{_fmt(scores.get("total"))}</div></div>'
            f'<div class="sh-metric-box"><div class="lbl">Semantic (0.55)</div>'
            f'<div class="val">{_fmt(scores.get("semantic"))}</div></div>'
            f'<div class="sh-metric-box"><div class="lbl">ARIA Role (0.15)</div>'
            f'<div class="val">{_fmt(scores.get("role"))}</div></div>'
            f'<div class="sh-metric-box"><div class="lbl">Spatial (0.20)</div>'
            f'<div class="val">{_fmt(scores.get("spatial"))}</div></div>'
            f'<div class="sh-metric-box"><div class="lbl">Attributes (0.10)</div>'
            f'<div class="val">{_fmt(scores.get("attr"))}</div></div>'
            f'<div class="sh-metric-box"><div class="lbl">Lead Margin</div>'
            f'<div class="val">{_fmt(event.get("margin"))}</div></div>'
            "</div>"
        )
    elif standalone_diff is not None:
        diff_uri = _embed_png_data_uri(str(standalone_diff))
        parts.append(
            '<div class="sh-diag-header">'
            "<div><strong>Post-Heal Computer Vision SSIM Comparison</strong></div>"
            '<div><span class="sh-pill sh-pill-t3">3-Panel Visual Diff</span></div>'
            "</div>"
        )

    if diff_uri:
        parts.append(
            '<div class="sh-diff-figure">'
            f'<img src="{diff_uri}" alt="3-panel SSIM visual diff" />'
            '<div class="sh-diff-caption">'
            "Left: Pre-drift Baseline  •  Centre: Current Render with Diff Regions Boxed  •  "
            "Right: Contrast-Boosted SSIM Heatmap"
            "</div></div>"
        )

    parts.append("</div>")
    return "".join(parts)


def build_executive_summary_html(
    total_tests: int,
    passed_tests: int,
    failed_tests: int,
    events: list[dict[str, Any]],
) -> str:
    """Build KPI cards and an interactive healing audit ledger for the top of report.html."""
    t2_count = sum(1 for e in events if e.get("failure_class") == "NATIVE_FALLBACK")
    t3_count = sum(1 for e in events if e.get("failure_class") == "LOCATOR_DRIFT_HEALED")
    healed_total = t2_count + t3_count
    refused_total = sum(
        1 for e in events if e.get("failure_class") in ("ELEMENT_REMOVED", "AMBIGUOUS")
    )
    vis_events = [e for e in events if e.get("visual")]
    vis_clean = sum(
        1
        for e in vis_events
        if e["visual"].get("severity") in ("NONE", "MINOR") and not e["visual"].get("occluded")
    )
    vis_blocked = sum(
        1
        for e in vis_events
        if e["visual"].get("severity") == "MAJOR" or e["visual"].get("occluded")
    )

    pass_rate = (passed_tests / total_tests * 100.0) if total_tests else 100.0
    fail_pill = (
        f'<span class="sh-pill sh-pill-major">{failed_tests} Failed</span>'
        if failed_tests
        else ""
    )
    block_pill = (
        f'<span class="sh-pill sh-pill-major">{vis_blocked} Blocked</span>'
        if vis_blocked
        else ""
    )

    kpi_html = f"""
    <div class="sh-kpi-grid">
      <div class="sh-kpi-card kpi-pass">
        <div class="sh-kpi-label">Suite Pass Rate</div>
        <div class="sh-kpi-value">{pass_rate:.1f}%</div>
        <div class="sh-kpi-sub">
          <span class="sh-pill sh-pill-pass">{passed_tests} Passed</span>
          {fail_pill}
          <span>of {total_tests} tests</span>
        </div>
      </div>
      <div class="sh-kpi-card kpi-heal">
        <div class="sh-kpi-label">Locators Self-Healed</div>
        <div class="sh-kpi-value">{healed_total}</div>
        <div class="sh-kpi-sub">
          <span class="sh-pill sh-pill-t2">T2 Role: {t2_count}</span>
          <span class="sh-pill sh-pill-t3">T3 MiniLM: {t3_count}</span>
        </div>
      </div>
      <div class="sh-kpi-card kpi-refuse">
        <div class="sh-kpi-label">Unsafe Traps Refused</div>
        <div class="sh-kpi-value">{refused_total}</div>
        <div class="sh-kpi-sub">
          <span class="sh-pill sh-pill-refuse">Hard Safety Gates Active</span>
        </div>
      </div>
      <div class="sh-kpi-card kpi-visual">
        <div class="sh-kpi-label">Post-Heal Visual Gate</div>
        <div class="sh-kpi-value">{len(vis_events)}</div>
        <div class="sh-kpi-sub">
          <span class="sh-pill sh-pill-pass">{vis_clean} Verified</span>
          {block_pill}
        </div>
      </div>
    </div>
    """

    if not events:
        return kpi_html

    rows_html: list[str] = []
    for ev in events:
        test_short = escape(str(ev.get("test") or "").split("::")[-1])
        elem = escape(str(ev.get("logical_name") or ""))
        f_class = str(ev.get("failure_class") or "")
        tier = ev.get("tier")
        new_sel = escape(str(ev.get("new_selector") or "— (Refused)"))
        total_score = float((ev.get("scores") or {}).get("total") or 0.0)
        pct = max(0, min(100, int(round(total_score * 100))))
        vis_badge = _visual_pill(ev.get("visual"))

        rows_html.append(
            f"<tr>"
            f"<td><code>{test_short}</code></td>"
            f"<td><code>{elem}</code></td>"
            f"<td>{_class_pill(f_class, tier)}</td>"
            f"<td><code>{new_sel}</code></td>"
            f'<td><div class="sh-bar-track"><div class="sh-bar-fill" '
            f'style="width:{pct}%"></div></div><strong>{total_score:.4f}</strong></td>'
            f"<td>{vis_badge}</td>"
            f"</tr>"
        )

    ledger_html = (
        '<div class="sh-ledger-wrap">'
        '<div class="sh-ledger-title">'
        "<div>Self-Healing &amp; Visual Gate Session Ledger</div>"
        "<span>Click any test row below to inspect full scores &amp; 3-panel SSIM diffs</span>"
        "</div>"
        '<table class="sh-ledger">'
        "<thead><tr>"
        "<th>Test Case</th><th>Element</th><th>Resolution</th>"
        "<th>Synthesized Selector</th><th>Confidence</th><th>Visual Gate</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )
    return kpi_html + ledger_html
