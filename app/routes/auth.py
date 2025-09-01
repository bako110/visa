from fastapi import APIRouter, HTTPException
from random import randint
from app.utils.email import send_verification_email
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import create_user, get_user_by_email
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# MongoDB
client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.database_name]

# Stockage temporaire des codes
email_codes = {}
phone_codes = {}

# Étape 1: Envoi code email
@router.post("/send-email-code")
async def send_email_code(email: str):
    if await get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    code = f"{randint(100000, 999999)}"
    email_codes[email] = code
    await send_verification_email(email, code)
    return {"message": f"Code envoyé à {email}"}

# Étape 2: Vérification code email
@router.post("/verify-email-code")
async def verify_email_code(email: str, code: str):
    if email not in email_codes or email_codes[email] != code:
        raise HTTPException(status_code=400, detail="Code invalide")
    return {"message": "Email vérifié"}

# Étape 3: Envoi code téléphone (simulé)
@router.post("/send-phone-code")
async def send_phone_code(phone: str):
    code = f"{randint(100000, 999999)}"
    phone_codes[phone] = code
    # Ici tu pourrais envoyer un vrai SMS via Twilio ou autre
    print(f"Code pour {phone} : {code}")
    return {"message": f"Code envoyé au {phone}"}

# Étape 4: Vérification code téléphone
@router.post("/verify-phone-code")
async def verify_phone_code(phone: str, code: str):
    if phone not in phone_codes or phone_codes[phone] != code:
        raise HTTPException(status_code=400, detail="Code invalide")
    return {"message": "Téléphone vérifié"}

# Étape 5: Création utilisateur final
@router.post("/final-register", response_model=UserResponse)
async def final_register(user: UserCreate):
    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    await create_user(db, user)
    return UserResponse(email=user.email, phone=user.phone, name=user.name)
