import hashlib
import logging
import os
import tempfile
from typing import AsyncGenerator

import edge_tts

logger = logging.getLogger(__name__)

# edge-tts accepts rates roughly within +/-100%; the UI slider spans 0.8x - 1.5x.
_MIN_RATE = 0.5
_MAX_RATE = 2.0

# Voice maps for European and Indian regional languages using Microsoft Azure Neural Voices
VOICE_MAP = {
    "de": {
        "female": "de-DE-KatjaNeural",
        "male": "de-DE-KillianNeural"
    },
    "fr": {
        "female": "fr-FR-EloiseNeural",
        "male": "fr-FR-HenriNeural"
    },
    "es": {
        "female": "es-ES-ElviraNeural",
        "male": "es-ES-AlvaroNeural"
    },
    "it": {
        "female": "it-IT-ElsaNeural",
        "male": "it-IT-DiegoNeural"
    },
    "pt": {
        "female": "pt-PT-RaquelNeural",
        "male": "pt-PT-DuarteNeural"
    },
    "ta": {
        "female": "ta-IN-PallaviNeural",
        "male": "ta-IN-ValluvarNeural"
    },
    "te": {
        "female": "te-IN-ShrutiNeural",
        "male": "te-IN-MohanNeural"
    },
    "ml": {
        "female": "ml-IN-SobhanaNeural",
        "male": "ml-IN-MidhunNeural"
    },
    "kn": {
        "female": "kn-IN-SapnaNeural",
        "male": "kn-IN-GaganNeural"
    },
    "mr": {
        "female": "mr-IN-AarohiNeural",
        "male": "mr-IN-ManoharNeural"
    }
}

class TTSService:
    def __init__(self, cache_dir: str = "tts_cache"):
        """
        Initializes the TTS Service with a local cache directory to optimize scaling.
        """
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, text: str, voice: str, rate: str) -> str:
        """
        Generates a unique cache file path based on a hash of text, voice, and rate settings.
        """
        hash_input = f"{text}_{voice}_{rate}".encode("utf-8")
        file_hash = hashlib.md5(hash_input).hexdigest()
        return os.path.join(self.cache_dir, f"{file_hash}.mp3")

    def get_voice(self, language: str, gender: str = "female") -> str:
        """
        Returns the neural voice name for the given language and gender.
        Defaults to English (US) if language is unsupported.
        """
        lang = (language or "").lower()
        gen = (gender or "").lower()
        if gen not in ("male", "female"):
            gen = "female"

        if lang in VOICE_MAP:
            return VOICE_MAP[lang][gen]
        
        # Fallback to general English neural voice if not matched
        return "en-US-AvaNeural" if gen == "female" else "en-US-AndrewNeural"

    async def stream_audio(self, text: str, language: str, gender: str = "female", rate_val: float = 1.0) -> AsyncGenerator[bytes, None]:
        """
        Streams audio bytes. Checks cache first; if missing, synthesizes audio using
        edge-tts, writes to cache, and yields chunks to the caller.
        """
        voice = self.get_voice(language, gender)

        # Convert numeric rate (e.g. 1.0) to edge-tts rate format (e.g. "+0%", "+10%", "-5%")
        rate_val = min(_MAX_RATE, max(_MIN_RATE, float(rate_val)))
        percentage = int(round((rate_val - 1.0) * 100))
        rate_str = f"{'+' if percentage >= 0 else ''}{percentage}%"

        cache_path = self._get_cache_path(text, voice, rate_str)

        # 1. Cache Hit - stream directly from stored file to conserve API calls
        if os.path.exists(cache_path):
            logger.info("TTS cache hit for voice %s at %s", voice, rate_str)
            chunk_size = 4096
            with open(cache_path, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
            return

        # 2. Cache Miss - synthesize, streaming to the client while writing a temp file.
        # The cache entry is only published (atomic rename) once synthesis completes, so an
        # aborted request can never leave a truncated MP3 behind under a valid cache key.
        logger.info("TTS cache miss; synthesizing voice %s at %s", voice, rate_str)
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".part")
        completed = False
        try:
            with os.fdopen(tmp_fd, "wb") as tmp_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        data_bytes = chunk["data"]
                        tmp_file.write(data_bytes)
                        yield data_bytes
            completed = True
        except Exception as e:
            logger.error("edge-tts synthesis failed for voice %s: %s", voice, e)
            raise
        finally:
            if completed:
                try:
                    os.replace(tmp_path, cache_path)
                except OSError as e:
                    logger.warning("Could not publish TTS cache entry: %s", e)
                    self._safe_unlink(tmp_path)
            else:
                self._safe_unlink(tmp_path)

    @staticmethod
    def _safe_unlink(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass
