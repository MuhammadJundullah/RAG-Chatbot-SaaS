import io
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from starlette.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db,
    check_quota_and_subscription,
)
from app.models.user_model import Users
from app.modules.speech.schemas import (
    TranscribeResponse,
    TextToSpeechRequest,
    SpeechChatResponse,
)
from app.modules.speech.service import speech_service
from app.utils.activity_logger import log_activity

router = APIRouter()


@router.post("/speech/transcribe", response_model=TranscribeResponse, tags=["Speech"])
async def transcribe_speech(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota_check: None = Depends(check_quota_and_subscription),
):
    """
    Terima audio (voice note) lalu transcribe memakai Whisper lokal.
    """
    result = await speech_service.transcribe_upload(file=audio, language=language)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id if current_user.company else None,
        activity_description=f"User '{current_user.email}' melakukan transkripsi audio.",
    )
    return result


@router.post("/speech/tts", tags=["Speech"])
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota_check: None = Depends(check_quota_and_subscription),
):
    """
    Ubah teks menjadi audio memakai TTS (misal mms/tts-ind via endpoint HF).
    """
    audio_bytes, content_type, metadata = await speech_service.text_to_speech(
        text=request.text,
        voice_id=request.voice_id,
        speed=request.speed,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id if current_user.company else None,
        activity_description=f"User '{current_user.email}' melakukan TTS.",
    )
    headers = {
        "X-Request-ID": metadata.request_id,
    }
    if metadata.voice_id:
        headers["X-Voice-ID"] = metadata.voice_id
    if metadata.speed:
        headers["X-TTS-Speed"] = str(metadata.speed)

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=content_type,
        headers=headers,
    )


@router.post("/chat/speech", tags=["Speech"])
async def chat_from_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    conversation_id: Optional[str] = Form(default=None),
    model: Optional[str] = Form(default=None),
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota_check: None = Depends(check_quota_and_subscription),
):
    """
    End-to-end: terima audio → transcribe → kirim ke chat → (opsional) kembalikan audio jawaban.
    """
    response_payload, audio_bytes, content_type, tts_metadata, metadata = await speech_service.chat_from_audio(
        file=audio,
        language=language,
        conversation_id=conversation_id,
        model=model,
        current_user=current_user,
        db=db,
    )

    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id if current_user.company else None,
        activity_description=(
            f"User '{current_user.email}' mengirim chat via audio pada percakapan {response_payload.conversation_id}."
        ),
    )

    # Selalu kembalikan JSON; sertakan path output audio jika tersedia.
    payload = response_payload.model_dump()
    payload.update(
        {
            "stt_request_id": metadata.get("stt_request_id"),
            "tts_request_id": metadata.get("tts_request_id"),
            "input_duration_ms": metadata.get("input_duration_ms"),
        }
    )
    if metadata.get("output_audio_path"):
        payload["output_audio_path"] = metadata["output_audio_path"]
    return payload
