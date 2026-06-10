import requests
import json

url = "http://127.0.0.1:8000/api/workspace/open"
data = {"path": "D:/Riya/Prerak2.0/test"}

try:
    response = requests.post(url, json=data)
    print("Status Code:", response.status_code)
    print("Response Body:", response.text)
except Exception as e:
    print("Request failed:", e)
