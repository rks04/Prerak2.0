import requests
import time
import uuid

convo_id = uuid.uuid4().hex[:32]
url = "http://127.0.0.1:8000/api/trigger"
data = {
    "prompt": "Create a simple hello world python script",
    "convo_id": convo_id,
    "workspace_id": "test_workspace_id"
}

print(f"Triggering pipeline for convo: {convo_id}")
try:
    response = requests.post(url, json=data)
    print("Status:", response.status_code)
    print("Body:", response.text)
except Exception as e:
    print("Error:", e)
