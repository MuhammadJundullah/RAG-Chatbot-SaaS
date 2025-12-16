import subprocess
import tempfile
from typing import Optional, Tuple
import os


class PiperTTSClient:
    """
    Simple local TTS client using Piper CLI.
    Requires piper binary and a model file (.onnx) available locally.
    """

    def __init__(
        self,
        piper_bin: str,
        model_path: str,
        output_format: str = "wav",
        sample_rate: Optional[int] = None,
        use_cuda: bool = False,
    ):
        self.piper_bin = piper_bin
        self.model_path = model_path
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.use_cuda = use_cuda

    @property
    def enabled(self) -> bool:
        return bool(self.piper_bin and self.model_path and os.path.exists(self.model_path))

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Tuple[bytes, str]:
        """
        Runs Piper CLI to synthesize audio. Returns bytes and content_type.
        """
        if not self.enabled:
            raise RuntimeError("Piper TTS is not configured or model file is missing.")

        args = [self.piper_bin, "-m", self.model_path, "--output_format", self.output_format]
        if self.sample_rate:
            args.extend(["--sample_rate", str(self.sample_rate)])
        if speed:
            args.extend(["--length_scale", str(speed)])
        if self.use_cuda:
            args.append("--cuda")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_out:
            out_path = tmp_out.name

        args.extend(["-f", out_path])

        # Piper reads text from stdin
        proc = subprocess.run(args, input=text.encode("utf-8"), capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Piper synthesis failed: {proc.stderr.decode('utf-8', errors='ignore')}")

        content_type = "audio/wav" if self.output_format == "wav" else "audio/mpeg"
        with open(out_path, "rb") as f:
            data = f.read()
        os.remove(out_path)
        return data, content_type

