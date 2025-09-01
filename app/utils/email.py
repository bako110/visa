import random
from email.message import EmailMessage
import aiosmtplib
from app.config import settings

async def send_verification_email(to_email: str):
    code = f"{random.randint(0, 999999):06d}"  # code à 6 chiffres

    message = EmailMessage()
    message["From"] = settings.smtp_user
    message["To"] = to_email
    message["Subject"] = "Votre code de vérification"
    message.set_content(f"Bonjour,\n\nVotre code de vérification est : {code}\n\nMerci!")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=True,
        username=settings.smtp_user,
        password=settings.smtp_password,
    )

    return code
