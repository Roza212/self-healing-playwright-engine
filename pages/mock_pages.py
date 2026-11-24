"""Page Object Model for the offline mock checkout benchmark page is defined here."""

from core.models import ElementSpec
from pages.base_page import BasePage


class MockCheckoutPage(BasePage):
    """Element specifications for the mock checkout form are encapsulated here."""

    SUBMIT = ElementSpec(
        "mock.submit",
        'form#checkout > div.actions > button#submit-payment.btn-primary'
        ':nth-child(1):has-text("Submit Payment")',
        "button",
        "Submit Payment",
    )
    CARD = ElementSpec("mock.card", "#card", "textbox", "Card number")
