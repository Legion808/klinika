from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from models.user import User, UserRole
from models.appointment import Appointment, AppointmentStatus
from models.consultation import Consultation, Message, ConsultationType


class ConsultationService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, consultation_id: UUID) -> Optional[Consultation]:
        """
        Get consultation by ID.
        """
        return self.db.query(Consultation).filter(Consultation.id == consultation_id).first()

    def get_by_appointment_id(self, appointment_id: UUID) -> Optional[Consultation]:
        """
        Get consultation by appointment ID.
        """
        return self.db.query(Consultation).filter(Consultation.appointment_id == appointment_id).first()

    def start_consultation(
            self, appointment_id: UUID, consultation_type: ConsultationType
    ) -> Consultation:
        """
        Start a new consultation.
        """
        # Get the appointment
        appointment = self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # Check if appointment is in correct status
        if appointment.status != AppointmentStatus.WAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start consultation for appointment with status '{appointment.status.value}'",
            )

        # Check if consultation already exists
        existing_consultation = self.get_by_appointment_id(appointment_id)
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
            type=consultation_type,
            started_at=datetime.utcnow(),
        )
        self.db.add(consultation)
        self.db.commit()
        self.db.refresh(consultation)

        return consultation

    def end_consultation(self, consultation_id: UUID, notes: Optional[str] = None) -> Consultation:
        """
        End a consultation.
        """
        consultation = self.get_by_id(consultation_id)
        if not consultation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation not found",
            )

        # Check if consultation can be ended
        if consultation.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consultation has already ended",
            )

        # Get the associated appointment
        appointment = self.db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated appointment not found",
            )

        # Update consultation
        consultation.ended_at = datetime.utcnow()
        if notes:
            consultation.notes = notes

        # Update appointment status
        appointment.status = AppointmentStatus.COMPLETED

        self.db.commit()
        self.db.refresh(consultation)

        return consultation

    def get_user_consultations(self, user_id: UUID) -> List[Consultation]:
        """
        Get consultations for a user.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.role == UserRole.PATIENT:
            # Get consultations where user is the patient
            consultations = self.db.query(Consultation).join(
                Appointment, Consultation.appointment_id == Appointment.id
            ).filter(
                Appointment.patient_id == user_id
            ).all()
        elif user.role == UserRole.DOCTOR:
            # Get consultations where user is the doctor
            consultations = self.db.query(Consultation).join(
                Appointment, Consultation.appointment_id == Appointment.id
            ).filter(
                Appointment.doctor_id == user_id
            ).all()
        else:  # Admin can see all
            consultations = self.db.query(Consultation).all()

        return consultations

    def add_message(self, consultation_id: UUID, sender_id: UUID, message_text: str) -> Message:
        """
        Add a message to a consultation.
        """
        consultation = self.get_by_id(consultation_id)
        if not consultation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation not found",
            )

        # Check if consultation is active
        if consultation.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send message to ended consultation",
            )

        # Get the associated appointment
        appointment = self.db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated appointment not found",
            )

        # Check if sender is a participant in this consultation
        if sender_id != appointment.patient_id and sender_id != appointment.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant in this consultation",
            )

        # Create new message
        message = Message(
            consultation_id=consultation_id,
            sender_id=sender_id,
            message=message_text,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def get_messages(self, consultation_id: UUID) -> List[Message]:
        """
        Get all messages in a consultation.
        """
        consultation = self.get_by_id(consultation_id)
        if not consultation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation not found",
            )

        # Get all messages in the consultation
        messages = self.db.query(Message).filter(
            Message.consultation_id == consultation_id
        ).order_by(Message.timestamp).all()

        return messages