from typing import Optional
from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    text: str
    duration_ms: Optional[int] = None
    language_detected: Optional[str] = None
    request_id: str
    input_audio_path: Optional[str] = None


class TextToSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice_id: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    session_id: Optional[str] = None


class TextToSpeechMetadata(BaseModel):
    request_id: str
    voice_id: Optional[str] = None
    speed: Optional[float] = None


class SpeechChatResponse(BaseModel):
    conversation_id: str
    text: str
    request_id: str
    input_audio_path: Optional[str] = None
    output_audio_path: Optional[str] = None
