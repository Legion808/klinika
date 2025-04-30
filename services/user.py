from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.user import User, Doctor, Patient, UserRole
from core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        """
        return self.db.query(User).filter(User.username == username).first()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user by username and password.
        """
        user = self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user.
        """
        # Check if user with this email or username already exists
        if self.get_by_email(user_data["email"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        if self.get_by_username(user_data["username"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists",
            )

        # Create user with hashed password
        db_user = User(
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data["full_name"],
            password_hash=get_password_hash(user_data["password"]),
            role=user_data["role"],
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def create_doctor(self, user_data: Dict[str, Any], doctor_data: Dict[str, Any]) -> Doctor:
        """
        Create a new doctor with user profile.
        """
        # Create user
        user_data["role"] = UserRole.DOCTOR
        db_user = self.create_user(user_data)

        # Create doctor profile
        db_doctor = Doctor(
            id=db_user.id,
            specialization=doctor_data.get("specialization", "General"),
            bio=doctor_data.get("bio", ""),
            working_hours=doctor_data.get("working_hours", ""),
        )
        self.db.add(db_doctor)
        self.db.commit()
        self.db.refresh(db_doctor)

        return db_doctor

    def create_patient(self, user_data: Dict[str, Any], patient_data: Dict[str, Any]) -> Patient:
        """
        Create a new patient with user profile.
        """
        # Create user
        user_data["role"] = UserRole.PATIENT
        db_user = self.create_user(user_data)

        # Create patient profile
        db_patient = Patient(
            id=db_user.id,
            date_of_birth=patient_data.get("date_of_birth"),
            blood_group=patient_data.get("blood_group"),
            allergies=patient_data.get("allergies"),
        )
        self.db.add(db_patient)
        self.db.commit()
        self.db.refresh(db_patient)

        return db_patient

    def update_user(self, user_id: UUID, user_data: Dict[str, Any]) -> User:
        """
        Update user data.
        """
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Update user fields
        for key, value in user_data.items():
            if hasattr(db_user, key) and value is not None:
                # Handle password separately
                if key == "password":
                    db_user.password_hash = get_password_hash(value)
                else:
                    setattr(db_user, key, value)

        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def get_doctors(self, skip: int = 0, limit: int = 100) -> List[Doctor]:
        """
        Get list of doctors.
        """
        return (
            self.db.query(Doctor)
            .join(User)
            .filter(User.role == UserRole.DOCTOR, User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_doctor_by_id(self, doctor_id: UUID) -> Optional[Doctor]:
        """
        Get doctor by ID.
        """
        return self.db.query(Doctor).filter(Doctor.id == doctor_id).first()

    def update_doctor(self, doctor_id: UUID, doctor_data: Dict[str, Any]) -> Doctor:
        """
        Update doctor data.
        """
        db_doctor = self.get_doctor_by_id(doctor_id)
        if not db_doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        # Update doctor fields
        for key, value in doctor_data.items():
            if hasattr(db_doctor, key) and value is not None:
                setattr(db_doctor, key, value)

        self.db.commit()
        self.db.refresh(db_doctor)

        return db_doctor

    def get_patient_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """
        Get patient by ID.
        """
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def update_patient(self, patient_id: UUID, patient_data: Dict[str, Any]) -> Patient:
        """
        Update patient data.
        """
        db_patient = self.get_patient_by_id(patient_id)
        if not db_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        # Update patient fields
        for key, value in patient_data.items():
            if hasattr(db_patient, key) and value is not None:
                setattr(db_patient, key, value)

        self.db.commit()
        self.db.refresh(db_patient)

        return db_patient