"""SauceDemo Page Object definitions are declared here using ElementSpec."""

from core.models import ElementSpec
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Locators and user actions for the SauceDemo login screen are defined here."""

    url = "https://www.saucedemo.com/"

    USER = ElementSpec("sd.username", '[data-test="username"]', "textbox", "Username")
    PASS = ElementSpec("sd.password", '[data-test="password"]')
    LOGIN = ElementSpec("sd.login", '[data-test="login-button"]', "button", "Login")
    ERROR = ElementSpec("sd.error", '[data-test="error"]')

    def sign_in(self, user: str, pwd: str = "secret_sauce") -> None:
        """Credentials are entered and the login form is submitted."""
        self.fill(self.USER, user)
        self.fill(self.PASS, pwd)
        self.click(self.LOGIN)
