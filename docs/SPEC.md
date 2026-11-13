# Self-Healing Playwright Engine (Lite) - spec

Tiers, in order:
T1 primary selector (wait visible). Success -> store fingerprint if missing.
T2 get_by_role(role, name=accessible_name, exact=True); 1 visible match + hard gates.
T3 MiniLM cosine + role + spatial + attribute Jaccard; hard gates; threshold; margin.
Refuse -> HealingRefused (AssertionError) with top-3 candidates.
After any heal -> SSIM vs pre-drift screenshot + occlusion check.
Hard gates: hidden, disabled, role_mismatch, opposite_action, moved_far (spatial < 0.10).
Weights: sem 0.55, role 0.15, spatial 0.20, attr 0.10 (renormalised over present signals).
accept 0.70, accept_high_risk 0.85, min_margin 0.08.
Event classes: NATIVE_FALLBACK, LOCATOR_DRIFT_HEALED, ELEMENT_REMOVED, AMBIGUOUS.
Bench: 6 drift mutations must heal to data-truth=submit; element_removed and
decoy_far must refuse.
