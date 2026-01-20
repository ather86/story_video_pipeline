"""
Planner Module (v2 - Semantics Only, Architecture-Clean)
--------------------------------------------------------

Responsibility:
- Convert raw story text into a structured scene_manifest.json
- Store ONLY story facts and semantics
- NO image / model / prompt / seed leakage
"""

from pathlib import Path
import json
import re
from pipeline.llm_character_extractor import extract_characters


SCHEMA_PATH = Path("schemas/scene_manifest.json")


def plan_story_to_scenes(story_text: str) -> dict:
    """
    Simple rule-based planner (v2).
    - One sentence = one scene
    - Semantics ONLY
    """

    # --- Character Extraction (Simulated LLM) ---
    # This is the new step to extract character data.
    characters = extract_characters(story_text)


    # Normalize whitespace (e.g., newlines, tabs) to a single space
    normalized_text = re.sub(r'\s+', ' ', story_text).strip()

    # Split by punctuation (.?!) followed by whitespace, avoiding common abbreviations
    # We require the next character to be Uppercase to avoid splitting on "v1.5", "approx. 10", etc.
    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+(?=[A-Z])', normalized_text) if s.strip()]
    scene_count = len(sentences)

    if scene_count == 0:
        raise ValueError("Story text produced zero scenes.")

    # Make duration robust for any number of scenes.
    # Each scene gets at least 1s, and the total duration is recalculated.
    scene_duration = max(1, 25 // scene_count)
    total_duration = scene_count * scene_duration

    scene_manifest = {
        "video_meta": {
            "title": "Story to Video",
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
        # NOTE: Character and scene details are now placeholders.
        # A more advanced NLP/LLM step is needed to extract these from the story.
        "characters": characters,
        "scenes": [],
    }

    for idx, sentence in enumerate(sentences):
        characters_in_scene = []
        for char in characters:
            # Simple name check (case-insensitive)
            if char["name"].lower() in sentence.lower():
                characters_in_scene.append(char["character_id"])

        scene_manifest["scenes"].append({
            "scene_id": idx + 1,
            "duration_sec": scene_duration,
            "visual": {
                "environment": "",  # Placeholder - to be extracted from sentence
                "characters_present": characters_in_scene,
                "key_objects": [],  # Placeholder - to be extracted
                "action": "",  # Placeholder - to be extracted
                "camera": "static shot",
            },
            "emotion": "",  # Placeholder - to be extracted
            "narration": {
                "text": sentences[idx],
                "voice": "male",
                "pace": "normal",
            },
        })

    return scene_manifest


def write_scene_manifest(scene_manifest: dict):
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(scene_manifest, f, indent=2, ensure_ascii=False)


def run_planner(story_text: str):
    """
    Public entry point used by Streamlit.
    """
    scene_manifest = plan_story_to_scenes(story_text)
    write_scene_manifest(scene_manifest)
    return scene_manifest
