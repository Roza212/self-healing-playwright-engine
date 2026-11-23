"""Base Page Object Model class is provided here for all application pages."""

from typing import Any, Self

from playwright.sync_api import Locator, Page, expect

from core.models import ElementSpec


class BasePage:
    """Common navigation and element interaction methods are encapsulated here."""

    url: str = ""

    def __init__(self, page: Page, healer: Any = None) -> None:
        """The page instance and optional self-healing locator engine are initialized."""
        self.page = page
        self.healer = healer

    def open(self) -> Self:
        """The target page URL is opened and waited on until DOM content is loaded."""
        self.page.goto(self.url, wait_until="domcontentloaded")
        return self

    def load_html(self, html: str) -> Self:
        """Raw HTML markup is injected directly into the page for offline testing."""
        self.page.set_content(html, wait_until="domcontentloaded")
        return self

    def el(self, spec: ElementSpec) -> Locator:
        """A Playwright locator is resolved directly or delegated to the healer."""
        if self.healer is None:
            return self.page.locator(spec.primary)
        return self.healer.locate(self.page, spec)

    def click(self, spec: ElementSpec) -> None:
        """The element is verified as enabled before a click action is performed."""
        loc = self.el(spec)
        expect(loc).to_be_enabled()
        loc.click()

    def fill(self, spec: ElementSpec, value: str) -> None:
        """The element is verified as editable before text is filled into it."""
        loc = self.el(spec)
        expect(loc).to_be_editable()
        loc.fill(value)

    def text(self, spec: ElementSpec) -> str:
        """The element is verified as visible before its trimmed inner text is returned."""
        loc = self.el(spec)
        expect(loc).to_be_visible()
        return loc.inner_text().strip()
