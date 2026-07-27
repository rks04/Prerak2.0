import requests

OLLAMA_HOST = "http://10.10.10.110:11434"

try:
    response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
    response.raise_for_status()

    data = response.json()
    models = data.get("models", [])

    if not models:
        print("No models found.")
    else:
        print("\nDOWNLOADED MODELS")
        print("-" * 60)

        for model in models:
            name = model.get("name", "Unknown")
            size = model.get("size", 0)

            size_gb = size / (1024**3)

            print(f"• {name:<25} {size_gb:.2f} GB")

        print("-" * 60)
        print(f"Total Models : {len(models)}")

except requests.exceptions.ConnectionError:
    print("Could not connect to the remote Ollama server.")
    print("Check:")
    print(" - Server IP")
    print(" - Ollama is running")
    print(" - Port 11434 is open")
except Exception as e:
    print("Error:", e)