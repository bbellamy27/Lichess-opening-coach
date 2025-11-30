import requests

# Pollinations.ai text endpoint (OpenAI compatible-ish)
url = "https://text.pollinations.ai/"
headers = {"Content-Type": "application/json"}

# Simple GET request format often works for them, or POST
# Let's try the standard POST with OpenAI format which they often support
payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, are you working?"}
    ],
    "model": "openai" # or 'searchgpt', 'mistral', etc.
}

try:
    # Pollinations often takes raw text or simple JSON. 
    # Let's try a direct POST which is how their docs usually describe it for bots
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
