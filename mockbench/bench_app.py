"""Offline deterministic HTML mutation generator for self-healing benchmarks is provided here."""

from typing import Any


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
        overlay_html = (
            '\n      <div style="position:absolute;inset:0;background:rgba(0,0,0,.45)"></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Acme Pay</title>
  </head>
  <body style="min-height:1600px">
    <header>
      <h1>Acme Pay</h1>
    </header>
    <main style="position:relative">
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
