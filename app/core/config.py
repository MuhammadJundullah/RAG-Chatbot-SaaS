from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    DATABASE_URL: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    EMBEDDING_MODEL_NAME: str
    PINECONE_API_KEY: str

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

    # Redis settings for Celery
    REDIS_URL: str = "redis://localhost:6379/0"

def get_settings():
    return Settings()

settings = get_settings()
