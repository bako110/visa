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
