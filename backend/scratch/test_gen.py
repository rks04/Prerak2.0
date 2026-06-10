import requests

try:
    print("Testing generate endpoint...")
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.1:latest", "prompt": "say hi", "stream": False},
        timeout=30
    )
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
