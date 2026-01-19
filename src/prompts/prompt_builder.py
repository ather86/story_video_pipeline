def build_image_prompt(scene, global_style, character_map):
    """
    Deterministic image prompt builder.
    Converts scene facts into a strong visual-first prompt.
    """

    visual = scene["visual"]

    # Resolve character descriptions from IDs
    characters = ", ".join(
        character_map[c]["description"]
        for c in visual.get("characters_present", [])
        if c in character_map
    )

    objects = ", ".join(visual.get("key_objects", []))
    environment = visual.get("environment", "")
    action = visual.get("action", "")
    emotion = scene.get("emotion", "")

    prompt = f"""
Minimal storybook editorial vector illustration,
{characters} in a {environment},
{action},
clearly visible objects nearby: {objects},
emotion and mood: {emotion},
{global_style['visual_style']},
flat vector style, bold simple shapes,
limited color palette,
clean background, strong focal point,
no text, no letters, no UI elements,
no realistic humans
""".strip()

    return prompt
