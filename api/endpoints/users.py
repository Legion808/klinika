from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import get_current_user, get_current_active_admin, get_current_active_doctor
from database import get_db
from models.user import User, Doctor, Patient, UserRole
from schemas.user import (
    User as UserSchema,
    UserUpdate,
    DoctorInDB,
    PatientInDB,
    DoctorUpdate,
    PatientUpdate
)

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_user_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_user_me(
        user_in: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user information.
    """
    # Update user attributes that are provided
    for key, value in user_in.dict(exclude_unset=True).items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/doctors", response_model=List[DoctorInDB])
def get_doctors(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> Any:
    """
    Get list of all doctors.
    """
    # Get all users with doctor role
    doctors = (
        db.query(Doctor)
        .join(User)
        .filter(User.role == UserRole.DOCTOR, User.is_active == True)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return doctors


@router.get("/doctor/{doctor_id}", response_model=DoctorInDB)
def get_doctor(
        doctor_id: str,
        db: Session = Depends(get_db),
) -> Any:
    """
    Get doctor by ID.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    return doctor


@router.put("/doctor/me", response_model=DoctorInDB)
def update_doctor_me(
        doctor_in: DoctorUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_doctor),
) -> Any:
    """
    Update current doctor information.
    """
    doctor = db.query(Doctor).filter(Doctor.id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    # Update doctor attributes that are provided
    for key, value in doctor_in.dict(exclude_unset=True).items():
        setattr(doctor, key, value)

    db.commit()
    db.refresh(doctor)
    return doctor


@router.put("/patient/me", response_model=PatientInDB)
def update_patient_me(
        patient_in: PatientUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current patient information.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    patient = db.query(Patient).filter(Patient.id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )

    # Update patient attributes that are provided
    for key, value in patient_in.dict(exclude_unset=True).items():
        setattr(patient, key, value)

    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{user_id}", response_model=UserSchema)
def get_user_by_id(
        user_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_admin),
) -> Any:
    """
    Get user by ID. Admin only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user