"""
Video Generation Module (v1 - Stub)
----------------------------------

Responsibility:
- Read scene_manifest.json
- Combine image + audio into a scene video clip

NOTE:
- Uses ffmpeg
- No motion effects yet
"""

import json
import subprocess
from pathlib import Path


SCENE_PATH = Path("schemas/scene_manifest.json")
IMAGE_DIR = Path("outputs/images")
AUDIO_DIR = Path("outputs/audio")
OUTPUT_DIR = Path("outputs/clips")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_scene_videos():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])

    for scene in scenes:
        scene_id = scene["scene_id"]
        duration = scene["duration_sec"]

        image_path = IMAGE_DIR / f"scene_{scene_id:02d}.png"
        audio_path = AUDIO_DIR / f"scene_{scene_id:02d}.wav"
        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.mp4"

        cmd = [
            "ffmpeg",
            "-y",                         # overwrite
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(output_path)
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return len(scenes)
