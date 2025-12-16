from typing import Optional, Tuple
import httpx


class TTSClient:
    """
    Simple client to call a TTS endpoint (e.g., HuggingFace inference for mms/tts-ind).
    """

    def __init__(
        self,
        base_url: Optional[str],
        api_token: Optional[str],
        default_voice_id: Optional[str] = None,
        default_speed: Optional[float] = None,
        timeout_seconds: float = 60.0,
    ):
        self.base_url = base_url
        self.api_token = api_token
        self.default_voice_id = default_voice_id
        self.default_speed = default_speed
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> dict:
        headers = {"Accept": "*/*"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Tuple[bytes, str]:
        """
        Calls the configured TTS endpoint and returns (audio_bytes, content_type).
        """
        if not self.base_url:
            raise RuntimeError("TTS base URL is not configured.")

        payload = {"inputs": text}
        # Some providers support additional params; we keep them optional.
        parameters = {}
        if voice_id or self.default_voice_id:
            parameters["voice_id"] = voice_id or self.default_voice_id
        if speed or self.default_speed:
            parameters["speed"] = speed or self.default_speed
        if parameters:
            payload["parameters"] = parameters

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.base_url, headers=self._headers(), json=payload)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg")
            return response.content, content_type

