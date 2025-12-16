import os
import tempfile
from typing import Optional


class WhisperLocalClient:
    """
    Thin wrapper around the open-source Whisper model for local inference.
    """

    def __init__(self, model_name: str = "base", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                import whisper  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "whisper package is required for local speech-to-text. "
                    "Install via `pip install openai-whisper`."
                ) from exc

            if self.device:
                self._model = whisper.load_model(self.model_name, device=self.device)
            else:
                self._model = whisper.load_model(self.model_name)

    def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> dict:
        """
        Run transcription on raw audio bytes. Returns dict with text, language, duration_ms.
        """
        self._ensure_model()
        tmp_path = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            tmp_path = tmp_file.name
            tmp_file.close()

            result = self._model.transcribe(tmp_path, language=language)
            text = (result.get("text") or "").strip()
            language_detected = result.get("language")
            duration_ms = None
            segments = result.get("segments") or []
            if segments:
                end_time = segments[-1].get("end")
                if end_time is not None:
                    duration_ms = int(end_time * 1000)

            return {
                "text": text,
                "language_detected": language_detected,
                "duration_ms": duration_ms,
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    # If cleanup fails, we don't want to mask the main error.
                    pass

