"""
Central configuration for the Story Video Pipeline.
"""

# --- LLM Configuration ---
# The Ollama client library will connect to http://localhost:11434 by default.
# You can override this by setting the OLLAMA_HOST environment variable.

# The model to use for character extraction
# Make sure you have pulled this model with `ollama pull <model_name>`
OLLAMA_MODEL = "llama3"