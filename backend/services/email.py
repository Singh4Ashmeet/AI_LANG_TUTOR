from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from ..config import settings


def _otp_html(username: str, code: str) -> str:
    digits = "".join(f"<span style='border:1px solid #e2e8f0;padding:8px 10px;margin:2px;font-family:monospace;font-size:20px;border-radius:6px;'>{d}</span>" for d in code)
    return f"""
    <div style="font-family:Arial,sans-serif;color:#0f172a;">
      <h2 style="margin-bottom:8px;">LinguAI</h2>
      <p>Hi {username},</p>
      <p>Your verification code is:</p>
      <div style="margin:12px 0;">{digits}</div>
      <p>This code expires in 10 minutes.</p>
      <p>If you didn't request this, ignore this email.</p>
      <p>Never share this code with anyone.</p>
    </div>
    """


async def send_otp_email(to_email: str, username: str, code: str) -> None:
    if not settings.gmail_address or not settings.gmail_app_password:
        raise RuntimeError("Gmail SMTP not configured")

    message = EmailMessage()
    message["From"] = settings.gmail_address
    message["To"] = to_email
    message["Subject"] = "LinguAI: Your verification code"
    message.set_content("Your LinguAI verification code is: " + code)
    message.add_alternative(_otp_html(username, code), subtype="html")

    smtp = aiosmtplib.SMTP(hostname="smtp.gmail.com", port=587, start_tls=True)
    await smtp.connect()
    await smtp.login(settings.gmail_address, settings.gmail_app_password)
    await smtp.send_message(message)
    await smtp.quit()
