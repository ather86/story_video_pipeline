"""
Audio Generation Module (v7 - XTTS-v2 Multi-Speaker)
--------------------------------------------------------------

Upgrades:
- Using XTTS-v2 for multi-speaker, high-quality voice generation.
- Foundational changes for upcoming character voice mapping.

Fixes:
✔ Smart quotes crash
✔ Empty sentence crash
✔ Short kernel crash
✔ Silence-trim destroying audio
✔ Blank WAV detection + auto-recovery
✔ Run-aware output isolation
"""

import json
import re
import unicodedata
import wave
from pathlib import Path
from TTS.api import TTS
from src.utils.ollama_client import call_ollama_text


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

# --- NEW: Voice Configuration ---
# Define preferred voices here. These names must match the available speakers from the model.
VOICE_CONFIG = {
    "narrator": "Claribel Dervla",
    "character_voices": [
        # Female
        "Daisy Studious", "Gracie Wise", "Tammie Ema", "Alison Dietlinde",
        "Gitta Nikolina", "Helena Waldeck",
        # Male
        "Andrew Chipper", "Badr Odhiambo", "Dionisio Schuyler", "Royston Min",
        "Viktor Eka", "Sumesh Kumar" # Adding more diverse names
    ]
}


# ---------- HELPERS ----------

def _is_mostly_ascii(text: str) -> bool:
    """
    Checks if a string is composed predominantly of ASCII characters,
    which helps identify Romanized text.
    """
    if not text:
        return False
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    return (ascii_chars / len(text)) > 0.9

def _transliterate_to_devanagari(text: str) -> str:
    """Uses an LLM to transliterate Romanized Hindi to Devanagari script."""
    prompt = f"""
You are an expert transliteration tool. Your task is to convert the following Romanized Hindi text into its proper Devanagari script.
- Do not translate the meaning.
- Preserve punctuation like commas and periods.
- Return only the final Devanagari text as a single, raw string.

Romanized Text: "{text}"

Devanagari Output:
"""
    return call_ollama_text(prompt)

def ensure_min_length(text: str) -> str:
    """
    Ensures text is long enough for the TTS model to avoid errors.
    Repeats the text if it's too short.
    """
    while 0 < len(text) < 20:
        text += " " + text
    return text


# ---------- AUDIO VALIDATION ----------

def wav_has_audio(path: Path) -> bool:
    if not path.exists():
        return False

    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            return frames > 1000   # ~0.05s @ 22050Hz
    except Exception:
        return False


# ---------- TTS ----------

def load_tts():
    # NOTE: gpu=False is set for maximum compatibility. For significantly
    # faster generation on a capable machine with a CUDA-enabled GPU,
    # you can set gpu=True.
    return TTS(
        model_name=MODEL_NAME,
        progress_bar=False,
        gpu=False  # Set to True for GPU acceleration
    )


def generate_audio(run_id: str, manifest: dict, tts: "TTS", narrator_voice: str = None, language: str = "en"):
    """
    Generates narration audio per scene using a provided TTS instance.
    Output files are isolated per run_id.

    Args:
        run_id: The unique identifier for this pipeline run.
        manifest: The scene manifest dictionary.
        tts: An initialized TTS object.
        narrator_voice: The voice to use for the narrator, selected from the UI.
        language: The language code for TTS (e.g., 'en', 'hi').
    """
    characters = manifest.get("characters", [])
    scenes = manifest.get("scenes", [])

    # --- Speaker Setup ---
    # The .speakers attribute is bugged in some versions of TTS.
    # Accessing the speaker names via the synthesizer is more reliable.
    # The .speaker_names property can also be bugged, so we access the underlying dict keys directly.
    available_speakers = list(tts.synthesizer.tts_model.speaker_manager.name_to_id)
    print(f"🎤 Available Speakers: {available_speakers}")

    if not available_speakers:
        raise RuntimeError("No speakers found for the TTS model.")

    # --- NEW: Configurable & Stable Voice Assignment ---
    # Use the voice from the UI if provided, otherwise use the config default.
    default_narrator_voice = narrator_voice or VOICE_CONFIG["narrator"]
    if default_narrator_voice not in available_speakers:
        print(f"[TTS][WARN] Narrator voice '{default_narrator_voice}' not found. Falling back to '{available_speakers[0]}'.")
        narrator_voice_to_use = available_speakers[0]
    else:
        narrator_voice_to_use = default_narrator_voice

    character_voice_map = {}
    # Use a pool of preferred character voices, falling back to all available if none match
    voice_pool = [v for v in VOICE_CONFIG["character_voices"] if v in available_speakers and v != narrator_voice_to_use]
    if not voice_pool:
        voice_pool = [v for v in available_speakers if v != narrator_voice_to_use] or available_speakers

    voice_idx = 0
    for char in characters:
        char_id = char["character_id"]
        # Cycle through the voice pool for deterministic assignment
        character_voice_map[char_id] = voice_pool[voice_idx % len(voice_pool)]
        voice_idx += 1
    print(f"   -> Narrator Voice: {narrator_voice_to_use}")
    for char_id, voice in character_voice_map.items():
        print(f"   -> Voice for '{char_id}': {voice}")

    for scene in scenes:
        scene_id = scene["scene_id"]
        raw_text = scene["narration"]["text"]
        text = raw_text
        if not text:
            print(f"[TTS] Scene {scene_id} skipped (empty text)")
            continue

        # --- NEW: AI-Powered Transliteration Step ---
        if language == "hi" and _is_mostly_ascii(text):
            print(f"[TTS] Romanized Hindi detected for scene {scene_id}. Transliterating to Devanagari...")
            try:
                devanagari_text = _transliterate_to_devanagari(text)
                print(f"     → Original: {text}")
                print(f"     → Transliterated: {devanagari_text}")
                text = devanagari_text
            except Exception as e:
                print(f"[TTS][WARN] Transliteration failed for scene {scene_id}: {e}. Using original Romanized text.")

        text = ensure_min_length(text)

        output_path = OUTPUT_DIR / f"{run_id}_scene_{scene_id}.wav"

        print(f"[TTS] Generating audio for scene {scene_id}...")
        print(f"     Text → {text}")

        # Determine which speaker to use for this scene
        speaker_to_use = narrator_voice_to_use
        characters_in_scene = scene.get("visual", {}).get("characters_present", [])

        # If one character is present, use their voice. Otherwise, use the narrator.
        if len(characters_in_scene) == 1:
            char_id = characters_in_scene[0]
            if char_id in character_voice_map:
                speaker_to_use = character_voice_map[char_id]
                print(f"     Voice → Using voice for '{char_id}': {speaker_to_use}")

        tts.tts_to_file(
            text=text,
            file_path=str(output_path),
            speaker=speaker_to_use,
            language=language,
            split_sentences=False,
        )

        # Validate WAV
        if not wav_has_audio(output_path):
            print(f"[TTS][WARN] Blank audio detected for scene {scene_id}, regenerating...")

            fallback_text = (
                text + " Remember, patience and effort always bring rewards."
            )

            tts.tts_to_file(
                text=fallback_text,
                file_path=str(output_path),
                speaker=speaker_to_use,
                language=language,
                split_sentences=False,
            )

            if not wav_has_audio(output_path):
                raise RuntimeError(
                    f"TTS failed for scene {scene_id}: WAV still silent"
                )

    return len(scenes)
