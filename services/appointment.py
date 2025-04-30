from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from models.user import User, UserRole
from models.appointment import Appointment, AppointmentStatus


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: UUID) -> Optional[Appointment]:
        """
        Get appointment by ID.
        """
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()

    def check_doctor_availability(self, doctor_id: UUID, scheduled_time: datetime) -> bool:
        """
        Check if doctor is available at the specified time.
        """
        # Define a time window (e.g., 30 minutes before and after)
        time_window = timedelta(minutes=30)
        start_time = scheduled_time - time_window
        end_time = scheduled_time + time_window

        # Check for existing appointments in the time window
        existing_appointment = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_time.between(start_time, end_time),
            Appointment.status.in_([AppointmentStatus.WAITING, AppointmentStatus.IN_PROGRESS])
        ).first()

        return existing_appointment is None

    def create_appointment(
            self, patient_id: UUID, doctor_id: UUID, scheduled_time: datetime
    ) -> Appointment:
        """
        Create a new appointment.
        """
        # Check if doctor exists
        doctor = self.db.query(User).filter(
            User.id == doctor_id,
            User.role == UserRole.DOCTOR,
            User.is_active == True
        ).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        # Check if doctor is available
        if not self.check_doctor_availability(doctor_id, scheduled_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor is not available at this time",
            )

        # Create new appointment
        db_appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_time=scheduled_time,
        )
        self.db.add(db_appointment)
        self.db.commit()
        self.db.refresh(db_appointment)

        return db_appointment

    def update_appointment(self, appointment_id: UUID, data: Dict[str, Any]) -> Appointment:
        """
        Update an appointment.
        """
        db_appointment = self.get_by_id(appointment_id)
        if not db_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # If updating scheduled time, check doctor availability
        if "scheduled_time" in data and data["scheduled_time"] != db_appointment.scheduled_time:
            if not self.check_doctor_availability(db_appointment.doctor_id, data["scheduled_time"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Doctor is not available at this time",
                )

        # Update fields
        for key, value in data.items():
            if hasattr(db_appointment, key) and value is not None:
                setattr(db_appointment, key, value)

        self.db.commit()
        self.db.refresh(db_appointment)

        return db_appointment

    def cancel_appointment(self, appointment_id: UUID) -> Appointment:
        """
        Cancel an appointment.
        """
        db_appointment = self.get_by_id(appointment_id)
        if not db_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # Check if appointment can be cancelled
        if db_appointment.status not in [AppointmentStatus.WAITING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel appointment with status '{db_appointment.status.value}'",
            )

        # Update status
        db_appointment.status = AppointmentStatus.CANCELLED
        self.db.commit()
        self.db.refresh(db_appointment)

        return db_appointment

    def get_user_appointments(
            self, user_id: UUID, status: Optional[AppointmentStatus] = None,
            start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Appointment]:
        """
        Get appointments for a user.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        query = self.db.query(Appointment)

        # Filter by user role
        if user.role == UserRole.PATIENT:
            query = query.filter(Appointment.patient_id == user_id)
        elif user.role == UserRole.DOCTOR:
            query = query.filter(Appointment.doctor_id == user_id)

        # Apply additional filters
        if status:
            query = query.filter(Appointment.status == status)

        if start_date:
            query = query.filter(Appointment.scheduled_time >= start_date)

        if end_date:
            query = query.filter(Appointment.scheduled_time <= end_date)

        # Sort by scheduled time
        query = query.order_by(Appointment.scheduled_time)

        return query.all()

    def get_queue_position(self, appointment_id: UUID) -> int:
        """
        Get the position of an appointment in the queue.
        """
        db_appointment = self.get_by_id(appointment_id)
        if not db_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # Count appointments scheduled before this one for the same doctor with WAITING status
        position = self.db.query(func.count(Appointment.id)).filter(
            Appointment.doctor_id == db_appointment.doctor_id,
            Appointment.scheduled_time < db_appointment.scheduled_time,
            Appointment.status == AppointmentStatus.WAITING
        ).scalar()

        # Add 1 to get the position (1-based index)
        return position + 1

    def get_estimated_wait_time(self, appointment_id: UUID) -> int:
        """
        Get the estimated wait time in minutes for an appointment.
        """
        position = self.get_queue_position(appointment_id)
        # Assume each appointment takes 15 minutes
        return position * 15