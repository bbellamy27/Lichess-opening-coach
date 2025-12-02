import requests

url = "https://api.puter.com/v2/ai/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Origin": "https://puter.com",
    "Referer": "https://puter.com/"
}

payload = {
    "model": "meta-llama/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Hello, are you working?"}]
}

try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
