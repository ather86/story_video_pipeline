"""
Planner Module
---------------

Responsibility:
- Convert raw story text into a structured scene_manifest.json
"""

from pathlib import Path
import json


SCHEMA_PATH = Path("schemas/scene_manifest.json")


def plan_story_to_scenes(story_text: str) -> dict:
    """
    Simple rule-based planner (v1).
    One sentence = one scene (max 5).
    """

    sentences = [s.strip() for s in story_text.split(".") if s.strip()]
    scene_count = min(len(sentences), 5)

    total_duration = 25
    scene_duration = total_duration // scene_count

    scene_manifest = {
        "video_meta": {
            "title": "Story to Video",
            "platform": "linkedin",
            "aspect_ratio": "1:1",
            "total_duration_sec": total_duration,
            "style_preset": "minimal"
        },
        "global_style": {
            "visual_style": "clean digital illustration",
            "color_palette": "neutral tones",
            "lighting": "soft ambient",
            "camera_language": "stable framing"
        },
        "characters": [
            {
                "id": "char_1",
                "description": "person working on a laptop",
                "clothing": "casual clothes",
                "age_range": "30-40",
                "consistency_notes": "same person in all scenes"
            }
        ],
        "scenes": []
    }

    for idx in range(scene_count):
        scene_manifest["scenes"].append({
            "scene_id": idx + 1,
            "duration_sec": scene_duration,
            "visual": {
                "environment": "home workspace",
                "characters_present": ["char_1"],
                "key_objects": "laptop",
                "action": "person reflecting",
                "camera": "static shot"
            },
            "emotion": "neutral",
            "narration": {
                "text": sentences[idx],
                "voice": "male",
                "pace": "normal"
            },
            "image_generation": {
                "prompt": f"person working on laptop, {sentences[idx]}, clean digital illustration",
                "negative_prompt": "blurry, distorted, low quality",
                "seed": 12345
            }
        })

    return scene_manifest


def write_scene_manifest(scene_manifest: dict):
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(scene_manifest, f, indent=2)


def run_planner(story_text: str):
    """
    Public entry point used by Streamlit.
    """
    scene_manifest = plan_story_to_scenes(story_text)
    write_scene_manifest(scene_manifest)
