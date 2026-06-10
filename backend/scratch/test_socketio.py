import requests
import time

time.sleep(1) # Wait for server
url = "http://127.0.0.1:8000/socket.io/?EIO=4&transport=polling"
try:
    response = requests.get(url)
    print("Socket.io Status:", response.status_code)
    print("Socket.io Body:", response.text[:200])
except Exception as e:
    print("Error:", e)
