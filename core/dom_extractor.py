"""Single-call browser DOM candidate extraction and element inspection are implemented here."""

from playwright.sync_api import Locator, Page

from core.models import Candidate

CANDIDATE_SELECTOR = (
    'a[href], button, input:not([type=hidden]), select, textarea, [role], [onclick]'
)

JS_LIB = """
const ALLOWED_ATTRS = [
  "id", "name", "class", "data-test", "data-testid", "type", "placeholder", "href"
];

function clean(s) {
  return (s || "").replace(/\\s+/g, " ").trim().slice(0, 120);
}

function getRole(el) {
  const explicit = (el.getAttribute("role") || "").trim().toLowerCase();
  if (explicit) return explicit;
  const tag = el.tagName.toLowerCase();
  if (tag === "a") return "link";
  if (tag === "button") return "button";
  if (tag === "select") return "combobox";
  if (tag === "textarea") return "textbox";
  if (tag === "input") {
    const t = (el.getAttribute("type") || "text").trim().toLowerCase();
    if (t === "submit" || t === "button" || t === "reset") return "button";
    if (t === "checkbox") return "checkbox";
    if (t === "radio") return "radio";
    return "textbox";
  }
  return tag;
}

function getLabelText(el) {
  if (el.labels && el.labels.length > 0) {
    return clean(el.labels[0].innerText || el.labels[0].textContent || "");
  }
  const id = el.getAttribute("id");
  if (id) {
    try {
      const lbl = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lbl) return clean(lbl.innerText || lbl.textContent || "");
    } catch (e) {}
  }
  const parentLbl = el.closest("label");
  if (parentLbl) return clean(parentLbl.innerText || parentLbl.textContent || "");
  return "";
}

function getName(el) {
  const aria = clean(el.getAttribute("aria-label"));
  if (aria) return aria;
  const lbl = getLabelText(el);
  if (lbl) return lbl;
  const inner = clean(el.innerText || el.textContent || "");
  if (inner) return inner;
  const tag = el.tagName.toLowerCase();
  if (tag === "input") {
    const t = (el.getAttribute("type") || "text").trim().toLowerCase();
    if (t === "submit" || t === "button" || t === "reset") {
      const val = clean(el.value || el.getAttribute("value"));
      if (val) return val;
    }
  }
  const ph = clean(el.getAttribute("placeholder"));
  if (ph) return ph;
  const title = clean(el.getAttribute("title"));
  if (title) return title;
  return "";
}

function getAttrs(el) {
  const out = {};
  for (const k of ALLOWED_ATTRS) {
    const v = el.getAttribute(k);
    if (v !== null && v !== "") out[k] = v;
  }
  return out;
}

function getCssPath(el) {
  const parts = [];
  let cur = el;
  while (cur && cur.nodeType === 1 && cur.tagName.toLowerCase() !== "html") {
    const tag = cur.tagName.toLowerCase();
    let idx = 1;
    let sib = cur.previousElementSibling;
    while (sib) {
      if (sib.tagName.toLowerCase() === tag) idx += 1;
      sib = sib.previousElementSibling;
    }
    parts.unshift(`${tag}:nth-of-type(${idx})`);
    cur = cur.parentElement;
  }
  return "html > " + parts.join(" > ");
}

function inspectElement(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  const box = [
    rect.x + window.scrollX,
    rect.y + window.scrollY,
    rect.width,
    rect.height
  ];
  const visible = (
    rect.width > 0 &&
    rect.height > 0 &&
    style.display !== "none" &&
    style.visibility !== "hidden"
  );
  const ariaDisabled = (el.getAttribute("aria-disabled") || "").trim().toLowerCase();
  const enabled = !el.disabled && ariaDisabled !== "true";
  return {
    tag: el.tagName.toLowerCase(),
    role: getRole(el),
    name: getName(el),
    text: clean(el.innerText || el.textContent || ""),
    attrs: getAttrs(el),
    box: box,
    css_path: getCssPath(el),
    visible: visible,
    enabled: enabled
  };
}
"""


def extract_candidates(page: Page) -> list[Candidate]:
    """All candidate interactive elements on the page are extracted in a single evaluate call."""
    script = (
        f"() => {{ {JS_LIB}\n"
        f" return Array.from(document.querySelectorAll({CANDIDATE_SELECTOR!r}))"
        f".map(inspectElement); }}"
    )
    raw_list = page.evaluate(script)
    return [Candidate(**item) for item in raw_list]


def describe(locator: Locator) -> Candidate:
    """A single Playwright locator is inspected into a Candidate via the shared JS helpers."""
    script = f"(el) => {{ {JS_LIB}\n return inspectElement(el); }}"
    raw = locator.evaluate(script)
    return Candidate(**raw)
