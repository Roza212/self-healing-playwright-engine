"""Three-tier self-healing Playwright locator engine and refusal exception are implemented here."""

import re
from typing import Any

import numpy as np
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from core.config import HealConfig
from core.dom_extractor import describe, extract_candidates
from core.embedder import Embedder
from core.models import Candidate, ElementSpec
from core.scoring import (
    attr_tokens,
    combine,
    jaccard,
    reject_reason,
    role_score,
    spatial_score,
    tokens,
)

_VOLATILE_ID_RE = re.compile(r"(?:\d{4,}|[0-9a-fA-F]{8,})")


class HealingRefused(AssertionError):
    """AssertionError subclass raised when all healing tiers fail or are rejected by gates."""

    def __init__(self, failure_class: str, top: list[dict[str, Any]], message: str = "") -> None:
        """The failure classification and top candidate diagnostics are stored on the exception."""
        self.failure_class = failure_class
        self.top = top
        super().__init__(message or f"Healing refused ({failure_class}): top={top}")


def _viewport_wh(page: Page) -> tuple[float, float]:
    """Current viewport width and height are returned, falling back to (1280.0, 720.0)."""
    vp = page.viewport_size
    if vp and vp.get("width") and vp.get("height"):
        return (float(vp["width"]), float(vp["height"]))
    return (1280.0, 720.0)


def _spec_doc(spec: ElementSpec) -> str:
    """A Candidate-style semantic document string is built from an ElementSpec."""
    role_part = spec.role or "element"
    label_part = spec.accessible_name or spec.name
    return f"{role_part}: {label_part}"


def _fp_doc(fp: dict[str, Any]) -> str:
    """A Candidate-style semantic document string is built from a stored fingerprint dict."""
    role_part = fp.get("role") or "element"
    label_part = fp.get("name") or fp.get("text") or ""
    return f"{role_part}: {label_part}"


def _build_selector(page: Page, cand: Candidate) -> str:
    """A stable Playwright selector is synthesized for the winning candidate and verified unique."""
    candidates_to_try: list[str] = []
    dt = cand.attrs.get("data-test")
    if dt:
        candidates_to_try.append(f'[data-test="{dt}"]')
    el_id = cand.attrs.get("id")
    if el_id and not _VOLATILE_ID_RE.search(str(el_id)):
        candidates_to_try.append(f'[id="{el_id}"]')
    if cand.role and cand.name and '"' not in cand.name:
        candidates_to_try.append(f'role={cand.role}[name="{cand.name}"]')
    candidates_to_try.append(cand.css_path)

    for sel in candidates_to_try:
        try:
            if page.locator(sel).count() == 1:
                return sel
        except Exception:
            continue
    return cand.css_path


