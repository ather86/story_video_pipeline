"""
Ollama Client Utility
---------------------

Centralized function for calling a local Ollama model.
Includes error handling for common issues like connection
errors and invalid JSON responses.
"""

import ollama
import json
from config import OLLAMA_MODEL

def call_ollama(prompt: str, format: str = '') -> dict:
    """Calls the local Ollama model and handles potential errors."""
    try:
        print(f"[OLLAMA] Calling model '{OLLAMA_MODEL}'...")
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}], format=format)
        print("[OLLAMA] ✓ Response received.")
        response_content = response['message']['content']
        return json.loads(response_content)
    except ollama.ResponseError as e:
        error_message = f"Ollama API error: {e.error}. Is the Ollama server running and the model '{OLLAMA_MODEL}' pulled?"
        raise ConnectionError(error_message) from e
    except json.JSONDecodeError as e:
        error_message = f"Failed to parse JSON response from Ollama. The model may have returned malformed JSON. Response: {response_content}"
        raise ValueError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred while communicating with Ollama: {e}"
        raise ConnectionError(error_message) from e

def call_ollama_text(prompt: str) -> str:
    """Calls the local Ollama model and returns the raw text response."""
    try:
        print(f"[OLLAMA-TEXT] Calling model '{OLLAMA_MODEL}' for raw text...")
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        print("[OLLAMA-TEXT] ✓ Response received.")
        return response['message']['content'].strip()
    except ollama.ResponseError as e:
        error_message = f"Ollama API error: {e.error}. Is the Ollama server running and the model '{OLLAMA_MODEL}' pulled?"
        raise ConnectionError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred while communicating with Ollama: {e}"
        raise ConnectionError(error_message) from e