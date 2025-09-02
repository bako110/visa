# app/utils/whatsapp.py

import random
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from app.config import settings

def generate_code() -> str:
    """
    Génère un code de vérification à 6 chiffres.
    """
    return f"{random.randint(0, 999999):06d}"

async def send_whatsapp_code(phone: str) -> str:
    """
    Envoie un code de vérification via WhatsApp en utilisant Twilio.
    
    :param phone: Numéro du destinataire (ex: '+226XXXXXXXX')
    :return: Le code envoyé
    """
    try:
        code = generate_code()
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # Message décoré
        message_text = (
            "🔐 *Vérification de votre compte*\n\n"
            f"Bonjour 👋,\n\n"
            f"Voici votre code de vérification :\n\n"
            f"👉 *{code}*\n\n"
            "⏳ Ce code est valide pendant 10 minutes.\n"
            "🚀 Merci d'utiliser notre service !"
        )

        client.messages.create(
            body=message_text,
            from_=settings.twilio_whatsapp_from,
            to=f"whatsapp:{phone}"
        )

        return code
    
    except TwilioException as e:
        raise Exception(f"Erreur Twilio: {str(e)}")
    except Exception as e:
        raise Exception(f"Erreur lors de l'envoi WhatsApp: {str(e)}")