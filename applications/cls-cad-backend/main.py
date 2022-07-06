import json
import os
import pickle
from collections import defaultdict
from json import JSONDecodeError

from fastapi import FastAPI, Body
from pathlib import Path
from cls_python import CLSDecoder, deep_str
from set_json import SetEncoder, SetDecoder

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/part")
async def save_part(
    payload: dict = Body(...),
):
    if not all(
        k in payload
        for k in (
            "forgeProjectId",
            "forgeFolderId",
            "forgeDocumentId",
            "partName",
            "partConfigs",
            "combinator",
        )
    ):
        return "Invalid Part, Missing Key."
    p = Path(
        os.path.join(
            "Repositories", "CAD", payload["forgeProjectId"], payload["forgeFolderId"]
        ).replace(":", "-")
    )
    p.mkdir(parents=True, exist_ok=True)
    with (p / payload["forgeDocumentId"].replace(":", "-")).open("w+") as f:
        json.dump(payload, f, indent=4)
    with open("Repositories/CAD/index.dat", "a+") as f:
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        data["folders"][payload["forgeFolderId"]] = set()

        try:
            data = json.load(f, cls=SetDecoder)
        # incase we switch to pickle later on
        except EOFError:
            pass
        except JSONDecodeError:
            pass

        data["parts"][payload["forgeDocumentId"]] = {
            "forgeProjectId": payload["forgeProjectId"],
            "forgeFolderId": payload["forgeFolderId"],
        }
        data["projects"][payload["forgeProjectId"]]["folders"].add(
            payload["forgeFolderId"]
        )
        data["projects"][payload["forgeProjectId"]]["documents"].add(
            payload["forgeDocumentId"]
        )
        data["folders"][payload["forgeFolderId"]].add(payload["forgeDocumentId"])

        json.dump(data, f, cls=SetEncoder, indent=4)
    # Data is sane and can be decoded, so from this we can construct all necessary combinators
    # print(json.loads(json.dumps(payload["combinator"]), cls=CLSDecoder))
    return "OK"
