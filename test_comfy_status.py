import requests
import json

COMFY_URL = "http://127.0.0.1:8188"

# Check if ComfyUI is running
try:
    response = requests.get(f"{COMFY_URL}/system_stats")
    print("ComfyUI System Stats:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"❌ ComfyUI not accessible: {e}")
    exit(1)

# Get execution history
try:
    response = requests.get(f"{COMFY_URL}/history")
    history = response.json()
    print("\nComfyUI Execution History (last 5 jobs):")
    for prompt_id in list(history.keys())[-5:]:
        job = history[prompt_id]
        print(f"  {prompt_id}: {job.get('outputs', {}).keys()}")
except Exception as e:
    print(f"Error getting history: {e}")

# Check queue
try:
    response = requests.get(f"{COMFY_URL}/queue")
    queue = response.json()
    print(f"\nQueue Status: {json.dumps(queue, indent=2)}")
except Exception as e:
    print(f"Error getting queue: {e}")
