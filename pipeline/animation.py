"""
Animation & Composition Module (v2 - Kandinsky5 I2V + FFmpeg)
---------------------------------------------------

Responsibility:
- Animate a static image using a ComfyUI Kandinsky5 Image-to-Video workflow.
- Composite the resulting silent video with narration audio.
"""

import json
import os
import requests
import time
import shutil
import uuid
import subprocess
import hashlib
from pathlib import Path
from math import ceil
from copy import deepcopy
from mutagen.wave import WAVE
from src.prompts.prompt_builder import build_image_prompt

# --- CONFIGURATION ---

COMFY_URL = "http://127.0.0.1:8188/prompt"
COMFY_OUTPUT_DIR = Path(os.getenv("COMFY_OUTPUT_DIR", "D:/StabilityMatrix-win-x64/Data/Packages/ComfyUI/output"))
COMFY_INPUT_DIR = Path(os.getenv("COMFY_INPUT_DIR", "D:/StabilityMatrix-win-x64/Data/Packages/ComfyUI/input"))
COMFY_INPUT_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_IMAGES_DIR = Path("outputs/images")
PIPELINE_AUDIO_DIR = Path("outputs/audio")
PIPELINE_VIDEOS_DIR = Path("outputs/videos")
PIPELINE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VIDEO_FPS = 24
BASE_ANIMATION_LENGTH_SEC = 2 # Generate a short, loopable animation to save time.
VIDEO_GENERATION_TIMEOUT_SEC = 900 # Max wait time for a single video (15 minutes for low VRAM safety).


# --- HELPERS ---

def _get_consistent_seed(run_id: str) -> int:
    """
    Deterministic per-run seed. Using the same seed across all scenes
    in a run encourages consistent motion style.
    """
    h = hashlib.sha256(f"{run_id}".encode()).hexdigest()
    return int(h[:8], 16)

def _find_scene_image(run_id: str, scene_id: int) -> Path:
    """Finds the generated image for a given scene."""
    matches = list(PIPELINE_IMAGES_DIR.glob(f"{run_id}_scene_{scene_id}_*.png"))
    if not matches:
        raise FileNotFoundError(f"Image for run '{run_id}', scene {scene_id} not found.")
    return max(matches, key=lambda p: p.stat().st_mtime)

def _get_audio_duration_sec(audio_path: Path) -> float:
    """Gets the duration of a WAV file."""
    if not audio_path.exists():
        return 4.0  # Default duration if audio is missing
    try:
        audio = WAVE(str(audio_path))
        return audio.info.length
    except Exception:
        return 4.0

def _wait_and_copy_video(filename_prefix: str, timeout_sec: int) -> Path:
    """Waits for ComfyUI to generate a video and copies it to the pipeline output."""
    start_time = time.time()
    print(f"[ANIMATE] ⏳ Waiting for video '{filename_prefix}'... 0s", end="\r")
    while time.time() - start_time < timeout_sec:
        # SVD workflows often output MP4
        matches = list(COMFY_OUTPUT_DIR.glob(f"{filename_prefix}_*.mp4"))
        if matches:
            src = max(matches, key=lambda p: p.stat().st_mtime)
            # Wait a moment to ensure the file is fully written
            time.sleep(1.0)
            dst = PIPELINE_VIDEOS_DIR / f"{filename_prefix}_silent.mp4"
            shutil.copy2(src, dst)
            print(f"[ANIMATE] ✓ Silent video copied: {dst.name}")
            return dst

        elapsed = int(time.time() - start_time)
        print(f"[ANIMATE] ⏳ Waiting for video '{filename_prefix}'... {elapsed}s", end="\r")
        time.sleep(2)

    print() # Add a newline after the waiting indicator is done.
    raise TimeoutError(f"Video timeout ({timeout_sec}s): '{filename_prefix}' not found in {COMFY_OUTPUT_DIR}")

def _create_static_fallback_video(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    reason: str = "Animation failed"
):
    """Creates a static video by looping an image over audio as a fallback."""
    print(f"[ANIMATE][STATIC] {reason}. Creating static video for {output_path.name}")
    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[ANIMATE][STATIC] ✓ Static fallback video created: {output_path.name}")

# --- CORE FUNCTIONS ---

