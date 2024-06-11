import uvicorn
from cls_cad_backend.database.commands import init_database


def start():
    """Launched with `poetry run start` at root level."""
    init_database()
    uvicorn.run("cls_cad_backend.server:app", reload=True)


if __name__ == "__main__":
    start()
