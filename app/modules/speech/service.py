import os
import uuid
from typing import Optional, Tuple

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.models.user_model import Users
from app.modules.chat.service import chat_service
from app.schemas import chat_schema
from app.modules.speech.schemas import (
    TranscribeResponse,
    SpeechChatResponse,
    TextToSpeechMetadata,
)
from app.modules.speech.providers.whisper_local import WhisperLocalClient
from app.modules.speech.providers.tts_client import TTSClient
from app.modules.speech.providers.piper_tts import PiperTTSClient
from app.modules.speech.providers.mms_tts_local import MMSLocalTTSClient
from app.repository.chatlog_repository import chatlog_repository


class SpeechService:
    """
    Orchestrates STT (Whisper) and TTS flows while reusing the existing chat pipeline.
    """

    ALLOWED_CONTENT_TYPES = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/webm",
        "audio/mp4",
        "video/mp4",
    }

    def __init__(
        self,
        stt_client: WhisperLocalClient,
        tts_client: Optional[object] = None,
        max_audio_mb: int = 15,
        store_audio_local: bool = False,
        audio_dir: str = "tmp/audio",
    ):
        self.stt_client = stt_client
        self.tts_client = tts_client
        self.max_audio_mb = max_audio_mb
        self.store_audio_local = store_audio_local
        self.audio_dir = audio_dir

    async def _read_and_validate_upload(self, file: UploadFile) -> bytes:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File audio kosong.",
            )

        if file.content_type and file.content_type.lower() not in self.ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipe konten tidak didukung: {file.content_type}.",
            )

        max_bytes = self.max_audio_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Ukuran file melebihi batas {self.max_audio_mb} MB.",
            )
        return content

    def _maybe_store_audio(
        self,
        audio_bytes: bytes,
        prefix: str,
        original_filename: Optional[str],
        force: bool = False,
    ) -> Optional[str]:
        """
        Store audio locally if configured. Returns the stored path or None.
        """
        if not (self.store_audio_local or force):
            return None

        os.makedirs(self.audio_dir, exist_ok=True)
        ext = ".wav"
        if original_filename and "." in original_filename:
            ext = f".{original_filename.split('.')[-1]}"
        filename = f"{prefix}_{uuid.uuid4()}{ext}"
        path = os.path.join(self.audio_dir, filename)
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return path

    async def transcribe_upload(
        self,
        file: UploadFile,
        language: Optional[str],
        force_store: bool = False,
    ) -> TranscribeResponse:
        audio_bytes = await self._read_and_validate_upload(file)
        request_id = str(uuid.uuid4())
        stored_input_path = self._maybe_store_audio(
            audio_bytes,
            prefix="input",
            original_filename=file.filename,
            force=force_store,
        )

        try:
            result = await run_in_threadpool(
                self.stt_client.transcribe_bytes,
                audio_bytes,
                language,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal memproses audio dengan Whisper: {exc}",
            )

        text = result.get("text") or ""
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transkripsi kosong; pastikan audio berisi suara yang jelas.",
            )

        return TranscribeResponse(
            text=text.strip(),
            duration_ms=result.get("duration_ms"),
            language_detected=result.get("language_detected"),
            request_id=request_id,
            input_audio_path=stored_input_path,
        )

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Tuple[bytes, str, TextToSpeechMetadata]:
        if not self.tts_client or not getattr(self.tts_client, "enabled", False):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TTS belum dikonfigurasi.",
            )
        request_id = str(uuid.uuid4())
        try:
            audio_bytes, content_type = await self.tts_client.synthesize(text=text, voice_id=voice_id, speed=speed)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal memproses TTS: {exc}",
            )

        metadata = TextToSpeechMetadata(
            request_id=request_id,
            voice_id=voice_id or getattr(self.tts_client, "default_voice_id", None),
            speed=speed or getattr(self.tts_client, "default_speed", None),
        )
        return audio_bytes, content_type, metadata

    async def chat_from_audio(
        self,
        file: UploadFile,
        language: Optional[str],
        conversation_id: Optional[str],
        model: Optional[str],
        current_user: Users,
        db: AsyncSession,
    ):
        transcription = await self.transcribe_upload(file=file, language=language, force_store=True)
        stored_input_path = transcription.input_audio_path
        stored_output_path = None
        tts_metadata = None

        chat_request = chat_schema.ChatRequest(
            message=transcription.text,
            conversation_id=conversation_id,
            model=model,
        )
        chat_result = await chat_service.process_chat_message(
            db=db,
            current_user=current_user,
            request=chat_request,
            chatlog_extra={
                "input_type": "audio",
                "input_audio_path": stored_input_path,
                "output_audio_path": stored_output_path,
                "stt_request_id": transcription.request_id,
                "tts_request_id": tts_metadata.request_id if tts_metadata else None,
                "input_duration_ms": transcription.duration_ms,
            },
        )

        text_response = (chat_result.get("response") or "").strip()
        audio_bytes = None
        content_type = None
        chatlog_id = chat_result.get("chatlog_id")
        if self.tts_client and self.tts_client.enabled and text_response:
            audio_bytes, content_type, tts_metadata = await self.text_to_speech(
                text=text_response,
                voice_id=None,
                speed=None,
            )
            stored_output_path = self._maybe_store_audio(
                audio_bytes,
                prefix="output",
                original_filename="tts.mp3",
                force=True,  # always store output to expose path in response
            )
            if chatlog_id:
                await chatlog_repository.update_audio_fields(
                    db=db,
                    chatlog_id=chatlog_id,
                    output_audio_path=stored_output_path,
                    tts_request_id=tts_metadata.request_id if tts_metadata else None,
                )

        speech_chat_response = SpeechChatResponse(
            conversation_id=chat_result["conversation_id"],
            text=text_response,
            request_id=transcription.request_id,
            input_audio_path=stored_input_path,
            output_audio_path=stored_output_path,
        )

        metadata = {
            "input_audio_path": stored_input_path,
            "output_audio_path": stored_output_path,
            "stt_request_id": transcription.request_id,
            "tts_request_id": tts_metadata.request_id if tts_metadata else None,
            "input_duration_ms": transcription.duration_ms,
        }

        if chatlog_id:
            await chatlog_repository.update_audio_fields(
                db=db,
                chatlog_id=chatlog_id,
                input_audio_path=stored_input_path,
                stt_request_id=transcription.request_id,
                input_duration_ms=transcription.duration_ms,
            )

        return speech_chat_response, audio_bytes, content_type, tts_metadata, metadata


