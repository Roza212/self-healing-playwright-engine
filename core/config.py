"""Configuration parameters and thresholds for the self-healing engine are defined here."""

from dataclasses import dataclass


@dataclass
class HealConfig:
    """Weights, acceptance thresholds, and timeout settings are stored here."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    enabled: bool = True
    w_sem: float = 0.55
    w_role: float = 0.15
    w_spatial: float = 0.20
    w_attr: float = 0.10
    accept: float = 0.70
    accept_high_risk: float = 0.85
    min_margin: float = 0.08
    min_spatial: float = 0.10
    probe_timeout_ms: int = 3000
