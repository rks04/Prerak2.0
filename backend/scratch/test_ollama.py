import requests
import time

try:
    start = time.time()
    response = requests.get("http://localhost:11434/api/tags")
    print("Ollama Status:", response.status_code)
    print("Models:", [m['name'] for m in response.json().get('models', [])])
    print(f"Time taken: {time.time() - start}s")
except Exception as e:
    print("Error connecting to Ollama:", e)
