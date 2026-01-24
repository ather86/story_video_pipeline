# 🎬 Story-to-Video Agentic Pipeline

This project is a fully autonomous, 100% local AI agentic system that converts raw text stories into complete, social-media-ready videos. It leverages a suite of local AI models for planning, image generation, audio narration, and video composition, all orchestrated by a user-friendly Streamlit interface.

The entire pipeline runs on your local machine, ensuring complete data privacy. No cloud APIs or external keys are required.

*(Here is a great place to add a GIF of the UI in action!)*

---

## ✨ Features

- **🤖 Agentic Architecture:** The system is not a linear script but a team of collaborating AI agents:
  - **Planner Agent:** Reads the story and creates a detailed scene-by-scene plan.
  - **Tool Router:** Intelligently selects high-quality or high-speed workflows based on scene importance.
  - **Critic Agent:** In autonomous mode, analyzes failures and decides whether to retry or modify its approach.
- **🔒 100% Local & Private:** All models run on your machine. Your stories and generated content never leave your computer.
  - **LLM:** `Ollama` (e.g., Llama 3) for planning, analysis, and transliteration.
  - **Image Generation:** `ComfyUI` with Stable Diffusion for visuals.
  - **Audio Generation:** `Coqui TTS` for high-quality, multi-speaker narration.
- **🌐 Multilingual & Multicultural Control:**
  - **Language Support:** Generate videos in English or Hindi.
  - **Flexible Input:** Supports both Devanagari (`नमस्ते`) and Romanized Hindi (`namaste`) input, with AI-powered transliteration for the highest quality audio.
  - **Ethnicity Control:** An explicit UI dropdown allows you to guide character appearance (e.g., Indian, European, East Asian) to match the story's context.
- **⚙️ Autonomous Mode:**
  - **Manual Mode:** Stops on the first error for easy debugging.
  - **Autonomous Mode:** Enables the Critic Agent to attempt retries and overcome transient errors without human intervention.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **UI & Orchestration** | Streamlit | User interface and central agent controller. |
| **LLM Backend** | Ollama | Powers the Planner, Critic, and Transliteration agents. |
| **Image Generation** | ComfyUI | Generates scene visuals via Stable Diffusion workflows. |
| **Audio Generation** | Coqui TTS (XTTS-v2) | Synthesizes narration and character voices. |
| **Video Processing** | FFmpeg | Animates images, composites audio, and stitches scenes. |
| **Core Language** | Python 3.10+ | The backbone of the entire application. |

---

## 🚀 Getting Started

### 1. Prerequisites

Before you begin, ensure you have the following services installed and running:

- **Python 3.10+**
- **FFmpeg:** Make sure it's installed and accessible in your system's PATH.
- **Ollama:**
  - Install Ollama.
  - Pull the model specified in `config.py` (default is Llama 3):
    ```bash
    ollama pull llama3
    ```
- **ComfyUI:**
  - It is recommended to use StabilityMatrix to install and manage ComfyUI.
  - Ensure the ComfyUI server is running on `http://127.0.0.1:8188`.

### 2. Installation

Clone the repository and install the required Python packages.

```bash
# Clone the repo
git clone <your-repo-url>
cd story-video-pipeline

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

The pipeline relies on ComfyUI's default input and output directories. If you have a custom setup, you can configure these paths by setting the following environment variables:

```bash
export COMFY_OUTPUT_DIR="/path/to/your/ComfyUI/output"
export COMFY_INPUT_DIR="/path/to/your/ComfyUI/input"
```

### 4. Running the Application

Launch the Streamlit web application from the project root directory:

```bash
streamlit run app.py
```

This will open the UI in your web browser. Paste your story, configure the settings in the sidebar, and click "🚀 Run Agentic Pipeline" to start the process.

---

## 📂 Project Structure

```
story-video-pipeline/
├── comfy/                 # ComfyUI workflow templates (.json)
├── outputs/               # Generated images, audio, and videos
├── pipeline/              # Core agent modules (planner, audio_gen, etc.)
├── schemas/               # The `scene_manifest.json` schema and output
├── src/                   # Reusable utilities and adapters
│   ├── image_generation/
│   ├── prompts/
│   └── utils/
├── app.py                 # The main Streamlit application UI and controller
├── config.py              # Central configuration (e.g., Ollama model name)
├── requirements.txt       # Python dependencies
└── README.md              # You are here!
```

---

## 🧪 Testing

The project includes several test scripts to validate individual components of the pipeline:

- **Full End-to-End Test:**
  ```bash
  python test_pipeline.py
  ```
- **Ollama Connectivity Test:**
  ```bash
  python test_ollama.py
  ```
- **ComfyUI API Test:**
  ```bash
  python test_comfy_api.py
  ```