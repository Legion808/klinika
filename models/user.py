import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum as PyEnum
from database import Base


class UserRole(str, PyEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctor_appointments = relationship("Appointment", foreign_keys="Appointment.doctor_id", back_populates="doctor")
    patient_appointments = relationship("Appointment", foreign_keys="Appointment.patient_id", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    specialization = Column(String, nullable=False)
    bio = Column(String)
    working_hours = Column(String)  # JSON encoded string of working hours

    # User relationship
    user = relationship("User", primaryjoin="Doctor.id == User.id")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    date_of_birth = Column(DateTime, nullable=True)
    blood_group = Column(String, nullable=True)
    allergies = Column(String, nullable=True)

    # User relationship
    user = relationship("User", primaryjoin="Patient.id == User.id")