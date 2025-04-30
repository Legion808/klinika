from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime
import json
import asyncio
from core.auth import get_current_user, get_current_active_patient
from database import get_db
from models.user import User, UserRole
from models.appointment import Appointment, AppointmentStatus
from schemas.appointment import (
    Appointment as AppointmentSchema,
    AppointmentCreate,
    AppointmentUpdate
)
from core.websockets import ConnectionManager

router = APIRouter()
# Connection manager for WebSocket connections
manager = ConnectionManager()


@router.post("/", response_model=AppointmentSchema)
def create_appointment(
        appointment_in: AppointmentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_patient),
) -> Any:
    """
    Create new appointment for current patient.
    """
    # Check if doctor exists
    doctor = db.query(User).filter(
        User.id == appointment_in.doctor_id,
        User.role == UserRole.DOCTOR,
        User.is_active == True
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Check if the doctor already has an appointment at this time
    existing_appointment = db.query(Appointment).filter(
        Appointment.doctor_id == appointment_in.doctor_id,
        Appointment.scheduled_time == appointment_in.scheduled_time,
        Appointment.status.in_([AppointmentStatus.WAITING, AppointmentStatus.IN_PROGRESS])
    ).first()

    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor already has an appointment at this time",
        )

    # Create new appointment
    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=appointment_in.doctor_id,
        scheduled_time=appointment_in.scheduled_time,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Send WebSocket notification to doctor
    asyncio.create_task(
        manager.send_personal_message(
            json.dumps({
                "type": "new_appointment",
                "appointment_id": str(appointment.id),
                "patient_name": current_user.full_name,
                "scheduled_time": appointment.scheduled_time.isoformat(),
            }),
            f"doctor_{appointment.doctor_id}"
        )
    )

    return appointment


@router.get("/me", response_model=List[AppointmentSchema])
def get_my_appointments(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        status: AppointmentStatus = None,
        start_date: datetime = None,
        end_date: datetime = None,
) -> Any:
    """
    Get current user appointments.
    """
    query = db.query(Appointment)

    # Filter by patient or doctor
    if current_user.role == UserRole.PATIENT:
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == UserRole.DOCTOR:
        query = query.filter(Appointment.doctor_id == current_user.id)

    # Apply additional filters if provided
    if status:
        query = query.filter(Appointment.status == status)

    if start_date:
        query = query.filter(Appointment.scheduled_time >= start_date)

    if end_date:
        query = query.filter(Appointment.scheduled_time <= end_date)

    # Sort by scheduled time (newest first)
    query = query.order_by(Appointment.scheduled_time)

    appointments = query.all()
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentSchema)
def get_appointment(
        appointment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get appointment by ID.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check if user is authorized to view this appointment
    if (current_user.role == UserRole.PATIENT and appointment.patient_id != current_user.id) or \
            (
                    current_user.role == UserRole.DOCTOR and appointment.doctor_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return appointment


@router.put("/{appointment_id}", response_model=AppointmentSchema)
def update_appointment(
        appointment_id: UUID,
        appointment_in: AppointmentUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update appointment.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check if user is authorized to update this appointment
    if current_user.role == UserRole.PATIENT and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Patients can only cancel appointments
    if current_user.role == UserRole.PATIENT and \
            (appointment_in.status and appointment_in.status != AppointmentStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients can only cancel appointments",
        )

    # Update appointment attributes that are provided
    for key, value in appointment_in.dict(exclude_unset=True).items():
        setattr(appointment, key, value)

    db.commit()
    db.refresh(appointment)

    # Send WebSocket notification about appointment status change
    if appointment_in.status:
        asyncio.create_task(
            manager.send_personal_message(
                json.dumps({
                    "type": "appointment_status_update",
                    "appointment_id": str(appointment.id),
                    "status": appointment.status.value,
                }),
                f"patient_{appointment.patient_id}"
            )
        )

        asyncio.create_task(
            manager.send_personal_message(
                json.dumps({
                    "type": "appointment_status_update",
                    "appointment_id": str(appointment.id),
                    "status": appointment.status.value,
                }),
                f"doctor_{appointment.doctor_id}"
            )
        )

    return appointment


@router.put("/{appointment_id}/cancel", response_model=AppointmentSchema)
def cancel_appointment(
        appointment_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cancel an appointment.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check if user is authorized to cancel this appointment
    if (current_user.role == UserRole.PATIENT and appointment.patient_id != current_user.id) or \
            (
                    current_user.role == UserRole.DOCTOR and appointment.doctor_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Check if appointment can be cancelled
    if appointment.status not in [AppointmentStatus.WAITING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status '{appointment.status.value}'",
        )

    # Cancel appointment
    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appointment)

    # Send WebSocket notification about appointment cancellation
    asyncio.create_task(
        manager.send_personal_message(
            json.dumps({
                "type": "appointment_cancelled",
                "appointment_id": str(appointment.id),
            }),
            f"patient_{appointment.patient_id}"
        )
    )

    asyncio.create_task(
        manager.send_personal_message(
            json.dumps({
                "type": "appointment_cancelled",
                "appointment_id": str(appointment.id),
            }),
            f"doctor_{appointment.doctor_id}"
        )
    )

    return appointment


@router.websocket("/live/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str,
        db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time appointment updates.
    """
    await manager.connect(websocket, user_id)
    try:
        # Send initial status of waiting appointments
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.role == UserRole.PATIENT:
                appointments = db.query(Appointment).filter(
                    Appointment.patient_id == user_id,
                    Appointment.status.in_([AppointmentStatus.WAITING, AppointmentStatus.IN_PROGRESS])
                ).order_by(Appointment.scheduled_time).all()

                for appointment in appointments:
                    # Calculate position in queue
                    position = db.query(Appointment).filter(
                        Appointment.doctor_id == appointment.doctor_id,
                        Appointment.scheduled_time < appointment.scheduled_time,
                        Appointment.status == AppointmentStatus.WAITING
                    ).count() + 1

                    # Estimate waiting time (15 minutes per appointment in queue)
                    estimated_time = position * 15

                    await manager.send_personal_message(
                        json.dumps({
                            "type": "appointment_update",
                            "appointment_id": str(appointment.id),
                            "status": appointment.status.value,
                            "current_position": position,
                            "estimated_time": estimated_time,
                        }),
                        user_id
                    )
            elif user.role == UserRole.DOCTOR:
                today = datetime.utcnow().date()
                appointments = db.query(Appointment).filter(
                    Appointment.doctor_id == user_id,
                    func.date(Appointment.scheduled_time) == today,
                    Appointment.status.in_([AppointmentStatus.WAITING, AppointmentStatus.IN_PROGRESS])
                ).order_by(Appointment.scheduled_time).all()

                for appointment in appointments:
                    patient = db.query(User).filter(User.id == appointment.patient_id).first()
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "appointment_update",
                            "appointment_id": str(appointment.id),
                            "status": appointment.status.value,
                            "patient_name": patient.full_name if patient else "Unknown",
                            "scheduled_time": appointment.scheduled_time.isoformat(),
                        }),
                        user_id
                    )

        # Keep the connection alive for receiving updates
        while True:
            data = await websocket.receive_text()
            # Process any client messages (if needed)
    except WebSocketDisconnect:
        manager.disconnect(user_id)