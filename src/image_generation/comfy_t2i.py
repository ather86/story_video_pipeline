"""
ComfyUI Text-to-Image Adapter (v2.2 – Stable, Run-Isolated, Scene-Variant, Semantic)
---------------------------------------------------------------------------------
TEMP WORKAROUND:
ComfyUI ignores workflow output_dir in some setups.
Images are copied from ComfyUI default output folder
into pipeline outputs/images with deterministic naming.

When Comfy output_dir works reliably, this copy block
can be removed safely.
"""

import json
import uuid
import os
import requests
import time
import shutil
import hashlib
from pathlib import Path
from copy import deepcopy


# ---------------- CONFIG ----------------

COMFY_URL = "http://127.0.0.1:8188/prompt"

# Use env var or default to standard ComfyUI output location relative to drive root or install
COMFY_OUTPUT_DIR = Path(os.getenv("COMFY_OUTPUT_DIR", "D:/StabilityMatrix-win-x64/Data/Packages/ComfyUI/output"))

PIPELINE_OUTPUT_DIR = Path("outputs/images")
PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- INTERNAL HELPERS ----------------

def _get_consistent_seed(run_id: str) -> int:
    """
    Deterministic per-run seed. Using the same seed across all scenes
    in a run is the simplest and most effective way to encourage
    character and style consistency.
    """
    h = hashlib.sha256(f"{run_id}".encode()).hexdigest()
    return int(h[:8], 16)


# ---------------- PUBLIC API ----------------

