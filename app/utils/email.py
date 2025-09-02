import random
from email.message import EmailMessage
import aiosmtplib
from app.config import settings

async def send_verification_email(email: str, code: str):
    # Corps HTML décoré
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 20px;">
            <h2 style="color: #4CAF50; text-align: center;">🔐 Code de vérification</h2>
            <p style="font-size: 16px; color: #333;">
                Bonjour, <br><br>
                Voici votre code de vérification :
            </p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 24px; font-weight: bold; color: #4CAF50;">{code}</span>
            </div>
            <p style="font-size: 14px; color: #555;">
                Ce code expirera dans <strong>10 minutes</strong>. 
                Si vous n'êtes pas à l'origine de cette demande, veuillez ignorer cet email.
            </p>
            <p style="font-size: 14px; color: #999; text-align: center; margin-top: 20px;">
                Merci d'utiliser nos services. 🚀
            </p>
        </div>
    </body>
    </html>
    """

    # Création du message
    message = EmailMessage()
    message["From"] = settings.smtp_user
    message["To"] = email
    message["Subject"] = "🔐 Votre code de vérification"
    message.set_content(f"Bonjour,\n\nVotre code de vérification est : {code}\n\nMerci!")
    message.add_alternative(html_content, subtype="html")

    # Envoi du mail
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=True,
        username=settings.smtp_user,
        password=settings.smtp_password,
    )

    return code