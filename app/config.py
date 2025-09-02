from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str
    database_name: str

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str

    # Twilio WhatsApp
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str

    class Config:
        env_file = ".env"

settings = Settings()
print(settings.dict())  # Vérifie que tout se charge
