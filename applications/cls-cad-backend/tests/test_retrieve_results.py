import cls_cad_backend.server
import pytest
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(9)
def test_for_project_in_results():
    response = client.get("/results")
    assert response.status_code == 200
    assert "forgeProject" in response.json()


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(10)
def test_for_project_has_results():
    response = client.get("/results/forgeProject")
    assert response.status_code == 200
    assert len(response.json()) == 4


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(11)
def test_for_project_results_are_individually_retrievable():
    response = client.get("/results/forgeProject")
    response = client.get(f"/results/forgeProject/{response.json()[0]['id']}/0")
    assert response.status_code == 200
    assert response.json()


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(12)
def test_for_project_results_are_sane():
    response = client.get("/results/forgeProject")
    result = response.json()[0]["id"]
    response = client.get(f"/results/forgeProject/{result}")
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Tests for caching
    response = client.get(f"/results/forgeProject/{result}")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(13)
def test_for_project_results_are_batchable():
    response = client.get("/results/forgeProject")
    response = client.get(f"/results/forgeProject/{response.json()[0]['id']}/maxcounts")
    assert response.status_code == 200
    assert response.json()


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(14)
def test_for_limit_and_skip():
    response = client.get("/results/forgeProject")
    result = response.json()[0]["id"]
    response = client.get(f"/results/forgeProject/{result}")
    assert response.status_code == 200
    result_length = len(response.json())

    response = client.get(f"/results/forgeProject/{result}?limit=0")
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(f"/results/forgeProject/{result}?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(f"/results/forgeProject/{result}?skip=1")
    assert response.status_code == 200
    assert len(response.json()) == result_length - 1

    response = client.get(f"/results/forgeProject/{result}?limit=1&skip=1")
    assert response.status_code == 200


@pytest.mark.dependency(
    depends=["tests/test_synthesis.py::test_synthesis_intersection_counting"],
    scope="session",
)
@pytest.mark.order(15)
def test_for_invidual_results():
    response = client.get("/results/forgeProject")
    result = response.json()[0]["id"]
    response = client.get(f"/results/forgeProject/{result}/0")
    assert response.status_code == 200
    assert len(response.json()) > 0

    response = client.get(f"/results/forgeProject/{result}/999")
    assert response.status_code == 200
    assert response.json() == ""
