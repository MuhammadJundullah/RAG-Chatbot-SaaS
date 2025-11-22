import logging
import requests
from typing import Optional

from app.core.config import settings


def send_brevo_sms(to_phone: str, text: str) -> bool:
    """
    Sends transactional SMS via Brevo.
    Returns True on success, False on failure (logs error, non-raising).
    """
    api_key = settings.BREVO_API_KEY
    sender = getattr(settings, "BREVO_SMS_SENDER", "InfoSMS")

    if not api_key:
        logging.warning("BREVO_API_KEY not set; skipping SMS send.")
        return False

    url = "https://api.brevo.com/v3/transactionalSMS/sms"
    payload = {
        "sender": sender,
        "recipient": to_phone,
        "content": text,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201, 202):
            logging.info("SMS sent to %s via Brevo", to_phone)
            return True
        logging.error("Failed to send SMS to %s: %s %s", to_phone, resp.status_code, resp.text)
        return False
    except Exception as e:
        logging.error("Error sending SMS to %s: %s", to_phone, e)
        return False
