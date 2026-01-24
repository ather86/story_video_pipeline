import streamlit as st
from pathlib import Path
import json
import time

from src.utils.run_id import generate_run_id
from src.utils.ollama_client import call_ollama # For critic agent
from src.utils.text_sanitizer import sanitize_text

# PIPELINE IMPORTS
from pipeline.planner import run_planner
from src.image_generation.comfy_t2i import run_comfy_api_workflow
from src.prompts.prompt_builder import build_image_prompt
from pipeline.audio_gen import generate_audio, load_tts
from pipeline.animation import animate_and_composite_scenes
from pipeline.stitcher import stitch_final_video


# --- AGENT CONFIG ---
MAX_RETRIES = 2

st.set_page_config(page_title="Story → Video Agent", layout="wide")

st.title("🎬 Story → Video Agent")
st.write("An agentic system to convert a story into a structured video using local LLMs.")

# --- UI Configuration ---
with st.sidebar:
    st.header("⚙️ Agent & Pipeline Settings")

    # --- NEW: Agent Autonomy Toggle ---
    agent_autonomy_mode = st.toggle(
        "🤖 Agent Autonomy Mode",
        value=False,
        help="**OFF:** Manual Mode. The pipeline stops on the first error. \n\n**ON:** Autonomous Mode. The agent will attempt to reason about failures and retry up to a limit."
    )

    # --- NEW: Model/Style Selection (now a Tool Router hint) ---
    st.write("The agent will try to select the best style, but you can provide a hint for high-importance scenes.")
    MODEL_STYLES = {
        "Storybook Illustration (Default)": "comfy/workflows/image_netayume_lumina_t2i_api.json",
        "Anime Style (High Quality)": "comfy/workflows/anime_style_api.json",
        "Photorealistic (High Quality)": "comfy/workflows/photorealistic_style_api.json",
    }
    selected_style_name = st.selectbox(
        "🎨 Preferred High-Quality Style",
        options=list(MODEL_STYLES.keys())
    )
    # This is now a suggestion, the agent can override it.
    preferred_workflow_path = MODEL_STYLES[selected_style_name]

    st.divider()

    # --- NEW: Character Ethnicity Control ---
    st.header("👥 Character Settings")
    selected_ethnicity = st.selectbox(
        "🌍 Character Ethnicity",
        options=["Automatic (from story)", "Indian", "East Asian", "European", "African", "Middle Eastern", "Latin American"],
        index=0,
        help="Guide the appearance of characters. 'Automatic' lets the AI decide from the story context."
    )

    st.divider()

    # --- NEW: Voice Selection ---
    st.header("🎙️ Audio Settings")

    @st.cache_resource
    def get_tts_model():
        """Load and cache the TTS model resource."""
        try:
            return load_tts()
        except Exception as e:
            st.error(f"Fatal: Could not load TTS model. Audio generation will be disabled. Error: {e}")
            return None

    tts_model = get_tts_model()
    available_speakers = []
    if tts_model:
        available_speakers = list(tts_model.synthesizer.tts_model.speaker_manager.name_to_id)

    default_narrator = "Claribel Dervla"
    default_index = 0
    if available_speakers and default_narrator in available_speakers:
        default_index = available_speakers.index(default_narrator)

    selected_narrator_voice = st.selectbox(
        "🗣️ Narrator Voice",
        options=available_speakers,
        index=default_index,
        help="Choose the main narrator voice. Character voices are assigned automatically.",
        disabled=not available_speakers
    )

    selected_language_name = st.selectbox(
        "🌐 Language (for Audio & Narration)",
        options=["English", "Hindi"],
        index=0,
        help="Select the language for the narration. If you select Hindi, please provide the story in Hindi for best results."
    )


    skip_images = st.checkbox("⚡ Skip Image Generation", value=False)
    skip_audio = st.checkbox("🔇 Skip Audio Generation", value=False)
    animate_scenes = st.checkbox("✨ Animate Scenes (slow, requires high VRAM)", value=False)

story_text = st.text_area(
    "Enter your story",
    height=250,
    placeholder="Paste your story, LinkedIn post, or idea here..."
)

st.divider()

