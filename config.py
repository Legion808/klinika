import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


class Settings(BaseSettings):
    PROJECT_NAME: str = "Xususiy Klinika Platformasi"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # JWT Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "82eqieae8928eea")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    # Database settings
    DATABASE_URL = "postgresql://doadmin:AVNS_0TwdierbkVNRnMdhr2-@db-postgresql-syd1-12346-do-user-19185546-0.h.db.ondigitalocean.com:25060/defaultdb?sslmode=require"

    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["*"]

    # WebSocket settings
    WS_MESSAGE_QUEUE: str = "redis://localhost"

    class Config:
        case_sensitive = True


settings = Settings()