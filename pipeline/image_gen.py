"""
Image Generation Module (v2 - Real Stable Diffusion, CPU Safe)
-------------------------------------------------------------

Responsibility:
- Read scene_manifest.json
- Generate one AI image per scene
- Maintain visual continuity using a fixed seed

NOTE:
- CUDA is intentionally DISABLED for stability
- This avoids GPU kernel compatibility issues
"""

import json
from pathlib import Path
import torch
from diffusers import StableDiffusionPipeline


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "runwayml/stable-diffusion-v1-5"


def load_pipeline():
    """
    Load Stable Diffusion pipeline on CPU ONLY.
    This is intentional for maximum compatibility.
    """
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32  # CPU-safe dtype
    )
    pipe = pipe.to("cpu")        # FORCE CPU
    return pipe


def generate_images():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])
    global_style = manifest.get("global_style", {})

    pipe = load_pipeline()

    seed = 12345  # fixed seed for continuity
    generator = torch.Generator(device="cpu").manual_seed(seed)

    for scene in scenes:
        scene_id = scene["scene_id"]
        base_prompt = scene["image_generation"]["prompt"]

        full_prompt = (
            f"{base_prompt}, "
            f"{global_style.get('visual_style', '')}, "
            f"{global_style.get('lighting', '')}"
        )

        print(f"[SD][CPU] Generating image for scene {scene_id}...")

        image = pipe(
            prompt=full_prompt,
            num_inference_steps=30,
            guidance_scale=7.5,
            generator=generator
        ).images[0]

        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.png"
        image.save(output_path)

    return len(scenes)
