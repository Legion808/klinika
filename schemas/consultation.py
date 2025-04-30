from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from models.consultation import ConsultationType


# Base Consultation Schema
class ConsultationBase(BaseModel):
    type: ConsultationType


# Schema for creating a consultation
class ConsultationCreate(ConsultationBase):
    pass


# Schema for updating a consultation
class ConsultationUpdate(BaseModel):
    notes: Optional[str] = None


# Schema for returning a consultation
class ConsultationInDB(ConsultationBase):
    id: UUID
    appointment_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Schema for consultation output
class Consultation(ConsultationInDB):
    pass


# Message schemas
class MessageBase(BaseModel):
    message: str


# Schema for creating a message
class MessageCreate(MessageBase):
    pass


# Schema for returning a message
class MessageInDB(MessageBase):
    id: UUID
    consultation_id: UUID
    sender_id: UUID
    timestamp: datetime

    class Config:
        orm_mode = True


# Schema for message output
class Message(MessageInDB):
    pass