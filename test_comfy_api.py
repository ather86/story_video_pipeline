import json
from src.image_generation.comfy_t2i import run_comfy_api_workflow
from src.prompts.prompt_builder import build_image_prompt
from src.utils.run_id import generate_run_id

# Load scene manifest
with open("schemas/scene_manifest.json", "r") as f:
    manifest = json.load(f)

scenes = manifest["scenes"]
global_style = manifest["global_style"]

# Build character lookup map
character_map = {c["character_id"]: c for c in manifest["characters"]}

# Generate run ID
run_id = generate_run_id()

# Generate one image per scene
for scene in scenes:
    scene_id = scene["scene_id"]

    print(f"[IMAGE GEN] Generating image for scene {scene_id}")

    prompt = build_image_prompt(
        scene=scene,
        global_style=global_style,
        character_map=character_map
    )

    run_comfy_api_workflow(
        api_workflow_path="comfy/workflows/image_netayume_lumina_t2i_api.json",
        prompts=prompt,
        run_id=run_id,
        scene_id=scene_id
    )

print("Images generated for run:", run_id)
