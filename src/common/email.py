import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from src.settings.models import Settings

logger = logging.getLogger()


async def send(settings: Settings, content: str, to: str, subject: str) -> None:
    """
    Sends an email asynchronously using the provided settings.

    Args:
        settings (Settings): Configuration object containing SMTP settings, such as server, port, sender email, and credentials.
        content (str): The HTML or plain text content of the email body.
        to (str): Recipient email address.
        subject (str): Subject line of the email.

    Returns:
        None
    """
    message = MIMEText(content, "html")
    message["from"] = settings.email_settings.sender
    message["to"] = to
    message["subject"] = subject

    smtp = smtplib.SMTP(
        host=settings.email_settings.server,
        port=settings.email_settings.port,
    )

    try:
        logger.info("[EMAIL]: Starting TLS")
        await asyncio.to_thread(smtp.ehlo)
        await asyncio.to_thread(smtp.starttls)
        await asyncio.to_thread(smtp.ehlo)

        logger.info("[EMAIL]: Logging in to SMTP server")
        await asyncio.to_thread(
            smtp.login, settings.email_settings.sender, settings.email_settings.password
        )

        logger.info("[EMAIL]: Sending email to recipient")
        await asyncio.to_thread(smtp.send_message, message)
    except Exception as ex:
        logger.error(ex)
    finally:
        logger.info("[EMAIL]: Quitting SMTP session")
        await asyncio.to_thread(smtp.quit)
