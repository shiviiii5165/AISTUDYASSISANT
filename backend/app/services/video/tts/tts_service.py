"""
Pluggable TTS Narration Engine & Audio Cache
============================================
Cascade Order (Decision #4):
1. Edge-TTS (high-clarity natural neural speech)
2. Kokoro Local (if available)
3. Piper Local (if available)
4. gTTS (emergency network fallback)

Never produces artificial sine/tone audio for learner-facing lessons.
Includes deterministic caching by content hash + voice + speed.
"""
from app.core.logging import logger
import os
import io
import hashlib
import wave
import shutil
import subprocess
import tempfile
from typing import Dict, Any, Tuple, Optional
from ..compositor.compositor import get_ffmpeg_binary
from ..localization.language_engine import LanguageTeachingEngine

AUDIO_CACHE_DIR = os.path.join(tempfile.gettempdir(), "teachgenie_scratch", "tts_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


def get_recommended_voice(language: str) -> str:
    lang = language.lower()
    if lang in ("hinglish", "hindi"):
        return "hi-IN-MadhurNeural"
    return "en-US-ChristopherNeural"


def probe_audio_duration(audio_path: str) -> float:
    """Accurately measures duration of an audio file using wave or ffmpeg."""
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        return 5.0

    # 1. Try wave if WAV
    if audio_path.lower().endswith(".wav"):
        try:
            with wave.open(audio_path, "r") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return max(1.0, round(frames / float(rate), 2))
        except Exception:
            pass

    # 2. Try ffmpeg probe
    ffmpeg_bin = get_ffmpeg_binary()
    try:
        cmd = [
            ffmpeg_bin, "-i", audio_path,
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Parse time from stderr e.g. "time=00:00:08.45"
        import re
        m = re.search(r'time=(\d+):(\d+):([\d\.]+)', res.stderr)
        if m:
            hours = float(m.group(1))
            mins = float(m.group(2))
            secs = float(m.group(3))
            return max(1.0, round(hours * 3600 + mins * 60 + secs, 2))
    except Exception:
        pass

    # 3. Fallback estimate from file size or word count
    return 5.0


async def _synthesize_edge_tts(text: str, voice: str, output_path: str) -> bool:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception as e:
        logger.warning(f"[TTS Cascade] Tier 1 edge-tts notice: {e}")
        return False


async def _synthesize_kokoro(text: str, output_path: str) -> bool:
    try:
        import kokoro  # type: ignore
        # If kokoro is available, invoke its pipeline
        pipeline = kokoro.KPipeline(lang_code='a')
        generator = pipeline(text, voice='af_heart', speed=1)
        for _, _, audio in generator:
            import soundfile as sf  # type: ignore
            sf.write(output_path, audio, 24000)
            return True
    except Exception:
        pass
    return False


async def _synthesize_piper(text: str, output_path: str) -> bool:
    try:
        piper_bin = shutil.which("piper")
        if piper_bin:
            cmd = [piper_bin, "--output_file", output_path]
            proc = subprocess.run(cmd, input=text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception:
        pass
    return False


async def _synthesize_gtts(text: str, language: str, output_path: str) -> bool:
    try:
        from gtts import gTTS
        lang_code = "hi" if language.lower() in ["hindi", "hinglish"] else "en"
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception as e:
        logger.warning(f"[TTS Cascade] Tier 4 gTTS notice: {e}")
        return False


async def generate_narration_audio(
    text: str,
    output_path: str,
    language: str = "hinglish",
    voice: Optional[str] = None,
    speed: float = 1.0,
) -> Tuple[str, float]:
    """
    Generates educational speech audio through the pluggable TTS cascade:
    Edge-TTS -> Kokoro Local -> Piper Local -> gTTS emergency fallback.
    Never produces artificial sine/tone audio for learner-facing lessons.
    """
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    text_clean = LanguageTeachingEngine.normalize_narration(text, language=language)
    if not text_clean:
        text_clean = "Welcome to this concept lesson."

    target_voice = voice or get_recommended_voice(language)
    text_hash = hashlib.md5(f"{text_clean}_{language}_{target_voice}_{speed}".encode()).hexdigest()
    cached_file = os.path.join(AUDIO_CACHE_DIR, f"{text_hash}.mp3")

    # 1. Check local audio cache
    if os.path.exists(cached_file) and os.path.getsize(cached_file) > 100:
        if cached_file != output_path:
            shutil.copy2(cached_file, output_path)
        dur = probe_audio_duration(output_path)
        return output_path, dur

    # Temporary file for synthesis
    temp_audio = output_path + ".tmp.mp3"

    # Tier 1: Edge-TTS
    success = await _synthesize_edge_tts(text_clean, target_voice, temp_audio)

    # Tier 2: Kokoro Local
    if not success:
        success = await _synthesize_kokoro(text_clean, temp_audio)

    # Tier 3: Piper Local
    if not success:
        success = await _synthesize_piper(text_clean, temp_audio)

    # Tier 4: gTTS Emergency Fallback
    if not success:
        success = await _synthesize_gtts(text_clean, language, temp_audio)

    if success and os.path.exists(temp_audio):
        shutil.move(temp_audio, output_path)
        # Cache the result
        shutil.copy2(output_path, cached_file)
        dur = probe_audio_duration(output_path)
        return output_path, dur

    # If all network/local TTS services were unavailable, estimate words
    # and raise clear exception rather than producing a fake sine tone
    word_count = len(text_clean.split())
    est_dur = max(3.0, round((word_count / 140.0) * 60.0, 1))
    raise RuntimeError(
        f"All TTS synthesis providers in cascade (edge-tts, kokoro, piper, gTTS) failed for text: '{text_clean[:60]}...'. "
        "Audio generation failed safely without corrupting lesson with artificial tones."
    )
