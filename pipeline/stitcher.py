"""
Final Stitcher Module (v5 - Run-Aware, Bulletproof Audio + Video)
---------------------------------------------------------------

Uses FFmpeg filter_complex concat
✔ Works on Windows
✔ Preserves audio
✔ Forces identical audio format
✔ Safe re-encode
✔ Run-aware (no cross-run collisions)
"""

import json
import subprocess
from pathlib import Path


SCENE_PATH = Path("schemas/scene_manifest.json")
VIDEOS_DIR = Path("outputs/videos")
OUTPUT_DIR = Path("outputs/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def stitch_final_video(run_id: str):
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes found to stitch.")

    ffmpeg_inputs = []
    filter_parts = []

    for idx, scene in enumerate(scenes):
        scene_id = scene["scene_id"]
        clip_path = VIDEOS_DIR / f"{run_id}_scene_{scene_id}.mp4"

        if not clip_path.exists():
            raise FileNotFoundError(f"Missing clip: {clip_path}")

        ffmpeg_inputs.extend(["-i", str(clip_path)])
        filter_parts.append(f"[{idx}:v][{idx}:a]")

    # Chain two filters: first concat all streams, then boost the final audio.
    filter_complex = (
        "".join(filter_parts)
        + f"concat=n={len(scenes)}:v=1:a=1[outv][outa]; [outa]volume=2.0[final_audio]"
    )

    final_video_path = OUTPUT_DIR / f"{run_id}_final.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        *ffmpeg_inputs,
        "-filter_complex",
        filter_complex,

        # explicit mapping
        "-map", "[outv]",
        "-map", "[final_audio]",

        # force audio compatibility
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

    print(f"[STITCH] Stitching final video for run: {run_id}")
    subprocess.run(cmd, check=True)

    print(f"[STITCH] Final video ready: {final_video_path}")
    return final_video_path
