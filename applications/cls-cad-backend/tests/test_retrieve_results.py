import cls_cad_backend.server
import pytest
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(8)
def test_for_project_in_results():
    response = client.get("/results")
    assert response.status_code == 200
    assert "a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ" in response.json()


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(9)
def test_for_project_has_results():
    response = client.get("/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ")
    assert response.status_code == 200
    assert len(response.json()) == 4


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(10)
def test_for_project_results_are_individually_retrievable():
    response = client.get("/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ")
    response = client.get(
        f"/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ/{response.json()[0]['id']}/0"
    )
    assert response.status_code == 200
    assert response.json()


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(11)
def test_for_project_results_are_sane():
    response = client.get("/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ")
    result = response.json()[0]["id"]
    response = client.get(
        f"/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ/{result}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Tests for caching
    response = client.get(
        f"/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ/{result}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(12)
def test_for_project_results_are_batchable():
    response = client.get("/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ")
    response = client.get(
        f"/results/a.YnVzaW5lc3M6Y2hhdW1ldCMyMDIzMTEwOTY5NjQ4MjUwMQ/{response.json()[len(response.json())-1]['id']}/maxcounts"
    )
    assert response.status_code == 200
    assert response.json()
