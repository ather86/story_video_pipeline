import streamlit as st
from pathlib import Path
import json

from src.utils.run_id import generate_run_id

# NEW PIPELINE IMPORTS
from pipeline.planner import run_planner
from src.image_generation.comfy_t2i import run_comfy_api_workflow
from src.prompts.prompt_builder import build_image_prompt
from pipeline.audio_gen import generate_audio
from pipeline.image_to_video import generate_scene_videos
from pipeline.stitcher import stitch_final_video



st.set_page_config(page_title="Story → Video Pipeline", layout="centered")

st.title("🎬 Story → Video Pipeline")
st.write("Convert a story into a structured video — end to end.")

story_text = st.text_area(
    "Enter your story",
    height=200,
    placeholder="Paste your story, LinkedIn post, or idea here..."
)

skip_images = st.checkbox("⚡ Skip Image Generation", value=False)
skip_audio = st.checkbox("🔇 Skip Audio Generation", value=False)

st.divider()

if st.button("🚀 Run Full Pipeline"):
    if not story_text.strip():
        st.warning("Please enter a story.")
        st.stop()

    # -------------------------------
    # 1️⃣ PLAN SCENES
    # -------------------------------
    with st.spinner("🧠 Planning scenes..."):
        run_planner(story_text)

    # Load manifest
    with open("schemas/scene_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest["scenes"]
    global_style = manifest["global_style"]
    aspect_ratio = manifest.get("video_meta", {}).get("aspect_ratio", "16:9")

    character_map = {
        c["character_id"]: c for c in manifest.get("characters", [])
    }

    run_id = generate_run_id()
    st.info(f"🆔 Run ID: {run_id}")

    # -------------------------------
    # 2️⃣ IMAGE GENERATION
    # -------------------------------
    if not skip_images:
        with st.spinner("🖼️ Generating images..."):
            for scene in scenes:
                scene_id = scene["scene_id"]
                prompt = build_image_prompt(scene, global_style, character_map)

                run_comfy_api_workflow(
                    api_workflow_path="comfy/workflows/image_netayume_lumina_t2i_api.json",
                    prompts=prompt,
                    run_id=run_id,
                    scene_id=scene_id,
                    aspect_ratio=aspect_ratio
                )
    else:
        st.info("⚡ Image generation skipped")

    # -------------------------------
    # 3️⃣ AUDIO GENERATION
    # -------------------------------
    if not skip_audio:
        with st.spinner("🎧 Generating audio..."):
            generate_audio(run_id)
    else:
        st.info("🔇 Audio generation skipped")

    # -------------------------------
    # 4️⃣ IMAGE → VIDEO
    # -------------------------------
    with st.spinner("🎞️ Creating scene videos..."):
        generate_scene_videos(run_id)

    # -------------------------------
    # 5️⃣ STITCH FINAL VIDEO
    # -------------------------------
    with st.spinner("🧩 Stitching final video..."):
        final_path = stitch_final_video(run_id)

    st.success("🎉 Video generated successfully!")

    # -------------------------------
    # PREVIEW
    # -------------------------------
    st.divider()
    st.subheader("🎬 Final Video")

    if Path(final_path).exists():
        st.video(str(final_path))
        st.download_button(
            "⬇️ Download Final Video",
            data=open(final_path, "rb"),
            file_name=f"{run_id}_final.mp4",
            mime="video/mp4"
        )
