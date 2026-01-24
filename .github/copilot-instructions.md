# Story-to-Video Pipeline: AI Coding Agent Guide

## Architecture Overview

**Goal:** Convert a story into a complete video with scenes, AI-generated images, TTS audio, and video composition.

**Five-Stage Pipeline** (see [app.py](../app.py) for orchestration):
1. **Planner** → Parse story into scenes, create `schema_manifest.json`
2. **Image Generation** → ComfyUI text-to-image per scene
3. **Audio Generation** → Tacotron2 TTS per scene narration
4. **Image→Video** → Combine image + audio into scene videos using FFmpeg
5. **Stitcher** → Concatenate all scene videos into final MP4

## Key Files & Patterns

### Semantic/Story Architecture
- [pipeline/planner.py](../pipeline/planner.py): Converts story text to structured `scene_manifest.json` — ONE sentence = ONE scene, max 5 scenes, stores ONLY story facts (no model/seed leakage)
- [schemas/scene_manifest.json](../schemas/scene_manifest.json): Central contract — contains video metadata, global style, character definitions, and per-scene visual/narration/emotion facts
- **Pattern:** Story data flows through schema; each stage reads it deterministically

### Image Generation (ComfyUI Integration)
- [src/image_generation/comfy_t2i.py](../src/image_generation/comfy_t2i.py): Main adapter
  - `run_comfy_api_workflow()`: Submits to ComfyUI HTTP API (`http://127.0.0.1:8188`)
  - **Deterministic seeding:** `_scene_seed(run_id, scene_id)` ensures same story+scene → same image
  - **Run isolation:** Files named `{run_id}_scene_{scene_id}_*.png` prevent cross-run collisions
  - **Workaround:** ComfyUI ignores output_dir in some setups; images are copied from ComfyUI default output to `outputs/images/`
- [src/prompts/prompt_builder.py](../src/prompts/prompt_builder.py): Builds prompts from scene semantic facts only (characters, objects, environment, action, emotion) — visual-first, clean vector style
- [comfy/workflows/image_netayume_lumina_t2i_api.json](../comfy/workflows/image_netayume_lumina_t2i_api.json): Workflow template (Netayume Lumina T2I model)

### Audio Generation
- [pipeline/audio_gen.py](../pipeline/audio_gen.py): Tacotron2 TTS pipeline
  - Sanitizes text (removes smart quotes, non-ASCII, normalizes spaces)
  - Generates one WAV per scene: `{run_id}_scene_{scene_id}.wav` in `outputs/audio/`
  - Model: `tts_models/en/ljspeech/tacotron2-DDC`
  - Bulletproof: Handles empty sentences, short kernels, blank WAV detection + auto-recovery

### Video Composition
- [pipeline/image_to_video.py](../pipeline/image_to_video.py): Image + audio → scene video
  - `wait_for_image()`: Polls for ComfyUI output (180s timeout, searches `{run_id}_scene_{scene_id}_*.png`)
  - FFmpeg: Loops image, syncs to audio duration, outputs `{run_id}_scene_{scene_id}.mp4` to `outputs/videos/`
  - Audio length drives video length (deterministic timing)
- [pipeline/stitcher.py](../pipeline/stitcher.py): Concatenates scene videos
  - FFmpeg `concat` filter (Windows-safe, preserves audio)
  - Final output: `outputs/final/{run_id}_final.mp4`

### Utilities
- [src/utils/run_id.py](../src/utils/run_id.py): `generate_run_id()` creates `run_YYYYMMDD_HHMMSS` — used as isolation key across all stages
- [app.py](../app.py): Streamlit UI; orchestrates entire pipeline with spinner states

## Critical Workflows

### Installation
The project has several Python dependencies. Before running any scripts, make sure you have activated your virtual environment and installed the required packages.

```bash
# From the project root directory
pip install -r requirements.txt
```
You also need to ensure your external services are running:
- ComfyUI server at `http://127.0.0.1:8188`
- Ollama server (if used for character extraction)

### Running the Full Pipeline
```bash
streamlit run app.py
# Enter story → click "Run Full Pipeline"
# Generates run_ID, plans scenes, creates images/audio/videos, stitches
```

### Testing Individual Stages
- `test_image_gen_comfy.py`: Image generation only
- `test_comfy_api.py`: ComfyUI API connectivity
- `test_comfy_status.py`: Check ComfyUI job queue
- `test_prompt_compiler.py`: Prompt builder validation
- `test_stitch.py`: Re-stitch existing run (requires run_ID in code)

### Debugging Workflows
1. **Scenes not created:** Check [pipeline/planner.py](../pipeline/planner.py) — story text must have sentences
2. **Images missing:** Verify ComfyUI running on `127.0.0.1:8188`, check `outputs/images/` for `{run_id}_scene_*` files
3. **Audio issues:** Look for sanitization failures in [pipeline/audio_gen.py](../pipeline/audio_gen.py) — smart quotes/non-ASCII are stripped
4. **Video stitching fails:** Ensure all scene videos exist in `outputs/videos/` with correct naming

## Project Conventions

### Run Isolation
Every stage uses `run_id` in filenames:
- Images: `{run_id}_scene_{scene_id}_*.png`
- Audio: `{run_id}_scene_{scene_id}.wav`
- Videos: `{run_id}_scene_{scene_id}.mp4`
- Final: `{run_id}_final.mp4`
→ **Multiple runs don't collide**; old outputs safe to delete

### Determinism & Reproducibility
- Same story + same scene ID → same image seed (via `_scene_seed()`)
- Scene manifest is the source of truth (no hardcoding values elsewhere)
- Avoid randomness in prompt generation; use scene facts only

### Error Handling
- All modules include bulletproofing (e.g., text sanitization, blank WAV recovery, image polling timeout)
- ComfyUI integration expects manual image copy due to output_dir quirk (noted in code)
- FFmpeg commands use `-y` flag for non-interactive mode

### Directories
- `schemas/` — manifest and config schemas
- `comfy/workflows/` — ComfyUI API workflow templates
- `outputs/{images,audio,videos,final}/` — generated artifacts (clean before major runs)
- `src/` — reusable modules (image_generation, prompts, utils)
- `pipeline/` — orchestration stage modules

## Common Tasks

**Add a new generation stage:** Create `pipeline/{stage_name}.py` with public function taking `run_id: str`, update [app.py](../app.py) with spinner, ensure outputs follow `{run_id}` naming

**Adjust scene duration:** Edit [pipeline/planner.py](../pipeline/planner.py) `total_duration` and `scene_duration` logic (currently 25 sec total / num_scenes)

**Change image model:** Swap [comfy/workflows/](../comfy/workflows/) JSON file, update `API_WORKFLOW` path in [src/image_generation/comfy_t2i.py](../src/image_generation/comfy_t2i.py)

**Modify prompt style:** Update [src/prompts/prompt_builder.py](../src/prompts/prompt_builder.py) `build_image_prompt()` — kept separate from scene facts for reusability

**Debug ComfyUI connectivity:** Run `test_comfy_api.py` to validate HTTP API, check server at `http://127.0.0.1:8188/system_stats`
