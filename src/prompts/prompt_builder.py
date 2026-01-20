def build_image_prompt(scene, global_style, character_map) -> dict:
    """
    Deterministic image prompt builder (v5).
    Separates positive and negative prompts and uses advanced techniques
    for character consistency and image quality.
    """
    # --- POSITIVE PROMPT ---
    positive_parts = [
        # Core style and medium
        "Minimal storybook editorial vector illustration",
        global_style.get("visual_style", "clean digital illustration"),
        "flat vector style",
        "bold simple shapes",
        "limited color palette",
        "strong focal point",
        "clean background",
    ]

    visual = scene.get("visual", {})
    narration_text = scene.get("narration", {}).get("text", "")
    characters_present = visual.get("characters_present", [])

    # 1. Character Block - very specific for consistency
    character_prompts = []
    if characters_present:
        for char_id in characters_present:
            if char_id in character_map:
                char_data = character_map[char_id]
                # Using names and weighted descriptions for better binding
                character_prompts.append(f"({char_data['name']}: {char_data['description']})")
    if character_prompts:
        positive_parts.append(", ".join(character_prompts))

    # 2. Narration as context for action
    if narration_text:
        positive_parts.append(narration_text)

    # 3. Environment Block
    if visual.get("environment"):
        positive_parts.append(f"in a {visual['environment']}")

    # 4. Emotion Block
    if scene.get("emotion"):
        positive_parts.append(f"emotion and mood: {scene['emotion']}")

    # --- NEGATIVE PROMPT ---
    negative_parts = [
        # For text issue
        "text", "letters", "words", "font", "signature", "watermark", "UI elements",
        # For incomplete image issue
        "cropped", "cut off", "out of frame", "blurry", "grainy", "pixelated",
        # General quality
        "ugly", "disfigured", "deformed", "bad anatomy", "extra limbs", "tiling",
        # To enforce the style
        "photorealistic", "realistic", "3d render", "photo", "photography", "realistic humans",
    ]

    # Assemble and return
    return {
        "positive": ", ".join(filter(None, positive_parts)),
        "negative": ", ".join(filter(None, negative_parts)),
    }
