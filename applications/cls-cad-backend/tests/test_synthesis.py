import cls_cad_backend.server
import pytest
from cls_cad_backend.database.commands import switch_to_test_database
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)
switch_to_test_database()


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
def test_synthesis_simple():
    test_payload = {
        "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
        "target": ["Cube_parts"],
        "name": "Simple Request",
    }
    response = client.post("/request/assembly", json=test_payload)
    assert response.status_code == 200
    assert response.text != "FAIL"
    assert response.json()["count"] == 100


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
def test_synthesis_intersection():
    test_payload = {
        "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
        "target": ["Cube_parts", "Plastic_attributes"],
        "name": "Intersection Request",
    }
    response = client.post("/request/assembly", json=test_payload)
    assert response.status_code == 200
    assert response.text != "FAIL"
    assert response.json()["count"] == 100


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
def test_synthesis_simple_counting():
    test_payload = {
        "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
        "target": ["Cube_parts"],
        "name": "Simple Counting Request",
        "partCounts": [
            {
                "partNumber": 5,
                "partCountName": "Simple Count",
                "partType": ["Cube_parts"],
            }
        ],
    }
    response = client.post("/request/assembly", json=test_payload)
    assert response.status_code == 200
    assert response.text != "FAIL"
    assert response.json()["count"] == 1


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
def test_synthesis_intersection_counting():
    test_payload = {
        "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
        "target": ["Cube_parts"],
        "name": "Simple Counting Request",
        "partCounts": [
            {
                "partNumber": 5,
                "partCountName": "Intersection Count",
                "partType": ["Cube_parts", "Plastic_attributes"],
            }
        ],
    }
    response = client.post("/request/assembly", json=test_payload)
    assert response.status_code == 200
    assert response.text != "FAIL"
    assert response.json()["count"] == 1
