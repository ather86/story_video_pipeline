"""
Dedicated test script for Ollama connectivity.
"""
import json
from pipeline.llm_character_extractor import extract_characters

# Use the same story as the main pipeline test for consistency.
STORY = """
In a quiet village, lived a young woman named Elara, known for her vibrant, curly red hair and the emerald green cloak she never took off. One day, a mysterious old man, Ronan, arrived. Ronan had a long, silver beard that reached his waist and carried a gnarled oak staff. Elara, curious, approached him by the village well. Ronan smiled, his eyes twinkling, and he told her a story of a hidden treasure.
"""

def test_ollama_call():
    """
    Calls the character extractor and prints the raw output.
    """
    print("🚀 Testing Ollama character extraction...")
    try:
        characters = extract_characters(STORY)
        print("\n✅ Ollama call successful! Extracted data:")
        print(json.dumps(characters, indent=2))
    except Exception as e:
        print(f"\n❌ An error occurred during the test: {e}")

if __name__ == "__main__":
    test_ollama_call()