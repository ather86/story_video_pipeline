"""
Image → Video (Deterministic FFmpeg, Scene-Aware, Audio-Driven)
--------------------------------------------------------------
- One image + one audio → one video clip per scene
- Audio duration defines video length
- Waits for ComfyUI image (async-safe)
- Run + scene isolated
"""

import json
import subprocess
import time
from pathlib import Path


SCENE_MANIFEST = Path("schemas/scene_manifest.json")

OUTPUTS_DIR = Path("outputs")
IMAGES_DIR = OUTPUTS_DIR / "images"
AUDIO_DIR = OUTPUTS_DIR / "audio"
VIDEOS_DIR = OUTPUTS_DIR / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def wait_for_image(run_id, scene_id, timeout_sec=180):
    start = time.time()
    search_pattern = f"{run_id}_scene_{scene_id}_*.png"
    print(f"[I2V] Searching for: {search_pattern}")

    while time.time() - start < timeout_sec:
        matches = sorted(IMAGES_DIR.glob(search_pattern))
        if matches:
            print(f"[I2V] ✓ Found image: {matches[-1].name}")
            return matches[-1]

        elapsed = int(time.time() - start)
        if elapsed % 10 == 0:
            print(f"[I2V] ⏳ Waiting for image (scene {scene_id})... {elapsed}s")
        time.sleep(1)

    return None


def generate_scene_videos(run_id: str):
    with open(SCENE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes found in scene_manifest.json")

    for scene in scenes:
        scene_id = scene["scene_id"]

        image_path = wait_for_image(run_id, scene_id)
        if not image_path:
            raise FileNotFoundError(
                f"Image not found for scene {scene_id} (run {run_id})"
            )

        audio_path = AUDIO_DIR / f"{run_id}_scene_{scene_id}.wav"
        if not audio_path.exists():
            raise FileNotFoundError(f"Missing audio: {audio_path}")

        output_path = VIDEOS_DIR / f"{run_id}_scene_{scene_id}.mp4"

        print(f"[I2V] Scene {scene_id}")
        print(f"      Image: {image_path.name}")
        print(f"      Audio: {audio_path.name}")

        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-shortest",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", "44100",
            "-ac", "2",
            str(output_path)
        ]

        subprocess.run(cmd, check=True)

    print(f"[I2V] ✓ Generated {len(scenes)} scene videos for run {run_id}")
    return len(scenes)
