import cls_cad_backend.server
import pytest
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.mark.dependency()
@pytest.mark.order(1)
def test_upsert_taxonomy():
    test_payload = {
        "_id": "forgeProject",
        "forgeProjectId": "forgeProject",
        "taxonomies": {
            "parts": {"Cube": ["Part"]},
            "formats": {"Square": ["Format"]},
            "attributes": {"Plastic": ["Attribute"]},
        },
        "mappings": {
            "parts": {
                "Part": "hear-should-help-close-person-change",
                "Cube": "lead-remain-stand-medical-central-day",
            },
            "formats": {
                "Format": "look-lose-work-leave-natural-case",
                "Square": "should-kill-past-part-word-family",
            },
            "attributes": {
                "Attribute": "should-spend-financial-great-late-area",
                "Plastic": "pay-bring-stand-different-question-community",
            },
        },
    }
    response = client.post("/submit/taxonomy", json=test_payload)
    assert response.status_code == 200


@pytest.mark.dependency()
@pytest.mark.order(2)
def test_upsert_parts():
    test_payload = {
        "_id": "1",
        "configurations": [
            {
                "requiresJointOrigins": ["a1"],
                "providesJointOrigin": "b1",
            }
        ],
        "meta": {
            "name": "Cube v2",
            "forgeDocumentId": "1",
            "forgeFolderId": "forgeFolder",
            "forgeProjectId": "forgeProject",
            "cost": 1.0,
            "availability": 1.0,
        },
        "jointOrigins": {
            "a1": {
                "motion": "Revolute",
                "count": 1,
                "requires": ["Square_formats", "Cube_parts"],
                "provides": [],
            },
            "b1": {
                "motion": "Rigid",
                "count": 1,
                "requires": [],
                "provides": ["Plastic_attributes", "Cube_parts", "Square_formats"],
            },
        },
    }
    response = client.post("/submit/part", json=test_payload)
    assert response.status_code == 200

    test_payload = {
        "_id": "2",
        "configurations": [
            {
                "requiresJointOrigins": ["a2"],
                "providesJointOrigin": "b2",
            }
        ],
        "meta": {
            "name": "Cube Double v2",
            "forgeDocumentId": "2",
            "forgeFolderId": "forgeFolder",
            "forgeProjectId": "forgeProject",
            "cost": 1.0,
            "availability": 1.0,
        },
        "jointOrigins": {
            "a2": {
                "motion": "Revolute",
                "count": 2,
                "requires": ["Square_formats", "Cube_parts"],
                "provides": [],
            },
            "b2": {
                "motion": "Rigid",
                "count": 1,
                "requires": [],
                "provides": ["Cube_parts", "Square_formats"],
            },
        },
    }
    response = client.post("/submit/part", json=test_payload)
    assert response.status_code == 200

    test_payload = {
        "_id": "3",
        "configurations": [
            {
                "requiresJointOrigins": [],
                "providesJointOrigin": "b3",
            }
        ],
        "meta": {
            "name": "Cube_End v2",
            "forgeDocumentId": "3",
            "forgeFolderId": "forgeFolder",
            "forgeProjectId": "forgeProject",
            "cost": 1.0,
            "availability": 1.0,
        },
        "jointOrigins": {
            "b3": {
                "motion": "Rigid",
                "count": 1,
                "requires": [],
                "provides": ["Plastic_attributes", "Cube_parts", "Square_formats"],
            }
        },
    }
    response = client.post("/submit/part", json=test_payload)
    assert response.status_code == 200


@pytest.mark.dependency(depends=["test_upsert_taxonomy"])
@pytest.mark.order(3)
def test_fetch_taxonomy():
    response = client.get("/data/taxonomy/non-existing")
    assert response.status_code == 200
    assert len(response.json()["taxonomies"]["parts"]["Part"]) == 0

    response = client.get("/data/taxonomy/forgeProject")
    assert response.status_code == 200
    assert len(response.json()["taxonomies"]["parts"]["Part"]) == 1
