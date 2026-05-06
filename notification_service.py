import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

import requests

from utils.ai_classifier import generate_guest_message, generate_host_message


def send_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not smtp_user:
        return {
            "success": True,
            "simulated": True,
            "channel": "email",
            "to": to_email,
            "subject": subject,
            "message": f"[SIMULADO] Email listo para enviar a {to_email}",
        }

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return {"success": True, "simulated": False, "channel": "email", "to": to_email}
    except Exception as e:
        return {"success": False, "simulated": False, "channel": "email", "error": str(e)}


def send_whatsapp(phone: str, message: str) -> Dict[str, Any]:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_FROM", "")

    if not account_sid:
        return {
            "success": True,
            "simulated": True,
            "channel": "whatsapp",
            "to": phone,
            "message": f"[SIMULADO] WhatsApp listo para enviar a {phone}",
            "content_preview": message[:80] + "..." if len(message) > 80 else message,
        }

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        response = requests.post(
            url,
            auth=(account_sid, auth_token),
            data={
                "From": f"whatsapp:{from_number}",
                "To": f"whatsapp:{phone}",
                "Body": message,
            },
            timeout=10,
        )
        ok = response.status_code == 201
        return {"success": ok, "simulated": False, "channel": "whatsapp", "to": phone}
    except Exception as e:
        return {"success": False, "simulated": False, "channel": "whatsapp", "error": str(e)}


def dispatch_notifications(context: Dict[str, Any]) -> Dict[str, Any]:
    guest_msg = generate_guest_message(context)
    host_msg = generate_host_message(context)

    guest_email = context.get("guest_email", "guest@example.com")
    guest_phone = context.get("guest_phone", "+573000000000")
    reservation_id = context.get("reservation_id", "N/A")
    action = context.get("action", "actualizada")

    email_result = send_email(
        to_email=guest_email,
        subject=f"Actualización de tu reserva {reservation_id}",
        body=guest_msg,
    )
    whatsapp_result = send_whatsapp(phone=guest_phone, message=guest_msg)

    return {
        "guest_message": guest_msg,
        "host_message": host_msg,
        "email": email_result,
        "whatsapp": whatsapp_result,
    }
