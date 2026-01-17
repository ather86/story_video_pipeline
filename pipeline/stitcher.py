"""
Final Stitcher Module
---------------------

Responsibility:
- Combine scene video clips into a single final video
- Uses absolute paths to avoid FFmpeg concat issues
"""

import json
import subprocess
from pathlib import Path


SCENE_PATH = Path("schemas/scene_manifest.json").resolve()
CLIPS_DIR = Path("outputs/clips").resolve()
OUTPUT_DIR = Path("outputs/final").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def stitch_final_video():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])

    concat_file = OUTPUT_DIR / "concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for scene in scenes:
            scene_id = scene["scene_id"]
            clip_path = CLIPS_DIR / f"scene_{scene_id:02d}.mp4"
            f.write(f"file '{clip_path.as_posix()}'\n")

    final_video_path = OUTPUT_DIR / "final_video.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(final_video_path)
    ]

    subprocess.run(cmd, check=True)

    return final_video_path
