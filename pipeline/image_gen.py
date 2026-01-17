"""
Image Generation Module (v1)
----------------------------

Responsibility:
- Read scene_manifest.json
- Generate one placeholder image per scene
- Save images to outputs/images/

NOTE:
- This is a stub implementation.
- Real image models will be plugged in later.
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_images():
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes", [])

    for scene in scenes:
        scene_id = scene["scene_id"]
        text = scene["narration"]["text"]

        # Create placeholder image
        img = Image.new("RGB", (1024, 1024), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        message = f"Scene {scene_id}\n\n{text}"
        draw.text((50, 50), message, fill=(0, 0, 0))

        output_path = OUTPUT_DIR / f"scene_{scene_id:02d}.png"
        img.save(output_path)

    return len(scenes)
