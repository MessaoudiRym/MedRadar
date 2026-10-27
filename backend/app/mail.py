"""Email senders. To add a provider: write a class with name and send(),
then add it to make_mailer()."""

import logging

import httpx

from .config import (EMAIL_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME, EMAIL_PROVIDER,
                     EMAIL_TIMEOUT_SECONDS)

logger = logging.getLogger("medradar")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class MailError(Exception):
    """The email was not sent (network error, or refused by the provider)."""


class BrevoMailer:
    name = "brevo"

    def __init__(self, api_key, sender, sender_name, timeout):
        self.api_key = api_key
        self.sender = {"email": sender, "name": sender_name}
        self.timeout = timeout

    def send(self, to: str, subject: str, text: str, html: str):
        try:
            response = httpx.post(BREVO_URL, timeout=self.timeout, headers={
                "api-key": self.api_key, "accept": "application/json"}, json={
                "sender": self.sender, "to": [{"email": to}], "subject": subject,
                "textContent": text, "htmlContent": html})
        except httpx.HTTPError as error:
            raise MailError(f"Brevo unreachable: {type(error).__name__}") from None
        if response.status_code >= 300:
            # The body says why (unverified sender, invalid key...), never contains the key
            raise MailError(f"Brevo refused the email ({response.status_code}): {response.text[:300]}")


class FakeMailer:
    """Keeps the emails in memory: tests and end-to-end demo only, nothing is sent."""
    name = "fake"

    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, to: str, subject: str, text: str, html: str):
        if self.fail:
            raise MailError("Simulated failure")
        self.sent.append({"to": to, "subject": subject, "text": text, "html": html})


def make_mailer():
    """The configured sender, or None when alert emails are off."""
    if EMAIL_PROVIDER == "fake":
        logger.warning("Alert emails use the FAKE sender (tests and demo only): nothing is sent.")
        return FakeMailer()
    if not EMAIL_API_KEY:
        logger.info("Alert emails are off: EMAIL_API_KEY is not set.")
        return None
    if EMAIL_PROVIDER != "brevo":
        logger.error("Alert emails are off: unknown EMAIL_PROVIDER %r (supported: brevo).",
                     EMAIL_PROVIDER)
        return None
    if not EMAIL_FROM:
        logger.error("Alert emails are off: EMAIL_FROM (the sender address) is not set.")
        return None
    return BrevoMailer(EMAIL_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME, EMAIL_TIMEOUT_SECONDS)
