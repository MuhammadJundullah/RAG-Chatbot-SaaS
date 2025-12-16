import io
import wave
from typing import Optional, Tuple

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel


class MMSLocalTTSClient:
    """
    Local TTS client using Meta MMS models (e.g., facebook/mms-tts-ind) via Transformers.
    Downloads the model/tokenizer once, then runs inference on CPU/GPU.
    """

    def __init__(self, model_id: Optional[str] = None, device: Optional[str] = None):
        self.model_id = model_id
        self.device = device
        self._tokenizer = None
        self._model = None
        self._device = None

    @property
    def enabled(self) -> bool:
        return bool(self.model_id)

    def _ensure_model(self):
        if not self.enabled:
            raise RuntimeError("MMS TTS model_id is not configured.")
        if self._model is not None and self._tokenizer is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = VitsModel.from_pretrained(self.model_id)
        target_device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = self._model.to(target_device)
        self._device = target_device

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Tuple[bytes, str]:
        """
        Generate speech audio (wav bytes). voice_id/speed are ignored for MMS.
        """
        if not text or not text.strip():
            raise ValueError("Teks untuk TTS kosong setelah diproses.")

        self._ensure_model()
        normalized_text = text.strip()
        inputs = self._tokenizer(normalized_text, return_tensors="pt")
        input_ids = inputs.get("input_ids")
        # Guard: tokenizer can return empty tensors for unsupported text → model crashes.
        if input_ids is None or input_ids.numel() == 0 or input_ids.shape[-1] == 0:
            raise ValueError("Tokenisasi MMS TTS menghasilkan input kosong; pastikan teks berisi karakter yang didukung.")
        # Some tokenizers may return float tensors; VITS expects integer token ids.
        inputs["input_ids"] = input_ids.long()
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self._model(**inputs)
            audio = outputs.waveform.squeeze(0).cpu().numpy()

        # Normalize and convert to 16-bit PCM WAV
        audio = np.clip(audio, -1.0, 1.0)
        pcm16 = (audio * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(getattr(self._model.config, "sampling_rate", 16000))
            wav_file.writeframes(pcm16.tobytes())
        return buf.getvalue(), "audio/wav"
