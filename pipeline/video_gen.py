"""
Video Generation Module (v7 - Stable & Correct)
-----------------------------------------------

Fixes:
- Uses valid FFmpeg flags only
- Prevents infinite image loop
- Ensures audible audio on Windows
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

        image_path = IMAGE_DIR / f"scene_{scene_id:02d}.png"
        audio_path = AUDIO_DIR / f"scene_{scene_id:02d}.wav"
        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.mp4"

        print(f"[VIDEO] Generating scene video {scene_id}...")

        cmd = [
            "ffmpeg",
            "-y",

            # Inputs
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),

            # Correct modern sync option
            "-fps_mode", "vfr",

            # Force universally playable audio
            "-ar", "44100",
            "-ac", "2",

            # Encoding
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",

            # Stop when audio ends
            "-shortest",

            str(output_path)
        ]

        subprocess.run(cmd, check=True)

    return len(scenes)
