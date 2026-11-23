"""Live end-to-end login scenarios against SauceDemo are verified here."""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.saucedemo_pages import LoginPage

pytestmark = pytest.mark.live


def test_standard_user_reaches_inventory(page: Page) -> None:
    """Navigation to the inventory page is verified for a valid standard user."""
    login_page = LoginPage(page).open()
    login_page.sign_in("standard_user")
    expect(page).to_have_url(re.compile(r"/inventory\.html"))


def test_locked_out_user_sees_error(page: Page) -> None:
    """An appropriate locked-out error banner is verified for a locked user."""
    login_page = LoginPage(page).open()
    login_page.sign_in("locked_out_user")
    assert "locked out" in login_page.text(LoginPage.ERROR).lower()
