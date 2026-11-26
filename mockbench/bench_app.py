"""Offline deterministic HTML mutation generator for self-healing benchmarks is provided here."""

from typing import Any

_PAGE_STYLE = """
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        padding: 24px 0;
        background: #ffffff;
        color: #0f172a;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
      }
      header {
        max-width: 720px;
        margin: 0 auto;
        background: #0f172a;
        color: #ffffff;
        padding: 20px 36px;
        border-radius: 14px 14px 0 0;
        border-bottom: 4px solid #2563eb;
      }
      header h1 {
        margin: 0;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.02em;
      }
      main {
        max-width: 720px;
        margin: 0 auto;
        background: #f1f5f9;
        border: 2px solid #cbd5e1;
        border-top: none;
        border-radius: 0 0 14px 14px;
        padding: 36px;
      }
      form#checkout {
        background: #ffffff;
        border: 2px solid #94a3b8;
        border-radius: 12px;
        padding: 32px 36px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
      }
      form#checkout h2 {
        margin: 0 0 22px;
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
      }
      form#checkout label {
        display: block;
        font-size: 18px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 10px;
      }
      form#checkout input#card {
        display: block;
        width: 100%;
        height: 48px;
        padding: 10px 14px;
        font-size: 18px;
        color: #0f172a;
        background: #f8fafc;
        border: 2px solid #475569;
        border-radius: 8px;
        margin-bottom: 26px;
      }
      .actions, .w {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }
      form#checkout button[type="submit"],
      form#checkout a[role="button"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #1d4ed8;
        color: #ffffff;
        font-size: 18px;
        font-weight: 700;
        padding: 13px 26px;
        border: 2px solid #1e3a8a;
        border-radius: 8px;
        text-decoration: none;
        cursor: pointer;
      }
      #cancel-payment {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #ffffff;
        color: #0f172a;
        font-size: 18px;
        font-weight: 700;
        padding: 13px 24px;
        border: 2px solid #334155;
        border-radius: 8px;
        cursor: pointer;
      }
    </style>"""


def render(
    submit_id: str = "submit-payment",
    submit_class: str = "btn btn-primary",
    submit_text: str = "Submit Payment",
    submit_tag: str = "button",
    wrap: int = 0,
    reverse: bool = False,
    remove: bool = False,
    decoy_far: bool = False,
    overlay: bool = False,
) -> str:
    """A full checkout HTML document is rendered with configurable UI drift mutations."""
    if submit_tag == "a":
        submit_html = (
            f'<a id="{submit_id}" class="{submit_class}" role="button" '
            f'href="#pay" data-truth="submit">{submit_text}</a>'
        )
    else:
        submit_html = (
            f'<button id="{submit_id}" class="{submit_class}" type="submit" '
            f'data-truth="submit">{submit_text}</button>'
        )

    cancel_html = (
        '<button id="cancel-payment" class="btn btn-secondary" type="button" '
        'data-truth="cancel">Cancel Payment</button>'
    )

    controls: list[str] = []
    if not remove:
        controls.append(submit_html)
    controls.append(cancel_html)
    if reverse:
        controls.reverse()

    actions_inner = "\n          ".join(controls)
    for _ in range(wrap):
        actions_inner = f'<div class="w">{actions_inner}</div>'

    decoy_html = ""
    if decoy_far:
        decoy_html = (
            '\n      <button type="button" data-truth="decoy" '
            'style="position:absolute;right:20px;top:1500px">'
            "Submit Payment (demo)</button>"
        )

    overlay_html = ""
    if overlay:
        # Occludes via position:absolute;inset:0 (no pointer-events:none) so elementFromPoint
        # hits the backdrop/card instead of controls; never extracted by dom_extractor because
        # both backdrop and centered card are plain <div>s (no role/onclick, not <button>/<a>).
        overlay_html = (
            '\n      <div style="position:absolute;inset:0;background:rgba(15,23,42,0.78);'
            "border-radius:0 0 14px 14px;display:flex;align-items:center;"
            'justify-content:center">'
            '<div style="background:#0f172a;border:3px solid #ef4444;border-radius:12px;'
            'padding:24px 32px;text-align:center;box-shadow:0 20px 40px rgba(15,23,42,0.45)">'
            '<div style="color:#f87171;font-size:22px;font-weight:800;letter-spacing:0.04em">'
            "SESSION LOCKED</div>"
            '<div style="color:#f1f5f9;font-size:16px;font-weight:600;margin-top:8px">'
            "Blocking overlay covers checkout controls</div>"
            "</div></div>"
        )

    body_attr = ' style="min-height:1600px"' if decoy_far else ""

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Acme Pay</title>{_PAGE_STYLE}
  </head>
  <body{body_attr}>
    <header>
      <h1>Acme Pay</h1>
    </header>
    <main style="position:relative;min-height:400px">
      <form id="checkout">
        <h2>Payment</h2>
        <label for="card">Card number</label>
        <input id="card" name="card" type="text" />
        <div class="actions">
          {actions_inner}
        </div>
      </form>{decoy_html}{overlay_html}
    </main>
  </body>
</html>
"""


MUTATIONS: dict[str, tuple[dict[str, Any], str]] = {
    "id_renamed": ({"submit_id": "btn-7f3a9c"}, "heal"),
    "class_renamed": ({"submit_class": "x9d2 cta"}, "heal"),
    "text_reworded": ({"submit_text": "Pay Now"}, "heal"),
    "wrapped_deeper": ({"wrap": 3}, "heal"),
    "reordered": ({"reverse": True}, "heal"),
    "tag_changed": ({"submit_tag": "a"}, "heal"),
    "element_removed": ({"remove": True}, "refuse"),
    "decoy_far": ({"remove": True, "decoy_far": True}, "refuse"),
}
