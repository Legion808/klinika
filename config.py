import os
from decouple import config
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


    # Ma'lumotlar Bazasi Konfiguratsiyasi
    raw_db_url = config('DATABASE_URL')

    # Handle the case where DATABASE_URL might be a template string like ${db.DATABASE_URL}
    if raw_db_url.startswith('${') and raw_db_url.endswith('}'):
        # If in Digital Ocean, use the default PostgreSQL connection string
        DATABASE_URL = "your_database_url"

    else:
        DATABASE_URL = raw_db_url

"

    class Config:
        case_sensitive = True


settings = Settings()
