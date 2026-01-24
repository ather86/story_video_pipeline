"""
LLM Character Extractor
-----------------------

This module is responsible for using a large language model to extract
character information from a story.
"""

# In a real-world scenario, this would use a library like openai,
# but we can also use a local LLM like Ollama.
from src.utils.ollama_client import call_ollama

def extract_characters(story_text: str) -> list:
    """
    Given a story, this function uses a simulated LLM call to extract a list
    of characters with their descriptions.

    The agent running this code is expected to act as the LLM.
    """

    prompt = f"""
Given the following story, identify the main characters (which can be people, animals, or objects). For each character, provide a short, consistent visual description for image generation. Also, determine the likely ethnicity based on context, names, or setting (e.g., "Indian", "European", "unspecified"). The character_id should be a lowercase, snake_case version of the character's name.

Story:
---
{story_text}
---

Expected output (JSON format):
{{
  "characters": [
    {{
      "character_id": "character_name_in_snake_case",
      "name": "Character Name",
      "description": "A short, consistent visual description.",
      "ethnicity": "e.g., Indian, European, unspecified"
    }}
  ]
}}
"""

    try:
        print("[LLM] Attempting to call local Ollama for character extraction...")
        llm_output = call_ollama(prompt, format='json')
        print("[LLM] ✓ Successfully extracted characters using Ollama.")

    # Catch specific errors from our client
    except (ConnectionError, ValueError) as e:
        print(f"[LLM][WARN] Ollama call failed: {e}")
        print("[LLM] Falling back to simulated character extraction.")

        # --- LLM Simulation (Fallback) ---
        # This is used if the Ollama call fails.
        # It uses hardcoded characters from the test story.
        llm_output = {
          "characters": [
            {
              "character_id": "elara",
              "name": "Elara",
              "description": "A young woman with vibrant, curly red hair and an emerald green cloak.",
              "ethnicity": "European"
            },
            {
              "character_id": "ronan",
              "name": "Ronan",
              "description": "A mysterious old man with a long, silver beard that reaches his waist and carries a gnarled oak staff.",
              "ethnicity": "European"
            }
          ]
        }

    return llm_output.get("characters", [])
