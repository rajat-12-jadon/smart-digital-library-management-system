"""
utils/email_utils.py

Generic email sending -- one function, send_email(), that every
notification (due tomorrow, overdue, reservation ready) reuses. Keeps
SMTP details in exactly one place.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_CONFIG

logger = logging.getLogger(__name__)


class EmailConfigError(Exception):
    # raised when sender_email/sender_password aren't set -- a clearer
    # error than whatever cryptic thing smtplib would raise trying to
    # authenticate with an empty password
    pass


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Sends a plain-text email via Gmail's SMTP server. Raises
    EmailConfigError if credentials aren't set up, or smtplib's own
    exceptions (e.g. SMTPAuthenticationError) if sending fails for
    other reasons -- callers should catch and handle both.
    """
    sender_email = EMAIL_CONFIG["sender_email"]
    sender_password = EMAIL_CONFIG["sender_password"]

    if not sender_email or not sender_password:
        raise EmailConfigError(
            "Email credentials are not configured. Set LMS_EMAIL_ADDRESS and "
            "LMS_EMAIL_APP_PASSWORD environment variables."
        )

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # `with` here guarantees the connection closes even if sending
    # fails partway through -- same resource-safety pattern as our
    # database context manager
    with smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"]) as server:
        server.starttls()  # upgrades the connection to encrypted (TLS)
        server.login(sender_email, sender_password)
        server.send_message(message)

    logger.info("Email sent to %s: %s", to_email, subject)