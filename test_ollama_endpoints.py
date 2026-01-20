"""
Dedicated test script to diagnose Ollama endpoint availability.
"""
import requests

OLLAMA_HOST = "http://localhost:11434"

print(f"🩺 Diagnosing Ollama connection at {OLLAMA_HOST}...")

# 1. Check the root endpoint
try:
    response = requests.get(OLLAMA_HOST, timeout=5)
    if response.status_code == 200 and "Ollama is running" in response.text:
        print(f"\n✅ [SUCCESS] Connected to Ollama root at {OLLAMA_HOST}.")
        print(f"   Server response: '{response.text.strip()}'")
    else:
        print(f"\n⚠️ [WARNING] Connected to {OLLAMA_HOST}, but response was unexpected.")
        print(f"   Status: {response.status_code}, Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"\n❌ [FAIL] Could not connect to Ollama at {OLLAMA_HOST}.")
    print(f"   Error: {e}")
    print("\n   Troubleshooting:")
    print("   - Is the Ollama application running?")
    print("   - Is it running on a different port? If so, you'll need to update `config.py`.")
    exit()


# Dummy payload for testing endpoints
dummy_payload_generate = {"model": "llama3", "prompt": "test", "stream": False}
dummy_payload_chat = {"model": "llama3", "messages": [{"role": "user", "content": "test"}], "stream": False}

# 2. Check /api/generate
print("\n--------------------------------------------------")
print("🔄 Testing '/api/generate' endpoint...")
try:
    response = requests.post(f"{OLLAMA_HOST}/api/generate", json=dummy_payload_generate, timeout=20)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ [SUCCESS] '/api/generate' endpoint is available and responded.")
    elif response.status_code == 404:
        print("   ❌ [FAIL] '/api/generate' endpoint does NOT exist (404 Not Found).")
    else:
        print(f"   ⚠️ [UNEXPECTED] Received status {response.status_code}. Response: {response.text[:100]}")
except requests.exceptions.RequestException as e:
    print(f"   ❌ [FAIL] Request to '/api/generate' failed: {e}")

# 2b. Check /generate (no /api prefix)
print("\n--------------------------------------------------")
print("🔄 Testing '/generate' endpoint (no /api prefix)...")
try:
    response = requests.post(f"{OLLAMA_HOST}/generate", json=dummy_payload_generate, timeout=20)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ [SUCCESS] '/generate' endpoint is available and responded.")
    elif response.status_code == 404:
        print("   ❌ [FAIL] '/generate' endpoint does NOT exist (404 Not Found).")
    else:
        print(f"   ⚠️ [UNEXPECTED] Received status {response.status_code}. Response: {response.text[:100]}")
except requests.exceptions.RequestException as e:
    print(f"   ❌ [FAIL] Request to '/generate' failed: {e}")

# 3. Check /api/chat
print("\n--------------------------------------------------")
print("🔄 Testing '/api/chat' endpoint...")
try:
    response = requests.post(f"{OLLAMA_HOST}/api/chat", json=dummy_payload_chat, timeout=20)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ [SUCCESS] '/api/chat' endpoint is available and responded.")
    elif response.status_code == 404:
        print("   ❌ [FAIL] '/api/chat' endpoint does NOT exist (404 Not Found).")
    else:
        print(f"   ⚠️ [UNEXPECTED] Received status {response.status_code}. Response: {response.text[:100]}")
except requests.exceptions.RequestException as e:
    print(f"   ❌ [FAIL] Request to '/api/chat' failed: {e}")

# 3b. Check /chat (no /api prefix)
print("\n--------------------------------------------------")
print("🔄 Testing '/chat' endpoint (no /api prefix)...")
try:
    response = requests.post(f"{OLLAMA_HOST}/chat", json=dummy_payload_chat, timeout=20)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ [SUCCESS] '/chat' endpoint is available and responded.")
    elif response.status_code == 404:
        print("   ❌ [FAIL] '/chat' endpoint does NOT exist (404 Not Found).")
    else:
        print(f"   ⚠️ [UNEXPECTED] Received status {response.status_code}. Response: {response.text[:100]}")
except requests.exceptions.RequestException as e:
    print(f"   ❌ [FAIL] Request to '/chat' failed: {e}")

print("\n--------------------------------------------------")
print("\n📋 Diagnosis complete. Please review the results above.")