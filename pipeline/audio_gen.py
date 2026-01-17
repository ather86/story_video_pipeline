"""
Audio Generation Module (v1 - Stub)
----------------------------------

Responsibility:
- Read scene_manifest.json
- Generate one narration audio file per scene

NOTE:
- This is a placeholder implementation.
- Real TTS will be integrated later.
"""

import json
from pathlib import Path
import wave
import struct


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_audio():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])

    for scene in scenes:
        scene_id = scene["scene_id"]
        narration_text = scene["narration"]["text"]

        # Create silent WAV as placeholder
        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.wav"

        duration_sec = scene["duration_sec"]
        sample_rate = 44100
        num_samples = duration_sec * sample_rate

        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)

            silence = struct.pack("<h", 0)
            wf.writeframes(silence * num_samples)

    return len(scenes)
