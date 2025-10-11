from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    DATABASE_URL: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    EMBEDDING_MODEL_NAME: str 
    PINECONE_API_KEY: str

    # Authentication settings
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

def get_settings():
    return Settings()

settings = get_settings()
