import json
import os
from collections import defaultdict
from json import JSONDecodeError

from fastapi import FastAPI, Body
from pathlib import Path

from cls_python import deep_str
from lib.set_json import SetEncoder, SetDecoder

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/submit/part")
async def save_part(
    payload: dict = Body(...),
):
    deep_str(payload)
    if not all(
        k in payload
        for k in (
            "meta",
            "partConfigs",
            "combinator",
        )
    ):
        return "Invalid Part, Missing Key."
    p = Path(
        os.path.join(
            "Repositories",
            "CAD",
            payload["meta"]["forgeProjectId"],
            payload["meta"]["forgeFolderId"],
        ).replace(":", "-")
    )
    p.mkdir(parents=True, exist_ok=True)
    with (p / payload["meta"]["forgeDocumentId"].replace(":", "-")).open("w+") as f:
        json.dump(payload, f, indent=4)
    with open("Repositories/CAD/index.dat", "a+") as f:
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        data["folders"][payload["meta"]["forgeFolderId"]] = set()

        try:
            data = json.load(f, cls=SetDecoder)
        # incase we switch to pickle later on
        except EOFError:
            pass
        except JSONDecodeError:
            pass

        data["parts"][payload["meta"]["forgeDocumentId"]] = {
            "forgeProjectId": payload["meta"]["forgeProjectId"],
            "forgeFolderId": payload["meta"]["forgeFolderId"],
        }
        data["projects"][payload["meta"]["forgeProjectId"]]["folders"].add(
            payload["meta"]["forgeFolderId"]
        )
        data["projects"][payload["meta"]["forgeProjectId"]]["documents"].add(
            payload["meta"]["forgeDocumentId"]
        )
        data["folders"][payload["meta"]["forgeFolderId"]].add(
            payload["meta"]["forgeDocumentId"]
        )

        json.dump(data, f, cls=SetEncoder, indent=4)
    # Data is sane and can be decoded, so from this we can construct all necessary combinators
    # print(json.loads(json.dumps(payload["combinator"]), cls=CLSDecoder))
    return "OK"
