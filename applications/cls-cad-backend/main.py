import uvicorn
from cls_cad_backend.database.commands import init_database


def start():
    """Launched with `poetry run start` at root level."""
    init_database()
    uvicorn.run("cls_cad_backend.server:app", reload=True)


def start_docker():
    """Launched with `poetry run start` at root level."""
    init_database()
    uvicorn.run("cls_cad_backend.server:app", reload=False, host="0.0.0.0", port=80)


if __name__ == "__main__":
    start()
