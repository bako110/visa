from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserModel(BaseModel):
    """
    Modèle principal de l'utilisateur pour validation.
    """

    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")
    phone: str = Field(..., min_length=8, max_length=15, description="Numéro de téléphone avec indicatif international")
    name: str = Field(..., min_length=2, max_length=50, description="Nom complet de l'utilisateur")
    password: str = Field(..., min_length=6, description="Mot de passe sécurisé")
    pin: Optional[str] = Field(None, min_length=4, max_length=6, description="Code PIN optionnel pour sécuriser le compte")
 ")
