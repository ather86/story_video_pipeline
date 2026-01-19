import json
from pipeline.prompt_compiler import PromptCompiler

with open("schemas/scene_manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

scene = manifest["scenes"][0]

prompt = PromptCompiler.compile(
    scene=scene,
    global_style=manifest["global_style"],
    characters=manifest["characters"]
)

print(prompt)