tts_provider = getattr(settings, "TTS_PROVIDER", "http")


speech_service = SpeechService(
    stt_client=WhisperLocalClient(
        model_name=getattr(settings, "SPEECH_WHISPER_MODEL", "base"),
        device=getattr(settings, "SPEECH_WHISPER_DEVICE", None),
    ),
    tts_client=(
        PiperTTSClient(
            piper_bin=getattr(settings, "PIPER_BIN", None),
            model_path=getattr(settings, "PIPER_MODEL_PATH", ""),
            output_format=getattr(settings, "PIPER_OUTPUT_FORMAT", "wav"),
            sample_rate=getattr(settings, "PIPER_SAMPLE_RATE", None),
            use_cuda=getattr(settings, "PIPER_USE_CUDA", False),
        )
        if tts_provider == "piper"
        else MMSLocalTTSClient(
            model_id=getattr(settings, "TTS_MMS_MODEL_ID", None),
            device=getattr(settings, "TTS_MMS_DEVICE", None),
        )
        if tts_provider == "mms_local"
        else TTSClient(
            base_url=getattr(settings, "TTS_API_BASE_URL", None),
            api_token=getattr(settings, "TTS_API_TOKEN", None),
            default_voice_id=getattr(settings, "TTS_DEFAULT_VOICE_ID", None),
            default_speed=getattr(settings, "TTS_DEFAULT_SPEED", None),
        )
    ),
    max_audio_mb=getattr(settings, "SPEECH_MAX_AUDIO_MB", 15),
    store_audio_local=getattr(settings, "SPEECH_STORE_AUDIO_LOCAL", False),
    audio_dir=getattr(settings, "SPEECH_AUDIO_DIR", "tmp/audio"),
)
