import os
import hashlib
import asyncio
import edge_tts
from typing import AsyncGenerator

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
        lang = language.lower()
        gen = gender.lower() if gender in ["male", "female"] else "female"
        
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
        percentage = int((rate_val - 1.0) * 100)
        rate_str = f"{'+' if percentage >= 0 else ''}{percentage}%"

        cache_path = self._get_cache_path(text, voice, rate_str)

        # 1. Cache Hit - stream directly from stored file to conserve API calls
        if os.path.exists(cache_path):
            print(f"TTS Cache HIT: {cache_path}")
            chunk_size = 4096
            with open(cache_path, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
            return

        # 2. Cache Miss - stream from edge-tts and save output asynchronously
        print(f"TTS Cache MISS. Synthesizing voice: {voice}, rate: {rate_str}")
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            
            # We want to save to the cache file while streaming
            # Open the cache file for writing bytes
            cache_file = open(cache_path, "wb")
            
            try:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        data_bytes = chunk["data"]
                        cache_file.write(data_bytes)
                        yield data_bytes
            finally:
                cache_file.close()
                
        except Exception as e:
            # Clean up partial files if synthesis fails
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except:
                    pass
            print(f"Error during edge-tts stream: {str(e)}")
            # Raise exception so routes can return an appropriate HTTP status
            raise e
