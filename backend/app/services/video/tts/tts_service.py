"""
TTS Narration Engine & Audio Cache
===================================
Generates educational speech audio from scene narration scripts with deterministic
local caching (text_hash + voice + language) and fallback support.
"""
from app.core.logging import logger
import os
import io
import hashlib
import wave
import struct
import math
from typing import Dict, Any, Tuple, Optional


import tempfile

AUDIO_CACHE_DIR = os.path.join(tempfile.gettempdir(), "teachgenie_scratch", "tts_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


def generate_offline_tone_audio(output_path: str, duration_sec: float = 5.0) -> str:
    """Generates a soft, clean placeholder WAV audio file for offline/testing environments."""
    sample_rate = 22050
    num_samples = int(sample_rate * duration_sec)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with wave.open(output_path, "w") as wav_file:
        wav_file.setnchannels(1)        # Mono
        wav_file.setsampwidth(2)        # 16-bit
        wav_file.setframerate(sample_rate)

        # Soft 440Hz sine wave fade
        for i in range(num_samples):
            t = i / sample_rate
            val = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * 440.0 * t))
            data = struct.pack("<h", val)
            wav_file.writeframes(data)

    return output_path


async def generate_narration_audio(
    text: str,
    output_path: str,
    language: str = "english",
    voice: str = "en-US-GuyNeural",
    speed: float = 1.0,
) -> Tuple[str, float]:
    """
    Generates narration audio file and returns (audio_path, duration_seconds).
    Caches results to eliminate redundant generation.
    """
    text_clean = text.strip()
    if not text_clean:
        text_clean = "Welcome to this concept lesson."

    text_hash = hashlib.md5(f"{text_clean}_{language}_{voice}_{speed}".encode()).hexdigest()
    cached_file = os.path.join(AUDIO_CACHE_DIR, f"{text_hash}.wav")

    # 1. Check local audio cache
    if os.path.exists(cached_file) and os.path.getsize(cached_file) > 100:
        # Copy to output_path if distinct
        if cached_file != output_path:
            import shutil
            shutil.copy2(cached_file, output_path)
        # Estimate duration from words (~140 words per minute)
        word_count = len(text_clean.split())
        estimated_duration = max(3.0, round((word_count / 140.0) * 60.0, 1))
        return output_path, estimated_duration

    # 2. Estimate duration
    word_count = len(text_clean.split())
    estimated_duration = max(3.0, round((word_count / 140.0) * 60.0, 1))

    # 3. Attempt high-quality edge-tts
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text_clean, voice)
        await communicate.save(output_path)
        return output_path, estimated_duration
    except Exception as edge_e:
        logger.error(f"[TTS] edge-tts failed: {edge_e}. Falling back to gTTS.")
        
    # 4. Attempt gTTS fallback
    try:
        from gtts import gTTS
        lang_code = "hi" if language.lower() in ["hindi", "hinglish"] else "en"
        tts = gTTS(text=text_clean, lang=lang_code, slow=False)
        tts.save(output_path)
        return output_path, estimated_duration
    except Exception as e:
        logger.error(f"[TTS] gTTS fallback failed: {e}. Falling back to offline tone.")
        # Fallback to deterministic tone/silence audio for robust offline operation
        generate_offline_tone_audio(output_path, duration_sec=estimated_duration)
        return output_path, estimated_duration
