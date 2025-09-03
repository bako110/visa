from fastapi import APIRouter, HTTPException, Depends
from random import randint
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from passlib.context import CryptContext
from app.utils.email import send_verification_email
from app.utils.whatsapp import send_whatsapp_code
from app.schemas.user import UserCreate, UserResponse, LoginRequest
from app.crud.user import create_user, get_user_by_email, get_user_by_phone, delete_user
from app.config import settings
from app.utils.pin import set_user_pin, verify_user_pin, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from typing import Optional
from bson import ObjectId
from datetime import datetime, timedelta, timezone


router = APIRouter(prefix="/auth", tags=["auth"])

# Configuration du hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# Schéma de connexion enrichi
class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    device_id: Optional[str] = None

# Dépendance pour récupérer la DB
async def get_db() -> AsyncIOMotorDatabase:
    return db

# Fonction helper pour valider ObjectId
def is_valid_object_id(user_id: str) -> bool:
    try:
        ObjectId(user_id)
        return True
    except:
        return False

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
    """
    Inscription finale : Crée un utilisateur et retourne toutes ses infos.
    """
    try:
        # Vérifier email vérifié
        if user.email not in verified_emails:
            raise HTTPException(
                status_code=400,
                detail="L'adresse email n'a pas été vérifiée"
            )

        # Vérifier téléphone vérifié
        if user.phone not in verified_phones:
            raise HTTPException(
                status_code=400,
                detail="Le numéro de téléphone n'a pas été vérifié"
            )

        # Vérifier si email existe déjà
        existing_user = await get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Cette adresse email est déjà utilisée"
            )

        # Créer l'utilisateur
        result = await create_user(db, user)
        user_id = result.inserted_id

        # 🔥 Récupérer et afficher toutes les infos
        created_user = await db.users.find_one({"_id": user_id})
        if not created_user:
            raise HTTPException(
                status_code=500,
                detail="Utilisateur non trouvé après création"
            )

        # Convertir ObjectId en str
        created_user["_id"] = str(created_user["_id"])

        # 🔥 Debug complet dans la console
        # print("[DEBUG] Nouvel utilisateur créé :", created_user)

        # Nettoyage des vérifications
        verified_emails.discard(user.email)
        verified_phones.discard(user.phone)

        # Retour complet
        return {
            "success": True,
            "message": "Compte créé avec succès",
            "user": created_user
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du compte: {str(e)}"
        )


# --- Gestion du PIN améliorée avec token ---
@router.post("/set-pin")
async def create_pin(data: PinData, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Définir le code PIN pour un utilisateur et retourner le token JWT.
    Si la création du PIN échoue, supprimer l'utilisateur.
    """
    try:
        # Valider l'ID utilisateur
        if not is_valid_object_id(data.user_id):
            raise HTTPException(status_code=400, detail="ID utilisateur invalide")

        # Valider le format du PIN (4-6 chiffres)
        if not data.pin.isdigit() or not (4 <= len(data.pin) <= 6):
            raise HTTPException(status_code=400, detail="Le PIN doit contenir entre 4 et 6 chiffres")

        # Vérifier que l'utilisateur existe
        user = await db.users.find_one({"_id": ObjectId(data.user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")

        # Définir le PIN et générer le token
        access_token = await set_user_pin(db, data.user_id, data.pin)

        # Préparer le profil utilisateur pour le retour
        user_profile = {
            "_id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "avatar": user.get("avatar"), 
            "balance": user.get("balance", 0.0),
            "phone": user.get("phone"),
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
        }

        return {
            "success": True,
            "message": "PIN défini avec succès",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_profile
        }

    except HTTPException:
        raise
    except Exception as e:
        # Suppression de l'utilisateur si une erreur survient
        try:
            await db.users.delete_one({"_id": ObjectId(data.user_id)})
            print(f"[DEBUG] Utilisateur {data.user_id} supprimé après échec du PIN")
        except Exception as delete_err:
            print(f"[ERROR] Impossible de supprimer l'utilisateur après échec: {delete_err}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la définition du PIN: {str(e)}"
        )



@router.post("/verify-pin")
async def check_pin(data: PinData, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Vérifier le code PIN d'un utilisateur.
    """
    try:
        # Valider l'ID utilisateur
        if not is_valid_object_id(data.user_id):
            raise HTTPException(
                status_code=400,
                detail="ID utilisateur invalide"
            )
        
        # Vérifier que l'utilisateur existe
        user = await db.users.find_one({"_id": ObjectId(data.user_id)})
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Utilisateur introuvable"
            )
        
        is_valid = await verify_user_pin(db, data.user_id, data.pin)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="PIN incorrect"
            )

        return {
            "success": True,
            "message": "PIN valide",
            "user_id": data.user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification du PIN: {str(e)}"
        )

