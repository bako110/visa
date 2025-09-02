from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.user import UserCreate
from passlib.context import CryptContext
from bson import ObjectId
from typing import Optional, Dict, Any
from datetime import datetime
import pymongo

# Configuration du contexte de hachage
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(db: AsyncIOMotorDatabase, user: UserCreate) -> pymongo.results.InsertOneResult:
    """
    Créer un nouvel utilisateur avec mot de passe haché et timestamps.
    
    Args:
        db: Base de données MongoDB
        user: Données utilisateur à créer
        
    Returns:
        InsertOneResult: Résultat de l'insertion
        
    Raises:
        Exception: Si l'insertion échoue
    """
    try:
        # Hacher le mot de passe
        hashed_password = pwd_context.hash(user.password)
        
        # Préparer les données utilisateur
        user_dict = user.dict(exclude_unset=True)  # Exclut les valeurs non définies
        user_dict.update({
            "password": hashed_password,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "is_verified": True,  # Puisque l'email et le téléphone sont déjà vérifiés
            "pin_hash": None,  # Sera défini plus tard si nécessaire
            "device_id": None,
            "last_login": None
        })
        
        # Insérer l'utilisateur
        result = await db.users.insert_one(user_dict)
        return result
        
    except Exception as e:
        raise Exception(f"Erreur lors de la création de l'utilisateur: {str(e)}")

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[Dict[str, Any]]:
    """
    Récupérer un utilisateur par son adresse email.
    
    Args:
        db: Base de données MongoDB
        email: Adresse email de l'utilisateur
        
    Returns:
        Dict ou None: Données utilisateur ou None si non trouvé
    """
    try:
        user = await db.users.find_one({"email": email.lower()})  # Email en minuscules
        return user
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération par email: {str(e)}")

async def get_user_by_phone(db: AsyncIOMotorDatabase, phone: str) -> Optional[Dict[str, Any]]:
    """
    Récupérer un utilisateur par son numéro de téléphone.
    
    Args:
        db: Base de données MongoDB
        phone: Numéro de téléphone de l'utilisateur
        
    Returns:
        Dict ou None: Données utilisateur ou None si non trouvé
    """
    try:
        user = await db.users.find_one({"phone": phone})
        return user
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération par téléphone: {str(e)}")

async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupérer un utilisateur par son ID.
    
    Args:
        db: Base de données MongoDB
        user_id: ID de l'utilisateur (string)
        
    Returns:
        Dict ou None: Données utilisateur ou None si non trouvé
    """
    try:
        # Valider l'ObjectId
        if not ObjectId.is_valid(user_id):
            return None
            
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération par ID: {str(e)}")

async def update_user(db: AsyncIOMotorDatabase, user_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Mettre à jour un utilisateur.
    
    Args:
        db: Base de données MongoDB
        user_id: ID de l'utilisateur
        update_data: Données à mettre à jour
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        if not ObjectId.is_valid(user_id):
            return False
            
        # Ajouter timestamp de mise à jour
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        raise Exception(f"Erreur lors de la mise à jour: {str(e)}")

async def delete_user(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """
    Supprimer un utilisateur (soft delete - marquer comme inactif).
    
    Args:
        db: Base de données MongoDB
        user_id: ID de l'utilisateur
        
    Returns:
        bool: True si la suppression a réussi, False sinon
    """
    try:
        if not ObjectId.is_valid(user_id):
            return False
            
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "is_active": False,
                "deleted_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        
        return result.modified_count > 0
    except Exception as e:
        raise Exception(f"Erreur lors de la suppression: {str(e)}")

async def verify_password(hashed_password: str, plain_password: str) -> bool:
    """
    Vérifier un mot de passe contre son hash.
    
    Args:
        hashed_password: Mot de passe haché
        plain_password: Mot de passe en clair
        
    Returns:
        bool: True si le mot de passe correspond, False sinon
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

async def update_last_login(db: AsyncIOMotorDatabase, user_id: str, device_id: Optional[str] = None) -> bool:
    """
    Mettre à jour la dernière connexion de l'utilisateur.
    
    Args:
        db: Base de données MongoDB
        user_id: ID de l'utilisateur
        device_id: ID du dispositif (optionnel)
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        if not ObjectId.is_valid(user_id):
            return False
            
        update_data = {
            "last_login": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if device_id:
            update_data["device_id"] = device_id
            
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        raise Exception(f"Erreur lors de la mise à jour de la connexion: {str(e)}")

async def check_email_exists(db: AsyncIOMotorDatabase, email: str, exclude_user_id: Optional[str] = None) -> bool:
    """
    Vérifier si un email existe déjà (utile pour les mises à jour).
    
    Args:
        db: Base de données MongoDB
        email: Email à vérifier
        exclude_user_id: ID utilisateur à exclure de la vérification
        
    Returns:
        bool: True si l'email existe déjà, False sinon
    """
    try:
        query = {"email": email.lower()}
        
        if exclude_user_id and ObjectId.is_valid(exclude_user_id):
            query["_id"] = {"$ne": ObjectId(exclude_user_id)}
            
        user = await db.users.find_one(query)
        return user is not None
    except Exception as e:
        raise Exception(f"Erreur lors de la vérification d'email: {str(e)}")

async def check_phone_exists(db: AsyncIOMotorDatabase, phone: str, exclude_user_id: Optional[str] = None) -> bool:
    """
    Vérifier si un téléphone existe déjà.
    
    Args:
        db: Base de données MongoDB
        phone: Numéro de téléphone à vérifier
        exclude_user_id: ID utilisateur à exclure de la vérification
        
    Returns:
        bool: True si le téléphone existe déjà, False sinon
    """
    try:
        query = {"phone": phone}
        
        if exclude_user_id and ObjectId.is_valid(exclude_user_id):
            query["_id"] = {"$ne": ObjectId(exclude_user_id)}
            
        user = await db.users.find_one(query)
        return user is not None
    except Exception as e:
        raise Exception(f"Erreur lors de la vérification de téléphone: {str(e)}")

# Index recommandés pour optimiser les performances
async def create_indexes(db: AsyncIOMotorDatabase):
    """
    Créer les index nécessaires pour la collection users.
    """
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("phone", unique=True)
        await db.users.create_index("device_id")
        await db.users.create_index("is_active")
        await db.users.create_index("created_at")
    except Exception as e:
        print(f"Erreur lors de la création des index: {str(e)}")