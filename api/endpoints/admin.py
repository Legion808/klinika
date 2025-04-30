from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import statistics

from core.auth import get_current_active_admin
from core.security import get_password_hash
from database import get_db
from models.user import User, Doctor, Patient, UserRole
from models.appointment import Appointment, AppointmentStatus
from models.consultation import Consultation, ConsultationType
from schemas.user import (
    User as UserSchema,
    DoctorCreate, DoctorInDB,
    PatientCreate, PatientInDB
)

router = APIRouter()


@router.get("/stats", response_model=dict)
def get_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    Get system statistics for admin dashboard.
    """
    # Count users by role
    total_users = db.query(User).count()
    total_patients = db.query(User).filter(User.role == UserRole.PATIENT).count()
    total_doctors = db.query(User).filter(User.role == UserRole.DOCTOR).count()

    # Count appointments by status
    waiting_appointments = db.query(Appointment).filter(Appointment.status == AppointmentStatus.WAITING).count()
    completed_appointments = db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count()
    cancelled_appointments = db.query(Appointment).filter(Appointment.status == AppointmentStatus.CANCELLED).count()

    # Count consultations by type
    chat_consultations = db.query(Consultation).filter(Consultation.type == ConsultationType.CHAT).count()
    video_consultations = db.query(Consultation).filter(Consultation.type == ConsultationType.VIDEO).count()

    # Calculate consultation durations
    consultation_durations = []
    completed_consultations = db.query(Consultation).filter(Consultation.ended_at.isnot(None)).all()
    for cons in completed_consultations:
        if cons.started_at and cons.ended_at:
            duration_minutes = (cons.ended_at - cons.started_at).total_seconds() / 60
            consultation_durations.append(duration_minutes)

    avg_consultation_duration = statistics.mean(consultation_durations) if consultation_durations else 0

    return {
        "users": {
            "total": total_users,
            "patients": total_patients,
            "doctors": total_doctors,
            "admins": total_users - total_patients - total_doctors,
        },
        "appointments": {
            "waiting": waiting_appointments,
            "completed": completed_appointments,
            "cancelled": cancelled_appointments,
            "total": waiting_appointments + completed_appointments + cancelled_appointments,
        },
        "consultations": {
            "chat": chat_consultations,
            "video": video_consultations,
            "total": chat_consultations + video_consultations,
            "avg_duration_minutes": round(avg_consultation_duration, 2),
        },
    }


@router.get("/users", response_model=List[UserSchema])
def get_users(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_admin),
        skip: int = 0,
        limit: int = 100,
        role: UserRole = None,
) -> Any:
    """
    Get all users with optional filtering by role.
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/add-doctor", response_model=DoctorInDB)
def create_doctor(
        doctor_in: DoctorCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    Create a new doctor account.
    """
    # Check if user with this email or username already exists
    user_exists = db.query(User).filter(
        (User.email == doctor_in.user.email) | (User.username == doctor_in.user.username)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Create user with doctor role
    user = User(
        email=doctor_in.user.email,
        username=doctor_in.user.username,
        full_name=doctor_in.user.full_name,
        password_hash=get_password_hash(doctor_in.user.password),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create doctor profile
    doctor = Doctor(
        id=user.id,
        specialization=doctor_in.specialization,
        bio=doctor_in.bio,
        working_hours=doctor_in.working_hours,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return {"id": doctor.id, "user": user, **doctor_in.dict()}


@router.post("/add-patient", response_model=PatientInDB)
def create_patient(
        patient_in: PatientCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    Create a new patient account.
    """
    # Check if user with this email or username already exists
    user_exists = db.query(User).filter(
        (User.email == patient_in.user.email) | (User.username == patient_in.user.username)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Create user with patient role
    user = User(
        email=patient_in.user.email,
        username=patient_in.user.username,
        full_name=patient_in.user.full_name,
        password_hash=get_password_hash(patient_in.user.password),
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create patient profile
    patient = Patient(
        id=user.id,
        date_of_birth=patient_in.date_of_birth,
        blood_group=patient_in.blood_group,
        allergies=patient_in.allergies,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return {"id": patient.id, "user": user, **patient_in.dict()}


# @router.delete("/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_user(
#         user_id: UUID,
#         db: Session = Depends(get_db),
#         current_user: User = Depends(get_current_active_admin),
# ) -> Any:
#     """
#     Delete a user.
#     """
#     # Check if user exists
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found",
#         )
#
#     # Don't allow deleting yourself
#     if user.id == current_user.id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot delete your own account",
#         )
#
#     # Instead of hard delete, just deactivate user
#     user.is_active = False
#     db.commit()
#
#     return None