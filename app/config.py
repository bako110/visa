from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    database_name: str = "visa_db"

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str

    class Config:
        env_file = ".env"  # indique à Pydantic de lire le fichier .env

settings = Settings()
