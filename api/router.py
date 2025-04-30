from fastapi import APIRouter
from api.endpoints import users, appointments, admin
from api.endpoints import auth, consultations

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(consultations.router, prefix="/consultations", tags=["Consultations"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])