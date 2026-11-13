"""Generate and cache Russian course audio. No arbitrary user text is accepted."""
import asyncio
import hashlib
import os
import tempfile
from pathlib import Path
from threading import BoundedSemaphore

GENERATION_SLOTS = BoundedSemaphore(2)


class AudioBusy(RuntimeError):
    """Reject excess work without tying up another web-server thread."""

VOICES = {"svetlana": "ru-RU-SvetlanaNeural", "dmitry": "ru-RU-DmitryNeural"}
RATES = {"slow": "-25%", "normal": "-10%", "fast": "+0%"}


def generate_audio(text: str, voice: str, rate: str, cache: Path) -> Path:
    speaker, speed = VOICES[voice], RATES[rate]
    text = text.replace("\u0301", "")
    fingerprint = hashlib.sha256(f"{speaker}|{speed}|{text}".encode("utf-8")).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / f"{fingerprint}.mp3"
    if destination.is_file() and destination.stat().st_size:
        return destination

    if not GENERATION_SLOTS.acquire(blocking=False):
        raise AudioBusy("Audio generation is busy")
    temporary = None
    try:
        import edge_tts
        fd, temporary_name = tempfile.mkstemp(suffix=".mp3", dir=cache)
        os.close(fd)
        temporary = Path(temporary_name)
        async def synthesize():
            await asyncio.wait_for(edge_tts.Communicate(text, speaker, rate=speed).save(str(temporary)), timeout=18)

        asyncio.run(synthesize())
        if not temporary.stat().st_size:
            raise RuntimeError("Empty speech response")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        GENERATION_SLOTS.release()
    return destination
