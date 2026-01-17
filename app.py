"""
Streamlit App
-------------

Responsibility:
- Orchestrate full Story → Video pipeline
"""

import streamlit as st

from pipeline.planner import run_planner
from pipeline.image_gen import generate_images
from pipeline.audio_gen import generate_audio
from pipeline.video_gen import generate_scene_videos
from pipeline.stitcher import stitch_final_video


st.set_page_config(page_title="Story → Video Pipeline", layout="centered")

st.title("Story → Video Pipeline")
st.write("Convert a story into a structured video — end to end.")

# Story input
story_text = st.text_area(
    label="Enter your story",
    height=200,
    placeholder="Paste your story, LinkedIn post, or idea here..."
)

st.divider()

# Full pipeline button
if st.button("🚀 Run Full Pipeline"):
    if story_text.strip() == "":
        st.warning("Please enter a story first.")
    else:
        with st.spinner("Planning scenes..."):
            run_planner(story_text)

        with st.spinner("Generating images..."):
            generate_images()

        with st.spinner("Generating audio..."):
            generate_audio()

        with st.spinner("Generating scene videos..."):
            generate_scene_videos()

        with st.spinner("Stitching final video..."):
            final_path = stitch_final_video()

        st.success("🎉 Video generated successfully!")
        st.write(f"✔ {final_path}")