@router.post("/login")
async def login(request: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Login utilisateur par mot de passe ou PIN.
    Retourne un JWT + toutes les infos utilisateur.
    """
    try:
        user = None

        # Vérification email ou téléphone
        if request.email:
            user = await db.users.find_one({"email": request.email})
        elif request.phone:
            user = await db.users.find_one({"phone": request.phone})
        else:
            raise HTTPException(status_code=400, detail="Email ou téléphone requis")

        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Vérification par mot de passe
        if request.password:
            if not pwd_context.verify(request.password, user["password"]):
                raise HTTPException(status_code=401, detail="Mot de passe incorrect")

        # Vérification par PIN
        elif request.pin:
            if not user.get("pin"):
                raise HTTPException(status_code=400, detail="Aucun PIN défini pour cet utilisateur")

            if not pwd_context.verify(request.pin, user["pin"]):
                raise HTTPException(status_code=401, detail="PIN incorrect")

        else:
            raise HTTPException(status_code=400, detail="Mot de passe ou PIN requis")

        # Mise à jour du last_login
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        # Génération du token JWT avec user_id + email + phone
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            user_id=str(user["_id"]),
            email=user.get("email"),
            phone=user.get("phone"),
            expires_delta=access_token_expires,
        )

        # Réponse complète
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # en secondes
            "user": {
                "id": str(user["_id"]),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "name": user.get("name"),
                "avatar": user.get("avatar"),
                "device_id": user.get("device_id"),
                "is_active": user.get("is_active", False),
                "is_verified": user.get("is_verified", False),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
                "last_login": datetime.utcnow().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("Erreur login:", e)
        traceback.print_exc()  # pour voir l’erreur exacte dans les logs
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# --- Endpoint pour changer le PIN ---
@router.post("/change-pin")
async def change_pin(
    old_pin_data: dict, 
    new_pin: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Changer le PIN d'un utilisateur après vérification de l'ancien PIN.
    """
    try:
        user_id = old_pin_data.get("user_id")
        old_pin = old_pin_data.get("old_pin")
        
        if not user_id or not old_pin:
            raise HTTPException(
                status_code=400,
                detail="ID utilisateur et ancien PIN requis"
            )
        
        # Vérifier l'ancien PIN
        is_valid = await verify_user_pin(db, user_id, old_pin)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Ancien PIN incorrect"
            )
        
        # Valider le nouveau PIN
        if not new_pin.isdigit() or not (4 <= len(new_pin) <= 6):
            raise HTTPException(
                status_code=400,
                detail="Le nouveau PIN doit contenir entre 4 et 6 chiffres"
            )
        
        # Définir le nouveau PIN
        await set_user_pin(db, user_id, new_pin)
        
        return {
            "success": True,
            "message": "PIN modifié avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du changement de PIN: {str(e)}"
        )

# suppression des utilsateur

@router.delete("/delete-user")
async def delete_user_route(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Endpoint pour supprimer un utilisateur par ID (soft delete).
    """
    success = await delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Suppression échouée ou utilisateur introuvable")
    return {"success": True, "message": "Utilisateur supprimé avec succès"}