from pydantic import BaseModel, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from models.appointment import AppointmentStatus


# Base Appointment Schema
class AppointmentBase(BaseModel):
    doctor_id: UUID
    scheduled_time: datetime


# Schema for creating an appointment
class AppointmentCreate(AppointmentBase):
    @validator('scheduled_time')
    def scheduled_time_must_be_future(cls, v):
        if v < datetime.utcnow():
            raise ValueError('Scheduled time must be in the future')
        return v


# Schema for updating an appointment
class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    scheduled_time: Optional[datetime] = None


# Schema for returning an appointment
class AppointmentInDB(AppointmentBase):
    id: UUID
    patient_id: UUID
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Schema for appointment output
class Appointment(AppointmentInDB):
    pass


# Schema for WebSocket appointment updates
class AppointmentWebSocketUpdate(BaseModel):
    appointment_id: UUID
    status: AppointmentStatus
    current_position: Optional[int] = None
    estimated_time: Optional[int] = None  # in minutes