import uvicorn


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("cls_cps.server:app", reload=True)


if __name__ == "__main__":
    start()
