"""
Audio Generation Module (v6 - Run-Aware, Bulletproof Tacotron2)
--------------------------------------------------------------

Fixes:
✔ Smart quotes crash
✔ Empty sentence crash
✔ Short kernel crash
✔ Silence-trim destroying audio
✔ Blank WAV detection + auto-recovery
✔ Run-aware output isolation
"""

import json
import re
import wave
from pathlib import Path
from TTS.api import TTS


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"


# ---------- TEXT SAFETY ----------

def sanitize_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "“": "",
        "”": "",
        "‘": "",
        "’": "",
        "—": " ",
        "–": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def ensure_min_length(text: str) -> str:
    if len(text) < 20:
        text += " This story teaches an important lesson."
    return text


# ---------- AUDIO VALIDATION ----------

def wav_has_audio(path: Path) -> bool:
    if not path.exists():
        return False

    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            return frames > 1000   # ~0.05s @ 22050Hz
    except Exception:
        return False


# ---------- TTS ----------

def load_tts():
    return TTS(
        model_name=MODEL_NAME,
        progress_bar=False,
        gpu=False
    )


def generate_audio(run_id: str):
    """
    Generates narration audio per scene.
    Output files are isolated per run_id.
    """

    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    tts = load_tts()

    for scene in scenes:
        scene_id = scene["scene_id"]
        raw_text = scene["narration"]["text"]

        text = sanitize_text(raw_text)
        if not text:
            print(f"[TTS] Scene {scene_id} skipped (empty text)")
            continue

        text = ensure_min_length(text)

        output_path = OUTPUT_DIR / f"{run_id}_scene_{scene_id}.wav"

        print(f"[TTS] Generating audio for scene {scene_id}...")
        print(f"     Text → {text}")

        tts.tts_to_file(
            text=text,
            file_path=str(output_path),
            split_sentences=False,
        )

        # Validate WAV
        if not wav_has_audio(output_path):
            print(f"[TTS][WARN] Blank audio detected for scene {scene_id}, regenerating...")

            fallback_text = (
                text + " Remember, patience and effort always bring rewards."
            )

            tts.tts_to_file(
                text=fallback_text,
                file_path=str(output_path),
                split_sentences=False,
            )

            if not wav_has_audio(output_path):
                raise RuntimeError(
                    f"TTS failed for scene {scene_id}: WAV still silent"
                )

    return len(scenes)
