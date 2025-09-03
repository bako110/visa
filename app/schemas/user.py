from typing import Optional
from pydantic import BaseModel, EmailStr


# --- Schéma pour la création d'un utilisateur ---
class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    name: str
    password: str
    device_id: Optional[str] = None  # Pour final-register


# --- Schéma pour la réponse API utilisateur ---
class UserResponse(BaseModel):
    email: EmailStr
    phone: str
    name: str
    avatar: Optional[str] = None  # Ajout si tu veux renvoyer l'avatar


# --- Schéma pour la requête de connexion ---
class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    device_id: Optional[str] = None
