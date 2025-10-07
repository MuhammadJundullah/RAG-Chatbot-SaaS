from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    DATABASE_URL: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash" 
    VECTOR_DB_PATH: str = "./chroma_db"

    # Authentication settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
