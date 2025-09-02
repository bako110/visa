# app/utils/pin.py

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext

# Création du contexte pour hasher les PINs
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Fonctions utilitaires ---
async def set_user_pin(db: AsyncIOMotorDatabase, user_id: str, pin: str):
    """
    Définit ou met à jour le PIN de l'utilisateur.
    """
    hashed_pin = pwd_context.hash(pin)

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"pin": hashed_pin}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")


async def verify_user_pin(db: AsyncIOMotorDatabase, user_id: str, pin: str) -> bool:
    """
    Vérifie si le PIN fourni est correct.
    """
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or "pin" not in user:
        return False

    return pwd_context.verify(pin, user["pin"])
