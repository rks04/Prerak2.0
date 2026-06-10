import requests
import time

time.sleep(1) # wait for server
url = "http://127.0.0.1:8000/api/workspace/open"
data = {"path": "D:/Riya/Prerak2.0/test"}
try:
    response = requests.post(url, json=data)
    print("Status:", response.status_code)
    print("Body:", response.text)
except Exception as e:
    print("Error:", e)
