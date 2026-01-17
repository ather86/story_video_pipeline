"""
Streamlit App
-------------
Responsibility:
- Orchestrate full Story → Video pipeline
- Provide dev-friendly toggles
"""

import streamlit as st

from pipeline.planner import run_planner
from pipeline.image_gen import generate_images
from pipeline.audio_gen import generate_audio
from pipeline.video_gen import generate_scene_videos
from pipeline.stitcher import stitch_final_video


st.set_page_config(
    page_title="Story → Video Pipeline",
    layout="centered"
)

st.title("Story → Video Pipeline")
st.write("Convert a story into a structured video — end to end.")

story_text = st.text_area(
    "Enter your story",
    height=200,
    placeholder="Paste your story here..."
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
        with st.spinner("🖼 Generating images..."):
            generate_images()
    else:
        st.info("Using existing images")

    if not skip_audio:
        with st.spinner("🎙 Generating audio..."):
            generate_audio()
    else:
        st.info("Using existing audio")

    with st.spinner("🎞 Generating scene videos..."):
        generate_scene_videos()

    with st.spinner("🎬 Stitching final video..."):
        final_path = stitch_final_video()

    st.success("🎉 Video generated successfully")
    st.code(str(final_path))

    try:
        with open(final_path, "rb") as f:
            st.video(f.read())
    except Exception:
        st.info("Video saved. Preview unavailable.")
