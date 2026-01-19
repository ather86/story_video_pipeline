"""
PromptCompiler
---------------
Responsibility:
- Convert scene meaning into a Comfy-optimized image prompt
- Enforce visual consistency and constraints
- NO image generation here
"""

class PromptCompiler:
    @staticmethod
    def compile(scene, global_style, characters):
        """
        Input:
          - scene: one scene dict from scene_manifest.json
          - global_style: global_style block
          - characters: list of character definitions

        Output:
          - string prompt (Comfy-friendly)
        """

        # ---------- STYLE BLOCK (constant) ----------
        style_block = (
            "Minimal editorial illustration, flat vector style, "
            "storybook illustration mood, clean background, "
            "soft shapes, limited color palette, high contrast, "
            "single clear visual metaphor, consistent lighting"
        )

        # ---------- SUBJECT BLOCK ----------
        visual = scene.get("visual", {})
        environment = visual.get("environment", "")
        action = visual.get("action", "")
        key_objects = visual.get("key_objects", "")

        subject_parts = []
        if environment:
            subject_parts.append(f"set in a {environment}")
        if action:
            subject_parts.append(action)
        if key_objects:
            subject_parts.append(f"featuring {key_objects}")

        subject_block = ", ".join(subject_parts)

        # ---------- GLOBAL STYLE HINTS ----------
        style_hints = []
        if global_style.get("visual_style"):
            style_hints.append(global_style["visual_style"])
        if global_style.get("lighting"):
            style_hints.append(global_style["lighting"])
        if global_style.get("color_palette"):
            style_hints.append(global_style["color_palette"])

        style_hint_block = ", ".join(style_hints)

        # ---------- CONSTRAINT BLOCK ----------
        constraint_block = (
            "no text, no letters, no UI elements, "
            "no realistic humans, no background clutter, "
            "strong focal point"
        )

        # ---------- FINAL PROMPT ----------
        prompt = (
            f"{style_block}, "
            f"{subject_block}, "
            f"{style_hint_block}, "
            f"{constraint_block}"
        )

        return prompt
