"""
Final Stitcher Module (v4 - Bulletproof Audio + Video)
----------------------------------------------------

Uses FFmpeg filter_complex concat
✔ Works on Windows
✔ Preserves audio
✔ Forces identical audio format
✔ Safe re-encode
"""

import json
import subprocess
from pathlib import Path


SCENE_PATH = Path("schemas/scene_manifest.json")
CLIPS_DIR = Path("outputs/clips")
OUTPUT_DIR = Path("outputs/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def stitch_final_video():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes found to stitch.")

    ffmpeg_inputs = []
    filter_parts = []

    for idx, scene in enumerate(scenes):
        scene_id = scene["scene_id"]
        clip_path = CLIPS_DIR / f"scene_{scene_id:02d}.mp4"

        if not clip_path.exists():
            raise FileNotFoundError(f"Missing clip: {clip_path}")

        ffmpeg_inputs.extend(["-i", str(clip_path)])
        filter_parts.append(f"[{idx}:v][{idx}:a]")

    filter_complex = (
        "".join(filter_parts)
        + f"concat=n={len(scenes)}:v=1:a=1[outv][outa]"
    )

    final_video_path = OUTPUT_DIR / "final_video.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        *ffmpeg_inputs,
        "-filter_complex", filter_complex,

        # explicit mapping
        "-map", "[outv]",
        "-map", "[outa]",

        # 🔥 FORCE AUDIO COMPATIBILITY
        "-ar", "44100",
        "-ac", "2",

        # codecs
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",

        # playback safety
        "-movflags", "+faststart",

        str(final_video_path)
    ]

    print("[STITCH] Stitching final video with filter_complex...")
    subprocess.run(cmd, check=True)

    return final_video_path
