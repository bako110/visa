from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.user import UserCreate
from passlib.hash import bcrypt

async def create_user(db: AsyncIOMotorDatabase, user: UserCreate):
    hashed_password = bcrypt.hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    result = await db.users.insert_one(user_dict)
    return result.inserted_id

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str):
    user = await db.users.find_one({"email": email})
    return user
