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
import wave
from pathlib import Path
from TTS.api import TTS


SCENE_PATH = Path("schemas/scene_manifest.json")
OUTPUT_DIR = Path("outputs/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


# ---------- TEXT SAFETY ----------

def sanitize_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "“": "",
        "”": "",
        "‘": "",
        "’": "",
        "—": " ",
        "–": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


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


def generate_audio(run_id: str):
    """
    Generates narration audio per scene.
    Output files are isolated per run_id.
    """

    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    characters = manifest.get("characters", [])
    scenes = manifest.get("scenes", [])
    tts = load_tts()

    # --- Speaker Setup ---
    # The .speakers attribute is bugged in some versions of TTS.
    # Accessing the speaker names via the synthesizer is more reliable.
    # The .speaker_names property can also be bugged, so we access the underlying dict keys directly.
    available_speakers = list(tts.synthesizer.tts_model.speaker_manager.name_to_id)
    print(f"🎤 Available Speakers: {available_speakers}")

    if not available_speakers:
        raise RuntimeError("No speakers found for the TTS model.")

    # Assign a default narrator voice and unique voices to each character.
    narrator_voice = available_speakers[0]
    character_voice_map = {}

    # Start assigning from the second speaker to keep the first for the narrator
    voice_idx = 1
    for char in characters:
        char_id = char["character_id"]
        if voice_idx < len(available_speakers):
            character_voice_map[char_id] = available_speakers[voice_idx]
            voice_idx += 1
        else:
            # If we run out of unique speakers, reuse the narrator's voice
            character_voice_map[char_id] = narrator_voice

    print(f"   -> Default Narrator Voice: {narrator_voice}")
    for char_id, voice in character_voice_map.items():
        print(f"   -> Voice for '{char_id}': {voice}")

    for scene in scenes:
        scene_id = scene["scene_id"]
        raw_text = scene["narration"]["text"]

        text = sanitize_text(raw_text)
        if not text:
            print(f"[TTS] Scene {scene_id} skipped (empty text)")
            continue

        text = ensure_min_length(text)

        output_path = OUTPUT_DIR / f"{run_id}_scene_{scene_id}.wav"

        print(f"[TTS] Generating audio for scene {scene_id}...")
        print(f"     Text → {text}")

        # Determine which speaker to use for this scene
        speaker_to_use = narrator_voice
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
            language="en",
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
                language="en",
                split_sentences=False,
            )

            if not wav_has_audio(output_path):
                raise RuntimeError(
                    f"TTS failed for scene {scene_id}: WAV still silent"
                )

    return len(scenes)
