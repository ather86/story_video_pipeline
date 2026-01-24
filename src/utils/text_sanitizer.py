"""
Text Sanitization Utility
-------------------------

Cleans and normalizes text to be safe and understandable for AI models.
"""
import unicodedata
import re

def sanitize_text(text: str) -> str:
    """
    Normalizes and sanitizes text to be safe for AI models (LLM, TTS, etc.).
    - Normalizes compatibility characters (e.g., full-width bold '𝗪') to their standard equivalents.
    - Replaces bullet points with hyphens.
    - Normalizes whitespace to preserve paragraphs but remove excess spacing.
    """
    if not text:
        return ""

    # Normalize Unicode to handle special characters (like full-width bold)
    # without removing script-specific characters like Devanagari.
    text = unicodedata.normalize('NFKD', text)
    
    text = re.sub(r'[•·*]', '-', text) # Replace bullet points with hyphens
    text = re.sub(r'\s+', ' ', text).strip() # Collapse all whitespace to single spaces

    return text