"""
Audio Generation Module (v2 - Real TTS using Coqui, Windows Safe)
---------------------------------------------------------------

Responsibility:
- Read scene_manifest.json
- Generate narration audio per scene
- Uses a model that does NOT require espeak
"""

import json
from pathlib import Path
from TTS.api import TTS


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Windows-safe model (NO espeak dependency)
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"


def load_tts():
    tts = TTS(model_name=MODEL_NAME, progress_bar=False)
    return tts


def generate_audio():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    tts = load_tts()

    for scene in scenes:
        scene_id = scene["scene_id"]
        text = scene["narration"]["text"]

        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.wav"

        print(f"[TTS] Generating audio for scene {scene_id}...")

        tts.tts_to_file(
            text=text,
            file_path=str(output_path)
        )

    return len(scenes)
