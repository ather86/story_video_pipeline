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
import requests
import time
import shutil
import hashlib
from pathlib import Path
from copy import deepcopy


# ---------------- CONFIG ----------------

COMFY_URL = "http://127.0.0.1:8188/prompt"

COMFY_OUTPUT_DIR = Path(
    "D:/StabilityMatrix-win-x64/Data/Packages/ComfyUI/output"
)

PIPELINE_OUTPUT_DIR = Path("outputs/images")
PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- INTERNAL HELPERS ----------------

def _scene_seed(run_id: str, scene_id: int) -> int:
    """
    Deterministic per-scene seed.
    Same run + scene → same image
    Different scene → different image
    """
    h = hashlib.sha256(f"{run_id}_{scene_id}".encode()).hexdigest()
    return int(h[:8], 16)


# ---------------- PUBLIC API ----------------

def run_comfy_api_workflow(
    api_workflow_path: str,
    prompt_text: str,
    run_id: str,
    scene_id: int,
):
    """
    Submits a ComfyUI workflow and guarantees that
    the generated image appears in outputs/images.
    """

    # Load workflow
    with open(api_workflow_path, "r", encoding="utf-8") as f:
        prompt_graph = deepcopy(json.load(f))

    # --------------------------------------------------
    # 1️⃣ 🔥 CORRECT PROMPT INJECTION (SEMANTIC FIX)
    # Inject story text into PrimitiveStringMultiline
    # that feeds POSITIVE prompt chain
    # --------------------------------------------------
    injected = False
    for node in prompt_graph.values():
        if node.get("class_type") == "PrimitiveStringMultiline":
            value = node.get("inputs", {}).get("value", "")
            # Skip system / instruction prefix
            if "high quality anime images" in value:
                continue
            node["inputs"]["value"] = prompt_text
            injected = True
            print("[COMFY] ✓ Story prompt injected into positive text node")
            break

    if not injected:
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
            save_nodes += 1

    if save_nodes == 0:
        raise RuntimeError("No SaveImage node found in workflow")

    print(f"[COMFY] ✓ Filename prefix set: {filename_prefix}")

    # --------------------------------------------------
    # 3️⃣ Inject PER-SCENE seed
    # --------------------------------------------------
    seed = _scene_seed(run_id, scene_id)

    sampler_nodes = 0
    for node in prompt_graph.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed
            sampler_nodes += 1

    if sampler_nodes == 0:
        raise RuntimeError("No KSampler node found to inject seed")

    print(f"[COMFY] ✓ Seed injected for scene {scene_id}: {seed}")

    # --------------------------------------------------
    # 4️⃣ Submit job
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
    # 5️⃣ Wait & copy image (TEMP WORKAROUND)
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