if st.button("🚀 Run Agentic Pipeline"):
    if not story_text.strip():
        st.warning("Please enter a story.")
        st.stop()

    # --- NEW: Sanitize text at the very beginning ---
    # This prevents issues with special characters (e.g., unicode bold) confusing the LLM planner.
    sanitized_story = sanitize_text(story_text)
    with st.expander("View Sanitized Text (Used by AI)"):
        st.text(sanitized_story)

    run_id = generate_run_id()
    st.info(f"🆔 Run ID: {run_id}")

    # -------------------------------
    # 1️⃣ PLAN SCENES
    # -------------------------------
    with st.spinner("🧠 Planner Agent is breaking down the story..."):
        try:
            # The planner writes the manifest and also returns it.
            manifest = run_planner(sanitized_story, language=selected_language_name, ethnicity_hint=selected_ethnicity)
        except (ConnectionError, ValueError) as e:
            st.error(f"**Planning Agent Failed:** {e}")
            st.error("The pipeline cannot start without a valid plan. Please ensure your Ollama server is running and the model is available.")
            st.stop()

    # We now have the manifest in memory and can pass it directly
    # to subsequent stages, avoiding reliance on the file.
    scenes = manifest["scenes"]
    global_style = manifest["global_style"]
    aspect_ratio = manifest.get("video_meta", {}).get("aspect_ratio", "16:9")
    character_map = {
        c["character_id"]: c for c in manifest.get("characters", [])
    }

    st.success("✅ Story planning complete.")
    with st.expander("📚 View Scene Manifest"):
        st.json(manifest)

    # --- CENTRAL DECISION CONTROLLER ---
    try:
        # -------------------------------
        # 2️⃣ IMAGE GENERATION (with Tool Router & Critic)
        # -------------------------------
        if not skip_images:
            st.subheader("🖼️ Image Generation Stage")
            image_gen_logs = st.container()

            for scene in scenes:
                scene_id = scene["scene_id"]
                
                # --- AGENT LOOP for this scene ---
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        with st.spinner(f"🎨 Generating image for scene {scene_id} (Attempt {attempt + 1})..."):
                            # --- TOOL ROUTER ---
                            importance = scene.get("importance", "medium")
                            if importance == "high":
                                workflow_path = preferred_workflow_path
                                image_gen_logs.info(f"Scene {scene_id} (Importance: High) → Using preferred high-quality workflow: `{workflow_path}`")
                            else:
                                workflow_path = "comfy/workflows/image_netayume_lumina_t2i_api.json"
                                image_gen_logs.info(f"Scene {scene_id} (Importance: {importance}) → Using default workflow: `{workflow_path}`")

                            if not Path(workflow_path).exists():
                                st.warning(f"Workflow file `{workflow_path}` not found. Falling back to default.")
                                workflow_path = "comfy/workflows/image_netayume_lumina_t2i_api.json"

                            prompt = build_image_prompt(scene, global_style, character_map)

                            run_comfy_api_workflow(
                                api_workflow_path=workflow_path,
                                prompts=prompt,
                                run_id=run_id,
                                scene_id=scene_id,
                                aspect_ratio=aspect_ratio
                            )
                        image_gen_logs.success(f"✅ Image for scene {scene_id} generated successfully.")
                        break 

                    except Exception as e:
                        image_gen_logs.error(f"❌ Failed to generate image for scene {scene_id} on attempt {attempt + 1}: {e}")
                        
                        if not agent_autonomy_mode or attempt >= MAX_RETRIES:
                            raise RuntimeError(f"Pipeline stopped. Could not generate image for scene {scene_id} after {attempt + 1} attempts.")
                        
                        # --- CRITIC AGENT (Autonomous Mode) ---
                        with st.spinner(f"🤔 Critic Agent is analyzing the failure for scene {scene_id}..."):
                            critic_prompt = f"""
An image generation task failed for a scene in a story-to-video pipeline.

Scene Details: {json.dumps(scene, indent=2)}
Error Message: {str(e)}

Your task is to decide the next step. You have two choices:
1. "RETRY": Retry the operation with the exact same parameters. This is a good choice for transient errors like network issues or timeouts.
2. "MODIFY": Suggest a change to the scene's visual prompt to fix a potential content issue.

Based on the error, which action is more logical?

Respond with a single JSON object containing:
{{
    "action": "RETRY" or "MODIFY",
    "reasoning": "A brief explanation of your choice.",
    "new_positive_prompt": "If action is MODIFY, provide a new, improved positive prompt here. Otherwise, an empty string."
}}
"""
                            try:
                                decision = call_ollama(critic_prompt, format='json')
                                image_gen_logs.info(f"🕵️ Critic Agent Decision: {decision.get('action')}. Reason: {decision.get('reasoning')}")

                                if decision.get("action") == "MODIFY":
                                    new_prompt_text = decision.get("new_positive_prompt")
                                    if new_prompt_text:
                                        image_gen_logs.warning(f"Critic suggests modifying prompt. For this version, we will just retry. Suggested prompt: {new_prompt_text}")
                                
                            except Exception as critic_e:
                                image_gen_logs.error(f"Critic Agent failed: {critic_e}. Retrying without changes.")
                        
                        time.sleep(3)
        else:
            st.info("⚡ Image generation skipped by user.")

        # -------------------------------
        # 3️⃣ AUDIO GENERATION
        # -------------------------------
        if not skip_audio:
            with st.spinner("🎧 Generating audio..."):
                if tts_model:
                    language_code = "hi" if selected_language_name == "Hindi" else "en"
                    generate_audio(run_id, manifest, tts=tts_model, narrator_voice=selected_narrator_voice, language=language_code)
                    st.success("✅ Audio generation complete.")
                else:
                    st.warning("Audio generation skipped: TTS model could not be loaded.")
        else:
            st.info("🔇 Audio generation skipped")

        # -------------------------------
        # 4️⃣ IMAGE → VIDEO
        # -------------------------------
        spinner_text = "🎞️ Animating scenes..." if animate_scenes else "🎞️ Creating static scene videos..."
        with st.spinner(spinner_text):
            animate_and_composite_scenes(run_id, manifest, animate=animate_scenes)
        st.success("✅ Scene video composition complete.")

        # -------------------------------
        # 5️⃣ STITCH FINAL VIDEO
        # -------------------------------
        with st.spinner("🧩 Stitching final video..."):
            final_path = stitch_final_video(run_id, manifest)
        st.success("✅ Final video stitched.")

        st.balloons()
        st.header("🎉 Pipeline Completed Successfully!", anchor=False)

        # -------------------------------
        # PREVIEW
        # -------------------------------
        if Path(final_path).exists():
            st.video(str(final_path))
            st.download_button(
                "⬇️ Download Final Video",
                data=open(final_path, "rb"),
                file_name=f"{run_id}_final.mp4",
                mime="video/mp4"
            )

    except (RuntimeError, FileNotFoundError, ConnectionError) as e:
        st.error(f"**A critical error occurred in the pipeline:** {e}")
        st.info("The agentic pipeline has been halted. Please check the logs and your service connections (Ollama, ComfyUI).")
        st.stop()
