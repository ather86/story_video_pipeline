"""
Planner Agent Module (v3 - LLM-Driven)
--------------------------------------------------------

Responsibility:
- Use an LLM to break down a story into a structured scene manifest.
- The agent decides the number of scenes, narration, visuals, emotion, and importance.
"""

from pathlib import Path
import json
from pipeline.llm_character_extractor import extract_characters
from src.utils.ollama_client import call_ollama

SCHEMA_PATH = Path("schemas/scene_manifest.json")


def _create_planner_prompt(story_text: str, characters: list, language: str) -> str:
    """Creates the prompt for the Planner Agent."""
    # Convert characters to a string for the prompt
    characters_json_string = json.dumps(characters, indent=2)

    return f"""You are a film director's assistant responsible for breaking down a story into a sequence of visual scenes for a short video.

Your task is to analyze the following story and output a structured JSON object representing the scenes.

Story:
---
{story_text}
---

You have also been provided with a list of characters identified in the story. When a character is present in a scene, you MUST include their `character_id` in the `characters_present` field for that scene.

Available Characters:
---
{characters_json_string}
---

Follow these rules precisely:
0.  **Language Rules**:
    - The `narration` field MUST be in **{language}**. If the input is Romanized, the narration must also be Romanized.
    - All fields related to visual descriptions (`environment`, `key_objects`, `action`) MUST be in **English** for the image generation model.
1.  **Scene Breakdown**: Divide the story into a logical sequence of scenes. It is critical that you cover the entire text and do not omit any parts of the story.
2.  **Narration**: For each scene, provide the exact narration text in **{language}**.
3.  **Visuals**: For each scene, describe the key visual elements in **English**.
    -   `environment`: The setting (e.g., "a dusty library", "a futuristic city at night").
    -   `key_objects`: A list of important objects in the scene.
    -   `action`: A brief description of the main action occurring.
4.  **Characters Present**: Identify which characters from the "Available Characters" list are in the scene. Use their `character_id`.
5.  **Emotion:** Describe the primary emotion or mood of the scene in one or two words (e.g., "mysterious", "urgent", "optimistic").
6.  **Importance:** Rate the scene's importance to the overall story on a scale of "low", "medium", or "high". High-importance scenes are crucial plot points.
7.  **Negative Keywords**: Provide a list of keywords to AVOID for this scene to prevent misinterpretation. For a fantasy scene, you might add ["modern", "car", "computer"]. For a scene with an animal, you might add ["human", "person"].

Produce a single, valid JSON object with a root key "scenes". Each item in the "scenes" list must contain:
-   `scene_id`: An integer, starting from 1.
-   `narration`: The text for the voiceover for this scene.
-   `visuals`: A JSON object with `environment`, `key_objects` (list of strings), and `action`.
-   `characters_present`: A list of character_ids (e.g., ["thirsty_crow"]) from the provided character list who are present in this scene.
-   `emotion`: A string describing the mood.
-   `importance`: A string ("low", "medium", "high").
-   `negative_prompt_keywords`: A list of strings.

Example of a single scene object:
{{
    "scene_id": 1,
    "narration": "In a quiet village, lived a young woman named Elara.",
    "visuals": {{
        "environment": "a peaceful, rustic village square",
        "key_objects": ["thatched-roof cottages", "a central well"],
        "action": "Establishing shot of the village, calm and serene."
    }},
    "characters_present": ["elara"],
    "emotion": "peaceful",
    "importance": "low",
    "negative_prompt_keywords": ["modern clothing", "technology"]
}}

Now, analyze the story and provide the complete JSON output.
"""


def plan_story_to_scenes(story_text: str, language: str = "English", ethnicity_hint: str = "Automatic (from story)") -> dict:
    """
    Uses an LLM agent to plan the story into a structured scene manifest.
    """
    # 1. Extract characters first, as they are a separate concern.
    characters = extract_characters(story_text)

    # --- NEW: Apply ethnicity hint from UI ---
    # If the user selected a specific ethnicity, override what the LLM found.
    if ethnicity_hint and ethnicity_hint.lower() != "automatic (from story)":
        print(f"[PLANNER] Overriding character ethnicity with UI hint: '{ethnicity_hint}'")
        for char in characters:
            # Only apply to characters that are likely people/humanoids to avoid affecting animals/objects.
            if any(term in char.get("description", "").lower() for term in ["person", "man", "woman", "boy", "girl"]):
                 char["ethnicity"] = ethnicity_hint

    # 2. Use the Planner Agent to break the story into scenes.
    print("[PLANNER AGENT] Planning story into scenes...")
    planner_prompt = _create_planner_prompt(story_text, characters, language) # Pass the (potentially modified) characters
    
    try:
        # This call can raise ConnectionError or ValueError
        llm_planned_scenes = call_ollama(planner_prompt, format='json').get("scenes", [])
        if not llm_planned_scenes:
            raise ValueError("LLM planner returned no scenes.")
        print(f"[PLANNER AGENT] ✓ Successfully planned {len(llm_planned_scenes)} scenes.")
    except (ConnectionError, ValueError) as e:
        print(f"[PLANNER AGENT][ERROR] Failed to plan scenes with LLM: {e}")
        print("[PLANNER AGENT] Aborting pipeline run.")
        # In a UI context, this exception should be caught and displayed.
        raise e

    # 3. Assemble the final scene_manifest.json
    scene_count = len(llm_planned_scenes)


    if scene_count == 0:
        raise ValueError("Story text produced zero scenes.")

    # Set a fixed duration per scene to ensure each part has enough time.
    scene_duration = 4  # seconds per scene
    total_duration = scene_count * scene_duration

    scene_manifest = {
        "video_meta": {
            "title": "AI Agent Story to Video",
            "platform": "linkedin",
            "aspect_ratio": "1:1",
            "total_duration_sec": total_duration,
        },
        "global_style": {
            "visual_style": "clean digital illustration",
            "color_palette": "neutral tones",
            "lighting": "soft ambient",
            "camera_language": "stable framing",
        },
        "characters": characters,
        "scenes": [],
    }

    for idx, planned_scene in enumerate(llm_planned_scenes):
        # The LLM now directly provides the characters present in the scene.
        characters_in_scene = planned_scene.get("characters_present", [])
        narration_text = planned_scene.get("narration", "")
        visuals = planned_scene.get("visuals", {})

        scene_manifest["scenes"].append({
            "scene_id": idx + 1,
            "duration_sec": scene_duration,
            "visual": {
                "environment": visuals.get("environment", ""),
                "characters_present": characters_in_scene,
                "key_objects": visuals.get("key_objects", []),
                "action": visuals.get("action", ""),
                "camera": "static shot", # Keep this simple for now
            },
            "emotion": planned_scene.get("emotion", ""),
            "importance": planned_scene.get("importance", "medium"), # NEW
            "negative_prompt_keywords": planned_scene.get("negative_prompt_keywords", []),
            "narration": {
                "text": narration_text,
                "voice": "male", # This can be refined later
                "pace": "normal",
            },
        })

    return scene_manifest


def write_scene_manifest(scene_manifest: dict):
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(scene_manifest, f, indent=2, ensure_ascii=False)


def run_planner(story_text: str, language: str = "English", ethnicity_hint: str = "Automatic (from story)"):
    """
    Public entry point used by Streamlit.
    """
    scene_manifest = plan_story_to_scenes(story_text, language=language, ethnicity_hint=ethnicity_hint)
    write_scene_manifest(scene_manifest)
    return scene_manifest
