# Architecture Writeup: Self-Healing Playwright Engine

UI tests often fail when markup changes -- a renamed ID, a hashed CSS class, an extra wrapper `<div>`, or a reworded button label -- even when a user can still complete the flow. Sending every broken selector straight to an embedding model is slow and unsafe: sentence embeddings place antonyms like "Submit Payment" and "Cancel Payment" close together. A tiered ladder handles most drift with deterministic browser queries first and uses ML scoring only as a gated fallback.

## The Three-Tier Ladder

- **T1 (Primary selector):** Probes the CSS or attribute selector and, on first hit, stores a baseline fingerprint (role, accessible name, text, bounding box, attribute tokens).
- **T2 (Exact ARIA fallback):** Calls `page.get_by_role(role, name=accessible_name, exact=True)` and accepts only a single visible match that passes all hard gates (`NATIVE_FALLBACK`).
- **T3 (Multi-signal semantic fallback):** Scores interactive DOM elements on MiniLM cosine similarity (0.55), ARIA role compatibility (0.15), Gaussian spatial proximity (0.20), and attribute Jaccard overlap (0.10), accepting only at or above threshold (`0.70`, or `0.85` for high-risk actions) with a `0.08` lead over the runner-up (`LOCATOR_DRIFT_HEALED`).

## Hard Gates and Safe Refusal

Before scoring can accept a match, every candidate must clear five hard gates: `hidden`, `disabled`, `role_mismatch`, `opposite_action` (lexical antonym sets such as submit/cancel or pay/refund), and `moved_far` (`spatial < 0.10`). When an element is genuinely removed or replaced only by a far-away decoy, the engine must raise `HealingRefused` with the top three candidates rather than click Cancel or an unrelated control. A loud test failure is recoverable; a false pass on a broken checkout is not.

## Why SSIM Over Pixel Diff

DOM healing cannot tell whether an overlay covers the page or the layout collapsed. After a heal, `verify_after_heal` runs `document.elementFromPoint` for occlusion and compares full-page screenshots with Structural Similarity (SSIM) instead of raw pixel equality. Rendering jitter breaks pixel diffs: in `tests/test_visual.py`, `-1/0/+1` noise alters over half of all pixels while SSIM stays above `0.97`, whereas a blocking overlay drops SSIM below `0.95` (`MAJOR`) and fails the gate.

## What This Does Not Do

This engine does not heal assertions or auto-commit rewritten selectors; heals are logged to JSONL and checked against a CI budget. See the [README](../README.md) for setup and benchmark results.
