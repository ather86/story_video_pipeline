import streamlit as st
from pathlib import Path
import json

from pipeline.planner import run_planner
from pipeline.image_gen import generate_images
from pipeline.audio_gen import generate_audio
from pipeline.video_gen import generate_scene_videos
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

    with st.spinner("🧠 Planning scenes..."):
        run_planner(story_text)

    if not skip_images:
        with st.spinner("🖼️ Generating images..."):
            generate_images()
    else:
        st.info("⚡ Image generation skipped")

    if not skip_audio:
        with st.spinner("🎧 Generating audio..."):
            generate_audio()
    else:
        st.info("🔇 Audio generation skipped")

    with st.spinner("🎞️ Creating scene videos..."):
        generate_scene_videos()

    with st.spinner("🧩 Stitching final video..."):
        final_path = stitch_final_video()

    st.success("🎉 Video generated successfully!")

    # ---------- PREVIEW SECTION ----------
    st.divider()
    st.subheader("📽️ Scene Preview")

    scene_manifest = Path("schemas/scene_manifest.json")
    if scene_manifest.exists():
        with open(scene_manifest, "r", encoding="utf-8") as f:
            scenes = json.load(f).get("scenes", [])

        for scene in scenes:
            sid = scene["scene_id"]

            st.markdown(f"### Scene {sid}")

            img_path = Path(f"outputs/images/scene_{sid:02d}.png")
            audio_path = Path(f"outputs/audio/scene_{sid:02d}.wav")

            if img_path.exists():
                st.image(str(img_path), use_column_width=True)

            if audio_path.exists():
                st.audio(str(audio_path))

    st.divider()
    st.subheader("🎬 Final Video")

    if Path(final_path).exists():
        st.video(str(final_path))
        st.download_button(
            "⬇️ Download Final Video",
            data=open(final_path, "rb"),
            file_name="final_video.mp4",
            mime="video/mp4"
        )
