import cls_cad_backend.server
import pytest
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.mark.dependency()
@pytest.mark.order(1)
def test_upsert_taxonomy():
    test_payload = {
        "_id": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
        "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
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
        "_id": "urn:adsk.wipprod:dm.lineage:5Za2vPl5QGGfDsQXYV1peA",
        "configurations": [
            {
                "requiresJointOrigins": ["speak-become-white-past-woman-case"],
                "providesJointOrigin": "allow-difficult-political-game-guy-art",
            }
        ],
        "meta": {
            "name": "Cube v2",
            "forgeDocumentId": "urn:adsk.wipprod:dm.lineage:5Za2vPl5QGGfDsQXYV1peA",
            "forgeFolderId": "urn:adsk.wipprod:fs.folder:co.FZZmke6KQXG_Fww59QryrA",
            "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
            "cost": 1.0,
            "availability": 1.0,
        },
        "jointOrigins": {
            "speak-become-white-past-woman-case": {
                "motion": "Revolute",
                "count": 1,
                "requires": ["Square_formats", "Cube_parts", "Plastic_attributes"],
                "provides": [],
            },
            "allow-difficult-political-game-guy-art": {
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
        "_id": "urn:adsk.wipprod:dm.lineage:7LFKjMFQRaSkLItKYLSJ6w",
        "configurations": [
            {
                "requiresJointOrigins": [],
                "providesJointOrigin": "allow-difficult-political-game-guy-art",
            }
        ],
        "meta": {
            "name": "Cube_End v2",
            "forgeDocumentId": "urn:adsk.wipprod:dm.lineage:7LFKjMFQRaSkLItKYLSJ6w",
            "forgeFolderId": "urn:adsk.wipprod:fs.folder:co.FZZmke6KQXG_Fww59QryrA",
            "forgeProjectId": "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ",
            "cost": 1.0,
            "availability": 1.0,
        },
        "jointOrigins": {
            "allow-difficult-political-game-guy-art": {
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

    response = client.get(
        "/data/taxonomy/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ"
    )
    assert response.status_code == 200
    assert len(response.json()["taxonomies"]["parts"]["Part"]) == 1