class SelfHealingLocator:
    """Three-tier self-healing locator resolver with fingerprinting and audit event recording."""

    def __init__(
        self,
        cfg: HealConfig | None = None,
        embedder: Embedder | None = None,
        audit: Any = None,
        test_id: str = "",
    ) -> None:
        """Configuration, embedder, audit sink, fingerprint store, and heal log are initialized."""
        self.cfg = cfg or HealConfig()
        self.embedder = embedder or Embedder(self.cfg.model_name)
        self.audit = audit
        self.test_id = test_id
        self.store: dict[str, dict[str, Any]] = {}
        self.heals: list[dict[str, Any]] = []

    def _emit(self, event: dict[str, Any], healed: bool) -> None:
        """An event is logged to self.heals on continuation and forwarded to the audit recorder."""
        if healed:
            self.heals.append(event)
        if self.audit is not None:
            self.audit.record(event)

    def locate(self, page: Page, spec: ElementSpec) -> Locator:
        """A Playwright Locator is resolved for spec via Tier 1, Tier 2, or Tier 3 healing."""
        # Tier 1: Primary selector
        loc = page.locator(spec.primary)
        try:
            loc.first.wait_for(state="visible", timeout=self.cfg.probe_timeout_ms)
            if spec.name not in self.store:
                cand = describe(loc.first)
                self.store[spec.name] = {
                    "role": cand.role,
                    "name": cand.name,
                    "text": cand.text,
                    "box": cand.box,
                    "viewport": _viewport_wh(page),
                    "attr_tokens": attr_tokens(cand.attrs),
                }
            return loc
        except PlaywrightTimeoutError:
            if not self.cfg.enabled:
                raise

        fp = self.store.get(spec.name)
        want = tokens(
            " ".join(
                filter(
                    None,
                    [
                        spec.accessible_name,
                        fp.get("name") if fp else None,
                        fp.get("text") if fp else None,
                    ],
                )
            )
        )

        # Tier 2: Playwright native get_by_role fallback
        if spec.role and spec.accessible_name:
            t2_loc = page.get_by_role(spec.role, name=spec.accessible_name, exact=True)
            if t2_loc.count() == 1 and t2_loc.first.is_visible():
                t2_cand = describe(t2_loc.first)
                if reject_reason(spec, t2_cand, want, spatial=None, cfg=self.cfg) is None:
                    new_sel = f'role={spec.role}[name="{spec.accessible_name}"]'
                    event = {
                        "test": self.test_id,
                        "logical_name": spec.name,
                        "failure_class": "NATIVE_FALLBACK",
                        "tier": 2,
                        "old_selector": spec.primary,
                        "new_selector": new_sel,
                        "scores": {
                            "semantic": 1.0,
                            "role": 1.0,
                            "spatial": None,
                            "attr": None,
                            "total": 1.0,
                        },
                        "runner_up": None,
                        "margin": None,
                        "url": page.url,
                    }
                    self._emit(event, healed=True)
                    return t2_loc.first

        # Tier 3: Multi-signal candidate scoring (MiniLM + role + spatial + attr Jaccard)
        cands = extract_candidates(page)
        queries = [_spec_doc(spec)]
        if fp:
            q_fp = _fp_doc(fp)
            if q_fp not in queries:
                queries.append(q_fp)

        sem_scores: list[float] = []
        if cands:
            q_vecs = self.embedder.encode(queries)
            c_vecs = self.embedder.encode([c.doc() for c in cands])
            sim_matrix = np.matmul(c_vecs, q_vecs.T)
            raw_max = sim_matrix.max(axis=1)
            sem_scores = [float(np.clip(val, 0.0, 1.0)) for val in raw_max]

        expected_role = spec.role or (fp.get("role") if fp else None)
        scored_all: list[dict[str, Any]] = []
        accepted: list[dict[str, Any]] = []

        for idx, cand in enumerate(cands):
            sem = sem_scores[idx]
            r_score = role_score(expected_role, cand.role)
            sp_score: float | None = None
            at_score: float | None = None
            if fp is not None:
                sp_score = spatial_score(
                    fp["box"],
                    cand.box,
                    fp.get("viewport") or _viewport_wh(page),
                )
                at_score = jaccard(fp["attr_tokens"], attr_tokens(cand.attrs))

            reason = reject_reason(spec, cand, want, spatial=sp_score, cfg=self.cfg)
            tot = combine(sem, r_score, sp_score, at_score, self.cfg)
            entry = {
                "cand": cand,
                "scores": {
                    "semantic": round(sem, 4),
                    "role": round(r_score, 4),
                    "spatial": round(sp_score, 4) if sp_score is not None else None,
                    "attr": round(at_score, 4) if at_score is not None else None,
                    "total": round(tot, 4),
                },
                "total": tot,
                "reject": reason,
            }
            scored_all.append(entry)
            if reason is None:
                accepted.append(entry)

        scored_all.sort(key=lambda x: x["total"], reverse=True)
        accepted.sort(key=lambda x: x["total"], reverse=True)

        top3 = [
            {
                "name": item["cand"].name or item["cand"].text,
                "role": item["cand"].role,
                "total": round(item["total"], 4),
                "reject": item["reject"],
            }
            for item in scored_all[:3]
        ]

        threshold = self.cfg.accept_high_risk if spec.risk == "high" else self.cfg.accept

        if not accepted or accepted[0]["total"] < threshold:
            best_scores = (
                accepted[0]["scores"]
                if accepted
                else (
                    scored_all[0]["scores"]
                    if scored_all
                    else {
                        "semantic": 0.0,
                        "role": 0.0,
                        "spatial": None,
                        "attr": None,
                        "total": 0.0,
                    }
                )
            )
            event = {
                "test": self.test_id,
                "logical_name": spec.name,
                "failure_class": "ELEMENT_REMOVED",
                "tier": 3,
                "old_selector": spec.primary,
                "new_selector": None,
                "scores": best_scores,
                "runner_up": round(accepted[1]["total"], 4) if len(accepted) > 1 else None,
                "margin": (
                    round(accepted[0]["total"] - accepted[1]["total"], 4)
                    if len(accepted) > 1
                    else None
                ),
                "url": page.url,
            }
            self._emit(event, healed=False)
            raise HealingRefused("ELEMENT_REMOVED", top3)

        winner = accepted[0]
        runner_up_val = accepted[1]["total"] if len(accepted) > 1 else 0.0
        margin_val = winner["total"] - runner_up_val

        if len(accepted) > 1 and margin_val < self.cfg.min_margin:
            event = {
                "test": self.test_id,
                "logical_name": spec.name,
                "failure_class": "AMBIGUOUS",
                "tier": 3,
                "old_selector": spec.primary,
                "new_selector": None,
                "scores": winner["scores"],
                "runner_up": round(runner_up_val, 4),
                "margin": round(margin_val, 4),
                "url": page.url,
            }
            self._emit(event, healed=False)
            raise HealingRefused("AMBIGUOUS", top3)

        new_sel = _build_selector(page, winner["cand"])
        event = {
            "test": self.test_id,
            "logical_name": spec.name,
            "failure_class": "LOCATOR_DRIFT_HEALED",
            "tier": 3,
            "old_selector": spec.primary,
            "new_selector": new_sel,
            "scores": winner["scores"],
            "runner_up": round(runner_up_val, 4) if len(accepted) > 1 else None,
            "margin": round(margin_val, 4),
            "url": page.url,
        }
        self._emit(event, healed=True)
        return page.locator(new_sel).first
