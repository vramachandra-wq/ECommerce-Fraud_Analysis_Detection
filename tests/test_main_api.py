from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert body["analyst_portal"] == "/portal/"
    assert body["customer_portal"] == "/shop/"
