from fastapi.testclient import TestClient
from app.main import fastapi_app

client = TestClient(fastapi_app)

try:
    response = client.post("/api/workspace/open", json={"path": "D:/Riya/Prerak2.0/test"})
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
