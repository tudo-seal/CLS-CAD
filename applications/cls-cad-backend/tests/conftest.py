import os
import shutil

import cls_cad_backend.database.commands
import cls_cad_backend.server
import pytest
from cls_cad_backend.database.commands import switch_to_test_database
from fastapi.testclient import TestClient

client = TestClient(cls_cad_backend.server.app)


@pytest.fixture(scope="session", autouse=True)
def prepare_everything(request):
    try:
        shutil.rmtree(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "cls_cad_backend",
                "database",
                "test_db",
            )
        )
    except OSError:
        pass
    switch_to_test_database()
    request.addfinalizer(cleanup)


def cleanup():
    shutil.rmtree(
        os.path.join(
            os.path.dirname(__file__), "..", "cls_cad_backend", "database", "test_db"
        )
    )
