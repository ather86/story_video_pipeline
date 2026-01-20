"""
Image Generation Module (ComfyUI - Step 1)
-----------------------------------------
Responsibility:
- Read scene_manifest.json
- Build image prompts strictly from story meaning
- Generate one image per scene via ComfyUI
"""

import json
from pathlib import Path

from src.prompts.prompt_builder import build_image_prompt
from src.image_generation.comfy_t2i import run_comfy_api_workflow
from src.utils.run_id import generate_run_id


SCENE_PATH = Path("schemas/scene_manifest.json")
API_WORKFLOW = Path("comfy/workflows/image_netayume_lumina_t2i_api.json")


def generate_images_with_comfy():
    # Load story manifest
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    global_style = manifest.get("global_style", {})
    aspect_ratio = manifest.get("video_meta", {}).get("aspect_ratio", "16:9")

    # Create a lookup map for character descriptions
    characters = manifest.get("characters", [])
    character_map = {c["character_id"]: c for c in characters}

    run_id = generate_run_id()
    print(f"[IMAGE GEN] Run ID: {run_id}")

    for scene in scenes:
        scene_id = scene["scene_id"]

        # ✅ Build prompt ONLY from scene meaning
        prompt = build_image_prompt(
            scene=scene,
            global_style=global_style,
            character_map=character_map
        )

        print(f"[IMAGE GEN] Generating image for scene {scene_id}")

        run_comfy_api_workflow(
            api_workflow_path=str(API_WORKFLOW),
            prompts=prompt,
            run_id=run_id,
            scene_id=scene_id,
            aspect_ratio=aspect_ratio
        )

    return run_id
