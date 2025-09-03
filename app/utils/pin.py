# app/utils/pin.py

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
import secrets
from typing import Optional

# Configuration JWT
SECRET_KEY = "your-secret-key-here"  # À garder secret en production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10000

# Création du contexte pour hasher les PINs
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Fonctions utilitaires ---
async def set_user_pin(db: AsyncIOMotorDatabase, user_id: str, pin: str) -> str:
    """
    Définit ou met à jour le PIN de l'utilisateur et génère un token de connexion.
    Retourne le token JWT généré.
    """
    hashed_pin = pwd_context.hash(pin)
    
    # Mise à jour du PIN dans la base de données
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"pin": hashed_pin, "pin_created_at": datetime.now(timezone.utc)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    # Génération du token de connexion
    access_token = create_access_token(user_id)
    print(f"[DEBUG] Token généré (set_user_pin): {access_token}")  # 🔥 LOG ICI
    
    return access_token


async def verify_user_pin(db: AsyncIOMotorDatabase, user_id: str, pin: str) -> Optional[str]:
    """
    Vérifie si le PIN fourni est correct.
    Retourne un token JWT si la vérification réussit, None sinon.
    """
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or "pin" not in user:
        return None

    if pwd_context.verify(pin, user["pin"]):
        # PIN correct, génération du token
        access_token = create_access_token(user_id)
        print(f"[DEBUG] Token généré (verify_user_pin): {access_token}")  # 🔥 LOG ICI
        return access_token
    
    return None


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token JWT pour l'utilisateur.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": user_id,  # Subject (ID utilisateur)
        "exp": expire,   # Expiration
        "iat": datetime.now(timezone.utc),  # Issued at
        "jti": secrets.token_hex(16)  # JWT ID unique
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[str]:
    """
    Vérifie la validité d'un token JWT et retourne l'ID utilisateur.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.PyJWTError:
        return None


async def authenticate_with_pin(db: AsyncIOMotorDatabase, user_id: str, pin: str) -> dict:
    """
    Authentifie un utilisateur avec son PIN et retourne les informations de connexion.
    """
    token = await verify_user_pin(db, user_id, pin)
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="PIN incorrect ou utilisateur introuvable"
        )
    
    print(f"[DEBUG] Token retourné (authenticate_with_pin): {token}")  # 🔥 LOG ICI
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # en secondes
    }


async def refresh_token(db: AsyncIOMotorDatabase, current_token: str) -> Optional[str]:
    """
    Rafraîchit un token existant s'il est valide.
    """
    user_id = verify_access_token(current_token)
    if not user_id:
        return None
    
    # Vérifier que l'utilisateur existe toujours
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None
    
    # Générer un nouveau token
    new_token = create_access_token(user_id)
    print(f"[DEBUG] Nouveau token généré (refresh_token): {new_token}")  # 🔥 LOG ICI
    return new_token
