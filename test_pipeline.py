"""
End-to-end pipeline test.
"""
import json
from pipeline.planner import run_planner
from pipeline.audio_gen import generate_audio, load_tts
from pipeline.animation import animate_and_composite_scenes # Use the new animation module
from pipeline.stitcher import stitch_final_video
from src.image_generation.comfy_t2i import run_comfy_api_workflow
from src.prompts.prompt_builder import build_image_prompt
from src.utils.run_id import generate_run_id

# 1. Define a sample story
# This story is designed to test character consistency.
STORY = """
In a quiet village, lived a young woman named Elara, known for her vibrant, curly red hair and the emerald green cloak she never took off. One day, a mysterious old man, Ronan, arrived. Ronan had a long, silver beard that reached his waist and carried a gnarled oak staff. Elara, curious, approached him by the village well. Ronan smiled, his eyes twinkling, and he told her a story of a hidden treasure.
"""

# --- NEW: Model/Style Selection for Testing ---
# Change this path to test different ComfyUI workflows.
# Examples:
# "comfy/workflows/image_netayume_lumina_t2i_api.json" (Default)
# "comfy/workflows/anime_style_api.json" (requires you to create this file)
TEST_WORKFLOW_PATH = "comfy/workflows/image_netayume_lumina_t2i_api.json"

# Control flag for testing. Set to True to test the memory-intensive animation.
ANIMATE_SCENES_IN_TEST = False

def test_full_pipeline():
    """
    Runs the full end-to-end pipeline and checks for errors.
    """
    # 2. Run the planner
    print("🧠 Planning scenes...")
    # Run the planner and use the returned manifest directly to ensure data consistency.
    manifest = run_planner(STORY, language="English", ethnicity_hint="Automatic (from story)")
    scenes = manifest["scenes"]
    global_style = manifest["global_style"]
    aspect_ratio = manifest.get("video_meta", {}).get("aspect_ratio", "16:9")

    # Create a lookup map for character descriptions, ensuring we use `character_id`
    # which is the correct key from the planner's output.
    character_map = {
        c["character_id"]: c for c in manifest.get("characters", [])
    }

    run_id = generate_run_id()
    print(f"🆔 Run ID: {run_id}")


    # 4. Generate images for each scene
    print("🖼️ Generating images...")
    for scene in scenes:
        scene_id = scene["scene_id"]
        prompt = build_image_prompt(scene, global_style, character_map)
        print(f"  - Scene {scene_id}: {prompt}")

        run_comfy_api_workflow(
            api_workflow_path=TEST_WORKFLOW_PATH,
            prompts=prompt,
            run_id=run_id,
            scene_id=scene_id,
            aspect_ratio=aspect_ratio
        )

    # 5. Generate audio
    print("🎧 Generating audio...")
    # Load the TTS model and pass the instance to the audio generation function.
    tts_instance = load_tts()
    generate_audio(run_id, manifest, tts=tts_instance, language="en")

    # 6. Generate scene videos
    if ANIMATE_SCENES_IN_TEST:
        print("🎞️ Animating scene videos...")
    else:
        print("🎞️ Creating static scene videos...")

    animate_and_composite_scenes(run_id, manifest, animate=ANIMATE_SCENES_IN_TEST)

    # 7. Stitch final video
    print("🧩 Stitching final video...")
    final_path = stitch_final_video(run_id, manifest)

    print("\n" + "="*30)
    print("✅ Full pipeline test completed successfully!")
    print(f"🎉 Final video created at: {final_path}")
    print("="*30 + "\n")

if __name__ == "__main__":
    test_full_pipeline()
