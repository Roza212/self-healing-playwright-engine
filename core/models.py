"""Data models for element specifications and DOM candidates are defined here."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ElementSpec:
    """Immutable specification by which a target UI element is described."""

    name: str
    primary: str
    role: str | None = None
    accessible_name: str | None = None
    risk: str = "normal"


@dataclass
class Candidate:
    """Extracted DOM element candidate that is evaluated during healing."""

    tag: str
    role: str
    name: str
    text: str
    attrs: dict[str, Any]
    box: list[float]
    css_path: str
    visible: bool = True
    enabled: bool = True

    def doc(self) -> str:
        """A text representation of the candidate is constructed for semantic scoring."""
        return f"{self.role}: {self.name or self.text or self.attrs.get('placeholder', '')}"
