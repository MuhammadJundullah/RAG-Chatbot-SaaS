import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from fastapi import HTTPException, status

from app.core.config import settings

async def send_brevo_email(to_email: str, subject: str, html_content: str):
    """
    Sends a transactional email using Brevo API.
    """
    # Konfigurasi API Key Brevo
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    # Instantiate the TransactionalEmailsApi client
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    transactional_api = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    # Tentukan detail pengirim
    # Mengambil dari environment variable atau menggunakan default
    sender_email = settings.DEFAULT_SENDER_EMAIL if settings.DEFAULT_SENDER_EMAIL else "noreply@smartai.com"
    # Menggunakan nama aplikasi dari settings jika ada, atau placeholder
    sender_name = getattr(settings, 'APP_NAME', 'SmartAI') 

    # Tentukan detail penerima p
    to_recipient = [{"email": to_email, "name": to_email}] 

    # Tentukan konten email
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to_recipient,
        subject=subject,
        html_content=html_content,
        sender={"email": sender_email, "name": sender_name},
        # Anda juga bisa menggunakan template_id untuk email yang lebih kompleks
        # template_id=1 # Contoh ID template
    )

    try:
        # Lakukan panggilan untuk mengirim email transaksional
        response = transactional_api.send_transac_email(send_smtp_email)
        logging.info(f"Email sent successfully to {to_email}. Response: {response}")
        # Objek response mungkin berisi 'messageId' atau yang serupa
    except ApiException as e:
        logging.error(f"Exception when calling Brevo API to send email to {to_email}: {e}")
        # Re-raise atau tangani exception sesuai kebutuhan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengirim email: {e.reason}"
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending email to {to_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan tak terduga saat mengirim email."
        )
