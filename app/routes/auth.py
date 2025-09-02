from fastapi import APIRouter, HTTPException, Depends
from random import randint
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.utils.email import send_verification_email
from app.utils.whatsapp import send_whatsapp_code
from app.schemas.user import UserCreate, UserResponse, LoginRequest
from app.crud.user import create_user, get_user_by_email
from app.config import settings
from app.utils.pin import set_user_pin, verify_user_pin
from typing import Optional
 
router = APIRouter(prefix="/auth", tags=["auth"])

# Connexion à MongoDB
client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.database_name]

# Stockage temporaire des codes et états de vérification
email_codes = {}
phone_codes = {}
verified_emails = set()  # Emails vérifiés
verified_phones = set()  # Téléphones vérifiés

# --- Schémas pour les requêtes intermédiaires ---
class EmailVerificationRequest(BaseModel):
    email: EmailStr

class VerifyEmailCodeRequest(BaseModel):
    email: EmailStr
    code: str

class PhoneVerificationRequest(BaseModel):
    phone: str

class VerifyPhoneCodeRequest(BaseModel):
    phone: str
    code: str

# Schéma pour les données PIN
class PinData(BaseModel):
    user_id: str
    pin: str

# Dépendance pour récupérer la DB
async def get_db() -> AsyncIOMotorDatabase:
    return db

# --- Étape 1: Envoi code email ---
@router.post("/send-email-code")
async def send_email_code(request: EmailVerificationRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        email = request.email

        # Vérifier si l'email existe déjà
        existing_user = await get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Cette adresse email est déjà utilisée"
            )

        # Génération du code
        code = f"{randint(100000, 999999)}"
        email_codes[email] = code

        # Envoi du mail
        await send_verification_email(email=email, code=code)
        return {
            "success": True,
            "message": f"Code de vérification envoyé à {email}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'envoi du code email: {str(e)}"
        )


# --- Étape 2: Vérification code email ---
@router.post("/verify-email-code")
async def verify_email_code(request: VerifyEmailCodeRequest):
    try:
        email = request.email
        code = request.code

        # Vérifier si le code existe et est correct
        if email not in email_codes:
            raise HTTPException(
                status_code=400,
                detail="Aucun code n'a été envoyé pour cette adresse email"
            )

        if email_codes[email] != code:
            raise HTTPException(
                status_code=400,
                detail="Le code de vérification est incorrect"
            )

        # Marquer l'email comme vérifié et supprimer le code
        verified_emails.add(email)
        del email_codes[email]
        return {
            "success": True,
            "message": "Adresse email vérifiée avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la vérification du code email"
        )

# --- Étape 3: Envoi code téléphone ---
@router.post("/send-phone-code")
async def send_phone_code(request: PhoneVerificationRequest):
    try:
        phone = request.phone
        code = await send_whatsapp_code(phone)
        phone_codes[phone] = code
        return {
            "success": True,
            "message": f"Code envoyé à {phone} via WhatsApp"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'envoi du code WhatsApp"
        )

# --- Étape 4: Vérification code téléphone ---
@router.post("/verify-phone-code")
async def verify_phone_code(request: VerifyPhoneCodeRequest):
    try:
        phone = request.phone
        code = request.code

        if phone not in phone_codes:
            raise HTTPException(
                status_code=400,
                detail="Aucun code n'a été envoyé pour ce numéro"
            )

        if phone_codes[phone] != code:
            raise HTTPException(
                status_code=400,
                detail="Le code de vérification WhatsApp est incorrect"
            )

        verified_phones.add(phone)
        del phone_codes[phone]
        return {
            "success": True,
            "message": "Numéro de téléphone vérifié avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la vérification du code WhatsApp"
        )

# --- Étape 5: Création utilisateur final ---
@router.post("/final-register")
async def final_register(user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        # Vérifier que l'email et le téléphone ont été vérifiés
        if user.email not in verified_emails:
            raise HTTPException(
                status_code=400,
                detail="L'adresse email n'a pas été vérifiée"
            )

        if user.phone not in verified_phones:
            raise HTTPException(
                status_code=400,
                detail="Le numéro de téléphone n'a pas été vérifié"
            )

        # Vérifier si l'email existe déjà
        existing_user = await get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Cette adresse email est déjà utilisée"
            )

        # Créer l'utilisateur
        created_user = await create_user(db, user)

        # Nettoyer les sets de vérification
        verified_emails.discard(user.email)
        verified_phones.discard(user.phone)

        # Convertir ObjectId en string
        created_user["_id"] = str(created_user["_id"])

        return {
            "success": True,
            "message": "Compte créé avec succès",
            "user": created_user  # 🔥 Retour complet, y compris l'id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du compte: {str(e)}"
        )


# --- Gestion du PIN ---
@router.post("/set-pin")
async def create_pin(data: PinData, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Définir le code PIN pour un utilisateur.
    """
    try:
        await set_user_pin(db, data.user_id, data.pin)
        return {
            "success": True,
            "message": "PIN défini avec succès"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la définition du PIN"
        )

@router.post("/verify-pin")
async def check_pin(data: PinData, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Vérifier le code PIN d'un utilisateur.
    """
    try:
        is_valid = await verify_user_pin(db, data.user_id, data.pin)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="PIN incorrect"
            )

        return {
            "success": True,
            "message": "PIN valide"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la vérification du PIN"
        )

@router.post("/login")
async def login(request: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Login utilisateur avec mot de passe ou PIN + option device_id.
    """
    try:
        user = None

        # Login classique (email ou téléphone + mot de passe)
        if request.email or request.phone:
            if request.email:
                user = await get_user_by_email(db, request.email)
            # Ajouter get_user_by_phone si login par téléphone
            if not user:
                raise HTTPException(status_code=400, detail="Utilisateur introuvable")
            if not request.password or not pwd_context.verify(request.password, user["password"]):
                raise HTTPException(status_code=400, detail="Mot de passe incorrect")

        # Login rapide par PIN + device_id
        elif request.pin and request.device_id:
            if request.email:
                user = await get_user_by_email(db, request.email)
            # Ajouter récupération par téléphone si nécessaire
            if not user:
                raise HTTPException(status_code=400, detail="Utilisateur introuvable")
            is_valid = await verify_user_pin(db, str(user["_id"]), request.pin)
            if not is_valid:
                raise HTTPException(status_code=400, detail="PIN incorrect")

        else:
            raise HTTPException(status_code=400, detail="Informations de connexion manquantes")

        # Retour user
        user["_id"] = str(user["_id"])
        return {
            "success": True,
            "message": "Connexion réussie",
            "user": user
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du login: {str(e)}")