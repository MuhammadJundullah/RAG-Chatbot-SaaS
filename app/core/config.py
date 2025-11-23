from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    TOGETHER_API_KEY: str
    TOGETHER_MODEL: str
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None
    EMBEDDING_MODEL_NAME: str
    PINECONE_API_KEY: str

    # iPaymu Payment Gateway settings
    IPAYMU_VA: str
    IPAYMU_API_KEY: str

    SUPERADMIN_USERNAME: str = "superadmin"
    SUPERADMIN_EMAIL: str = "superadmin@example.com"
    SUPERADMIN_PASSWORD: str = "superadmin"
    
    # Authentication settings
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # S3 Object Storage settings
    S3_REGION_NAME: str
    S3_ENDPOINT_URL: str
    S3_AWS_ACCESS_KEY_ID: str
    S3_AWS_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    PUBLIC_S3_BASE_URL: str = "https://1xg7ah.leapcellobj.com"

    # Brevo (SendGrid) settings
    BREVO_API_KEY: str 
    DEFAULT_SENDER_EMAIL: str
    BREVO_SMS_SENDER: str = "InfoSMS"

    # Application base URL for links
    APP_BASE_URL: str = "https://127.0.0.1:8000"
    APP_NAME: str

    # Redis settings for Celery
    REDIS_URL: str = "redis://localhost:6379/0"

def get_settings():
    return Settings()

settings = get_settings()
