"""Email sending via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


def send_email_sync(
    *,
    to_email: str,
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    from_email: str,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    smtp_host: str,
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    use_tls: bool = True,
) -> bool:
    """Send a single email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html or "", "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        return False
