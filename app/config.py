from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str
    database_name: str

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str

    class Config:
        env_file = ".env"  # indique à Pydantic de lire le fichier .env

settings = Settings()
