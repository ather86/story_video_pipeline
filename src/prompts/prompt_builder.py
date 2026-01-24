"""
Prompt Builder (v2 - Character-Centric)
---------------------------------------
Responsibility:
- Convert scene semantics into a high-quality, character-focused image prompt.
- Prioritize character descriptions to improve consistency.
"""

def build_image_prompt(scene: dict, global_style: dict, character_map: dict) -> dict:
    """
    Builds a positive and negative prompt for a scene, with a strong focus
    on maintaining character consistency.
    """
    visual = scene.get("visual", {})
    characters_present = visual.get("characters_present", [])
    action = visual.get("action", "")
    environment = visual.get("environment", "")
    key_objects = visual.get("key_objects", [])
    emotion = scene.get("emotion", "neutral")
    planner_negatives = scene.get("negative_prompt_keywords", [])

    # --- 1. Subject Block (Character-First) ---
    subject_parts = []
    if characters_present:
        # If characters are in the scene, they are the primary subject.
        character_descriptions = []
        for char_id in characters_present:
            if char_id in character_map:
                # Use the detailed description from the character map.
                character = character_map[char_id]
                description = character["description"]
                ethnicity = character.get("ethnicity")

                # Prepend ethnicity to the description if it's specified and not 'unspecified'
                if ethnicity and ethnicity.lower() not in ["unspecified", "none", ""]:
                    # Make the description lowercase before prepending to avoid "An Indian A young woman..."
                    description = f"An {ethnicity} {description.lower()}"
                
                character_descriptions.append(description)

        if character_descriptions:
            # Combine character descriptions with the action they are performing.
            full_subject = ", ".join(character_descriptions)
            if action:
                full_subject += f", {action}"
            subject_parts.append(full_subject)
        elif action:
            # Fallback if character is listed but not in map
            subject_parts.append(action)
    elif action:
        # If no characters, the action is the subject.
        subject_parts.append(action)

    # --- 2. Context Block (Environment & Objects) ---
    context_parts = []
    if environment:
        context_parts.append(f"in {environment}")
    if key_objects:
        context_parts.append(f"with {', '.join(key_objects)}")
    
    # --- 3. Style & Composition Block ---
    style_block = f"{global_style.get('visual_style', 'cinematic illustration')}, mood of {emotion}, {global_style.get('color_palette', 'vibrant colors')}, {global_style.get('lighting', 'dramatic lighting')}"
    composition_block = "wide shot, clear subject, rule of thirds, beautiful composition"

    # --- 4. Assemble the Positive Prompt ---
    final_prompt_parts = [p for p in [", ".join(subject_parts), " ".join(context_parts)] if p]
    positive_prompt = ". ".join(final_prompt_parts) + f". {style_block}. {composition_block}."
    
    # --- 5. Negative Prompt ---
    # Base quality negatives that are almost always useful.
    quality_negatives = [
        "ugly", "tiling", "poorly drawn hands", "poorly drawn feet", "poorly drawn face",
        "out of frame", "extra limbs", "disfigured", "deformed", "body out of frame",
        "blurry", "bad anatomy", "blurred", "watermark", "grainy", "signature", "cut off", "draft"
    ]

    # Text is usually unwanted in generated images.
    text_negatives = ["text", "letters", "words", "speech bubble", "font", "typography"]

    # Dynamically add negatives for humans if no human characters are in the story.
    # This helps prevent the model from adding people to scenes with only animals or objects.
    human_negatives = []
    is_human_present = any(
        any(term in char.get("description", "").lower() for term in ["human", "person", "man", "woman", "boy", "girl"])
        for char in character_map.values()
    )
    if not is_human_present and character_map: # Only add if characters are defined and none are human
        human_negatives = ["human", "person", "kid", "boy", "girl", "man", "woman", "people"]

    # Combine all parts, using a set to remove duplicates, then join.
    all_negative_parts = set(quality_negatives + text_negatives + human_negatives + planner_negatives)
    negative_prompt = ", ".join(sorted(list(all_negative_parts)))

    return {"positive": positive_prompt, "negative": negative_prompt}