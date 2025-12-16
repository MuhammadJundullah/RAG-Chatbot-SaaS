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

    # Speech settings
    SPEECH_WHISPER_MODEL: str = "base"
    SPEECH_WHISPER_DEVICE: Optional[str] = None
    SPEECH_MAX_AUDIO_MB: int = 15
    SPEECH_MAX_AUDIO_DURATION_SEC: int = 60
    SPEECH_STORE_AUDIO_LOCAL: bool = False
    SPEECH_AUDIO_DIR: str = "tmp/audio"

    # TTS settings (e.g., HuggingFace inference for mms/tts-ind)
    TTS_API_BASE_URL: Optional[str] = None
    TTS_API_TOKEN: Optional[str] = None
    TTS_DEFAULT_VOICE_ID: Optional[str] = None
    TTS_DEFAULT_SPEED: Optional[float] = None
    # Local TTS (Piper)
    TTS_PROVIDER: str = "http"  # options: http, piper
    PIPER_BIN: Optional[str] = None
    PIPER_MODEL_PATH: Optional[str] = None
    PIPER_SAMPLE_RATE: Optional[int] = None
    PIPER_OUTPUT_FORMAT: str = "wav"  # wav or mp3
    PIPER_USE_CUDA: bool = False
    # Local TTS (Meta MMS)
    TTS_MMS_MODEL_ID: Optional[str] = None  # e.g., facebook/mms-tts-ind
    TTS_MMS_DEVICE: Optional[str] = None  # e.g., cpu or cuda

def get_settings():
    return Settings()

settings = get_settings()
