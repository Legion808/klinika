from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from config import settings
from core.auth import get_current_user, get_current_active_doctor
from database import get_db
from models.user import User, UserRole
from models.appointment import Appointment, AppointmentStatus
from models.consultation import Consultation, Message
from schemas.consultation import (
    Consultation as ConsultationSchema,
    ConsultationCreate,
    ConsultationUpdate,
    MessageCreate,
    Message as MessageSchema
)

router = APIRouter()


@router.post("/start/{appointment_id}", response_model=ConsultationSchema)
def start_consultation(
    appointment_id: UUID,
    consultation_in: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Start a new consultation for an appointment.
    """
    # Get the appointment
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check if user is authorized to start consultation for this appointment
    is_patient = current_user.id == appointment.patient_id
    is_doctor = current_user.id == appointment.doctor_id

    if not (is_patient or is_doctor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Check if appointment is in correct status
    if appointment.status != AppointmentStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start consultation for appointment with status '{appointment.status.value}'",
        )

    # Check if consultation already exists
    existing_consultation = db.query(Consultation).filter(
        Consultation.appointment_id == appointment_id
    ).first()

    if existing_consultation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation already exists for this appointment",
        )

    # Update appointment status
    appointment.status = AppointmentStatus.IN_PROGRESS

    # Create new consultation
    consultation = Consultation(
        appointment_id=appointment_id,
        type=consultation_in.type,
        started_at=datetime.utcnow(),
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return consultation


@router.post("/{consultation_id}/end", response_model=ConsultationSchema)
def end_consultation(
    consultation_id: UUID,
    consultation_in: ConsultationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_doctor),
) -> Any:
    """
    End a consultation and provide notes (doctor only).
    """
    # Get the consultation
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Get the associated appointment
    appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated appointment not found",
        )

    # Check if user is authorized to end this consultation
    if current_user.id != appointment.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned doctor can end the consultation",
        )

    # Check if consultation can be ended
    if consultation.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation has already ended",
        )

    # Update consultation
    consultation.ended_at = datetime.utcnow()
    consultation.notes = consultation_in.notes

    # Update appointment status
    appointment.status = AppointmentStatus.COMPLETED

    db.commit()
    db.refresh(consultation)

    return consultation


@router.get("/me", response_model=List[ConsultationSchema])
def get_my_consultations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user's consultations.
    """
    if current_user.role == UserRole.PATIENT:
        consultations = db.query(Consultation).join(
            Appointment, Consultation.appointment_id == Appointment.id
        ).filter(
            Appointment.patient_id == current_user.id
        ).all()
    elif current_user.role == UserRole.DOCTOR:
        consultations = db.query(Consultation).join(
            Appointment, Consultation.appointment_id == Appointment.id
        ).filter(
            Appointment.doctor_id == current_user.id
        ).all()
    else:  # Admin can see all
        consultations = db.query(Consultation).all()

    return consultations


@router.get("/{consultation_id}", response_model=ConsultationSchema)
def get_consultation(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a consultation by ID.
    """
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Get the associated appointment
    appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated appointment not found",
        )

    # Check if user is authorized to view this consultation
    is_patient = current_user.id == appointment.patient_id
    is_doctor = current_user.id == appointment.doctor_id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_patient or is_doctor or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return consultation


@router.post("/{consultation_id}/message", response_model=MessageSchema)
def create_message(
    consultation_id: UUID,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send a message in a consultation.
    """
    # Get the consultation
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id). personally
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Get the associated appointment
    appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated appointment not found",
        )

    # Check if user is authorized to send message in this consultation
    is_patient = current_user.id == appointment.patient_id
    is_doctor = current_user.id == appointment.doctor_id

    if not (is_patient or is_doctor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Check if consultation is active
    if consultation.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to ended consultation",
        )

    # Create new message
    message = Message(
        consultation_id=consultation_id,
        sender_id=current_user.id,
        message=message_in.message,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("/{consultation_id}/messages", response_model=List[MessageSchema])
def get_consultation_messages(
    consultation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all messages in a consultation.
    """
    # Get the consultation
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Get the associated appointment
    appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated appointment not found",
        )

    # Check if user is authorized to view messages in this consultation
    is_patient = current_user.id == appointment.patient_id
    is_doctor = current_user.id == appointment.doctor_id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_patient or is_doctor or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Get all messages in the consultation
    messages = db.query(Message).filter(
        Message.consultation_id == consultation_id
    ).order_by(Message.timestamp).all()

    return messages