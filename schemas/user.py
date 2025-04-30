from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from models.user import UserRole


# Base User Schema
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str


# Schema for creating a user
class UserCreate(UserBase):
    password: str
    role: UserRole

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


# Schema for updating a user
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# Schema for returning a user
class UserInDB(UserBase):
    id: UUID
    role: UserRole
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        orm_mode = True


# Schema for user output (hiding sensitive info)
class User(UserInDB):
    pass


# Doctor specific schemas
class DoctorBase(BaseModel):
    specialization: str
    bio: Optional[str] = None
    working_hours: Optional[str] = None


class DoctorCreate(DoctorBase):
    user: UserCreate


class DoctorUpdate(DoctorBase):
    pass


class DoctorInDB(DoctorBase):
    id: UUID
    user: User

    class Config:
        orm_mode = True


# Patient specific schemas
class PatientBase(BaseModel):
    date_of_birth: Optional[datetime] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None


class PatientCreate(PatientBase):
    user: UserCreate


class PatientUpdate(PatientBase):
    pass


class PatientInDB(PatientBase):
    id: UUID
    user: User

    class Config:
        orm_mode = True


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str
    exp: int
    role: str