def run_comfy_api_workflow(
    api_workflow_path: str,
    prompts: dict,
    run_id: str,
    scene_id: int,
    aspect_ratio: str = "16:9",
):
    """
    Submits a ComfyUI workflow and guarantees that
    the generated image appears in outputs/images.
    """

    # 0️⃣ Pre-flight check
    if not COMFY_OUTPUT_DIR.exists():
        raise FileNotFoundError(
            f"ComfyUI output directory not found: {COMFY_OUTPUT_DIR}\n"
            "Please set the COMFY_OUTPUT_DIR environment variable to your ComfyUI output folder."
        )

    # Load workflow
    with open(api_workflow_path, "r", encoding="utf-8") as f:
        prompt_graph = deepcopy(json.load(f))

    # --------------------------------------------------
    # 1️⃣ 🔥 CORRECT PROMPT INJECTION (SEMANTIC FIX)
    # Inject story text into PrimitiveStringMultiline
    # that feeds POSITIVE and NEGATIVE prompt chains
    # --------------------------------------------------
    positive_injected = False
    negative_injected = False

    # Find all potential prompt nodes first
    prompt_nodes = [
        node for node in prompt_graph.values()
        if node.get("class_type") == "PrimitiveStringMultiline"
    ]

    # Try to identify and inject the negative prompt first
    for node in prompt_nodes:
        value = node.get("inputs", {}).get("value", "").lower()
        if ("ugly" in value or "negative prompt" in value or "bad anatomy" in value) and "you are an assistant" not in value:
            node["inputs"]["value"] = prompts["negative"]
            negative_injected = True
            print("[COMFY] ✓ Negative prompt injected.")
            prompt_nodes.remove(node)  # Remove from list to avoid re-use
            break

    # Assume the first remaining non-system prompt node is the positive one
    for node in prompt_nodes:
        value = node.get("inputs", {}).get("value", "").lower()
        if "you are an assistant" in value or "speech bubble" in value:
            continue
        node["inputs"]["value"] = prompts["positive"]
        positive_injected = True
        print("[COMFY] ✓ Positive prompt injected.")
        break

    if not positive_injected:
        raise RuntimeError(
            "Failed to inject story prompt into POSITIVE prompt chain"
        )

    # --------------------------------------------------
    # 2️⃣ Inject deterministic filename prefix
    # --------------------------------------------------
    filename_prefix = f"{run_id}_scene_{scene_id}"

    save_nodes = 0
    for node in prompt_graph.values():
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = filename_prefix
            # Remove absolute output_dir if present to force ComfyUI to use its default
            if "output_dir" in node["inputs"]:
                del node["inputs"]["output_dir"]
            save_nodes += 1

    if save_nodes == 0:
        raise RuntimeError("No SaveImage node found in workflow")

    print(f"[COMFY] ✓ Filename prefix set: {filename_prefix}")

    # --------------------------------------------------
    # 3️⃣ Inject aspect ratio from manifest
    # --------------------------------------------------
    try:
        w_ratio, h_ratio = map(int, aspect_ratio.split(':'))
        # Target a total area of ~1MP (1024*1024), common for SD3/Lumina models
        target_area = 1024 * 1024
        k = (target_area / (w_ratio * h_ratio)) ** 0.5
        # Round to nearest 64 for model compatibility
        width = int(k * w_ratio // 64) * 64
        height = int(k * h_ratio // 64) * 64
    except (ValueError, ZeroDivisionError):
        width, height = 1024, 1024 # Default to 1:1 if ratio is malformed

    latent_nodes = 0
    for node in prompt_graph.values():
        # Target any node that creates an empty latent image
        if "Empty" in node.get("class_type") and "LatentImage" in node.get("class_type"):
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            latent_nodes += 1

    if latent_nodes > 0:
        print(f"[COMFY] ✓ Aspect ratio {aspect_ratio} injected as {width}x{height}")
    else:
        print("[COMFY][WARN] Could not find an EmptyLatentImage node to inject aspect ratio.")

    # --------------------------------------------------
    # 4️⃣ Inject CONSISTENT seed for character/style
    # --------------------------------------------------
    seed = _get_consistent_seed(run_id)

    sampler_nodes = 0
    for node in prompt_graph.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed
            sampler_nodes += 1

    if sampler_nodes == 0:
        raise RuntimeError("No KSampler node found to inject seed")

    print(f"[COMFY] ✓ Consistent seed injected for run: {seed}")

    # --------------------------------------------------
    # 5️⃣ Submit job
    # --------------------------------------------------
    payload = {
        "prompt": prompt_graph,
        "client_id": str(uuid.uuid4()),
    }

    response = requests.post(COMFY_URL, json=payload)
    response.raise_for_status()

    prompt_id = response.json().get("prompt_id")
    print(f"[COMFY] Job submitted: {prompt_id} (scene {scene_id})")

    # --------------------------------------------------
    # 6️⃣ Wait & copy image (TEMP WORKAROUND)
    # --------------------------------------------------
    _wait_and_copy_image(
        filename_prefix=filename_prefix,
        timeout_sec=180,
    )

    return prompt_id


# ---------------- INTERNAL ----------------

def _wait_and_copy_image(filename_prefix: str, timeout_sec: int):
    """
    Waits for ComfyUI to emit an image and copies the
    most recent matching file into outputs/images.

    Preserves Comfy suffix (_00001.png).
    """

    start_time = time.time()
    last_seen = None

    while time.time() - start_time < timeout_sec:
        matches = list(COMFY_OUTPUT_DIR.glob(f"{filename_prefix}_*.png"))

        if matches:
            src = max(matches, key=lambda p: p.stat().st_mtime)

            # Skip half-written files
            if last_seen != src:
                last_seen = src
                time.sleep(0.5)
                continue

            dst = PIPELINE_OUTPUT_DIR / src.name
            shutil.copy2(src, dst)
            print(f"[COMFY] ✓ Image copied: {dst.name}")
            return dst

        elapsed = int(time.time() - start_time)
        print(
            f"[COMFY] ⏳ Waiting for image '{filename_prefix}'... {elapsed}s",
            end="\r",
        )
        time.sleep(2)

    raise TimeoutError(
        f"[COMFY] Image timeout: '{filename_prefix}' not found in {COMFY_OUTPUT_DIR}"
    )
