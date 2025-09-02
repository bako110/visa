from typing import Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    name: str
    password: str

class UserResponse(BaseModel):
    email: EmailStr
    phone: str
    name: str

# --- Schéma pour login ---
class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    device_id: Optional[str] = None
