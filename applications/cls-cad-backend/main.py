import uvicorn


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("cls_cad_backend.server:app", reload=True)


if __name__ == "__main__":
    start()
