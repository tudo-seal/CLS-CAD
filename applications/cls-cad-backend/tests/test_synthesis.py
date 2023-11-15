import cls_cad_backend.server
import pytest
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
@pytest.mark.order(4)
def test_synthesis_simple():
    test_payload = {
        "forgeProjectId": "forgeProject",
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
@pytest.mark.order(5)
def test_synthesis_intersection():
    test_payload = {
        "forgeProjectId": "forgeProject",
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
@pytest.mark.order(6)
def test_synthesis_simple_counting():
    test_payload = {
        "forgeProjectId": "forgeProject",
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
    assert response.json()["count"] == 3


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
@pytest.mark.order(7)
def test_synthesis_intersection_counting():
    test_payload = {
        "forgeProjectId": "forgeProject",
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
    assert response.json()["count"] == 4


@pytest.mark.dependency(
    depends=[
        "tests/test_database.py::test_upsert_taxonomy",
        "tests/test_database.py::test_upsert_parts",
    ],
    scope="session",
)
@pytest.mark.order(8)
def test_synthesis_intersection_fail():
    # There is no way to construct this without using at least one plastic part.
    test_payload = {
        "forgeProjectId": "forgeProject",
        "target": ["Cube_parts"],
        "name": "Simple Counting Request",
        "partCounts": [
            {
                "partNumber": 0,
                "partCountName": "Intersection Count",
                "partType": ["Cube_parts", "Plastic_attributes"],
            }
        ],
    }
    response = client.post("/request/assembly", json=test_payload)
    assert response.status_code == 200
    assert response.text == '"FAIL"'