def _run_comfy_animation(
    input_image_path: Path,
    run_id: str,
    scene_id: int,
    positive_prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    video_length_frames: int,
) -> Path:
    """Runs the Kandinsky5 I2V workflow in ComfyUI to generate a silent video."""
    print(f"[ANIMATE] Submitting Kandinsky5 I2V job for scene {scene_id}")

    # 1. Load workflow template
    with open("comfy/workflows/video_kandinsky5_i2v.json", "r", encoding="utf-8") as f: # Changed to Kandinsky5
        prompt_graph = json.load(f)

    # 1b. Stage the source image in ComfyUI's input directory so it can be found.
    image_name = input_image_path.name
    comfy_input_path = COMFY_INPUT_DIR / image_name
    shutil.copy2(input_image_path, comfy_input_path)
    print(f"[ANIMATE] ✓ Input image staged in ComfyUI input folder.")

    # 2. Inject scene-specific data into the workflow graph
    filename_prefix = f"{run_id}_scene_{scene_id}"

    # Find and update the LoadImage node
    load_image_node = next((n for n in prompt_graph.values() if n["class_type"] == "LoadImage"), None)
    if not load_image_node:
        raise RuntimeError("No 'LoadImage' node found in the Kandinsky5 workflow.")
    load_image_node["inputs"]["image"] = image_name # Use just the filename
    print(f"[ANIMATE] ✓ Input image set in workflow: {image_name}")

    # Find and update the SaveVideo node
    save_node = next((n for n in prompt_graph.values() if n["class_type"] == "SaveVideo"), None)
    if not save_node:
        raise RuntimeError("No 'SaveVideo' node found in the Kandinsky5 workflow.")
    save_node["inputs"]["filename_prefix"] = filename_prefix
    print(f"[ANIMATE] ✓ Filename prefix set: {filename_prefix}")

    # 3. Inject positive and negative prompts
    positive_prompt_node = next((n for n in prompt_graph.values() if n.get("_meta", {}).get("title") == "CLIP Text Encode (Positive Prompt)"), None)
    negative_prompt_node = next((n for n in prompt_graph.values() if n.get("_meta", {}).get("title") == "CLIP Text Encode (Negative Prompt)"), None)

    if not positive_prompt_node or not negative_prompt_node:
        raise RuntimeError("Could not find positive or negative CLIP Text Encode nodes in Kandinsky5 workflow.")

    positive_prompt_node["inputs"]["text"] = positive_prompt
    negative_prompt_node["inputs"]["text"] = negative_prompt
    print(f"[ANIMATE] ✓ Prompts injected (Positive: '{positive_prompt[:50]}...', Negative: '{negative_prompt[:50]}...')")

    # 4. Inject resolution (width and height)
    width_node = next((n for n in prompt_graph.values() if n.get("_meta", {}).get("title") == "Width"), None)
    height_node = next((n for n in prompt_graph.values() if n.get("_meta", {}).get("title") == "Height"), None)
    kandinsky_i2v_node = next((n for n in prompt_graph.values() if n["class_type"] == "Kandinsky5ImageToVideo"), None)

    if not width_node or not height_node or not kandinsky_i2v_node:
        raise RuntimeError("Could not find resolution or Kandinsky5ImageToVideo nodes in workflow.")

    width_node["inputs"]["value"] = width
    height_node["inputs"]["value"] = height
    print(f"[ANIMATE] ✓ Resolution set to {width}x{height}")

    # 5. Inject video length in frames
    kandinsky_i2v_node["inputs"]["length"] = video_length_frames
    print(f"[ANIMATE] ✓ Video length set to {video_length_frames} frames")

    # 6. Inject consistent seed for deterministic motion
    seed = _get_consistent_seed(run_id)
    sampler_node = next((n for n in prompt_graph.values() if n["class_type"] == "KSampler"), None)
    if not sampler_node:
        raise RuntimeError("No 'KSampler' node found in the Kandinsky5 workflow to inject seed.")
    sampler_node["inputs"]["seed"] = seed
    print(f"[ANIMATE] ✓ Consistent seed injected for run: {seed}")

    # 7. Submit to ComfyUI
    payload = {"prompt": prompt_graph, "client_id": str(uuid.uuid4())}
    response = requests.post(COMFY_URL, json=payload)
    response.raise_for_status()

    # 8. Wait for and retrieve the generated video
    silent_video_path = _wait_and_copy_video(filename_prefix, timeout_sec=VIDEO_GENERATION_TIMEOUT_SEC)
    return silent_video_path

