from typing import Optional
from pydantic import BaseModel, EmailStr

class UserModel(BaseModel):
    email: EmailStr
    phone: str
    name: str
    password: str
