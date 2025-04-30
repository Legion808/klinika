from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.auth import (
    get_current_user
)
from models.user import User


def get_user_from_path(
        user_id: str,
        db: Session = Depends(get_db)
) -> User:
    """
    Get a user by ID from the path parameter.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def check_user_permission(
        user: User = Depends(get_user_from_path),
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if the current user has permission to access the user's data.
    """
    # Admin can access any user
    if current_user.role == "admin":
        return user

    # Users can access their own data
    if current_user.id == user.id:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions",
    )