def _composite_with_audio(
    silent_video_path: Path,
    audio_path: Path,
    output_path: Path,
    target_duration: float
):
    """Combines the silent video with audio using FFmpeg, looping video to match audio duration."""
    print(f"[ANIMATE] Compositing video and audio for {output_path.name}")

    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop", "-1",  # Loop the video input indefinitely
        "-i", str(silent_video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",  # Finish encoding when the shortest stream (audio) ends
        str(output_path),
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[ANIMATE] ✓ Final scene video created: {output_path.name}")


# --- PUBLIC ENTRY POINT ---

def animate_and_composite_scenes(
    run_id: str,
    manifest: dict,
    animate: bool = True
):
    """
    Public entry point.
    For each scene, animates the image and composites it with audio.
    If `animate` is False, it creates static videos instead.
    """
    scenes = manifest.get("scenes", [])
    global_style = manifest.get("global_style", {})
    aspect_ratio_str = manifest.get("video_meta", {}).get("aspect_ratio", "16:9")
    character_map = {c["character_id"]: c for c in manifest.get("characters", [])}

    if not scenes:
        print("[ANIMATE] No scenes to animate.")
        return

    # Calculate target resolution based on aspect ratio and 720p height
    try:
        w_ratio, h_ratio = map(int, aspect_ratio_str.split(':'))
        target_height = 576 # Lowered from 720 to reduce VRAM usage. 576p is a good balance.
        target_width = int(target_height * w_ratio / h_ratio)
        # Ensure width is a multiple of 8 or 64 for model compatibility if needed,
        # but Kandinsky5 often handles various resolutions.
        target_width = (target_width // 8) * 8
        target_height = (target_height // 8) * 8
    except (ValueError, ZeroDivisionError):
        print(f"[ANIMATE][WARN] Invalid aspect ratio '{aspect_ratio_str}'. Defaulting to 1280x720.")
        target_width, target_height = 1280, 720

    print(f"[ANIMATE] Target animation resolution: {target_width}x{target_height}")

    for scene in scenes:
        scene_id = scene["scene_id"]

        # --- 1. Asset Pre-flight Check ---
        # Ensure the required image and audio files exist before trying to process them.
        # If they don't, we can't create a video for this scene, so we skip it.
        try:
            image_path = _find_scene_image(run_id, scene_id)
            audio_path = PIPELINE_AUDIO_DIR / f"{run_id}_scene_{scene_id}.wav"
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found for scene {scene_id}")
        except FileNotFoundError as e:
            print(f"[ANIMATE][ERROR] Skipping scene {scene_id} due to missing asset: {e}")
            continue

        # --- 2. Video Generation ---
        # Now that we know the assets exist, we can safely proceed.
        final_video_path = PIPELINE_VIDEOS_DIR / f"{run_id}_scene_{scene_id}.mp4"
        try:
            if not animate:
                _create_static_fallback_video(image_path, audio_path, final_video_path, reason="Animation disabled by user")
                continue

            prompts = build_image_prompt(scene, global_style, character_map)
            audio_duration = _get_audio_duration_sec(audio_path)
            video_length_frames = ceil(BASE_ANIMATION_LENGTH_SEC * DEFAULT_VIDEO_FPS)

            silent_video_path = _run_comfy_animation(
                image_path,
                run_id,
                scene_id,
                prompts["positive"],
                prompts["negative"],
                target_width,
                target_height,
                video_length_frames
            )

            _composite_with_audio(silent_video_path, audio_path, final_video_path, audio_duration)
            silent_video_path.unlink()

        except (RuntimeError, TimeoutError) as e:
            print(f"[ANIMATE][ERROR] Animation failed for scene {scene_id}: {e}")
            # Fallback is safe here because image_path and audio_path are guaranteed to exist.
            _create_static_fallback_video(image_path, audio_path, final_video_path, reason="Animation failed, creating static fallback.")
            continue
