import glob
import json
import os
import pickle
import typing
from collections import defaultdict
from json import JSONDecodeError
from uuid import uuid4

from fastapi import FastAPI, Body
from pathlib import Path

from starlette.responses import Response

from cls_python import (
    deep_str,
    CLSDecoder,
    FiniteCombinatoryLogic,
    Subtypes,
    CLSEncoder,
)
from util.set_json import SetEncoder, SetDecoder
from repository_builder import RepositoryBuilder

app = FastAPI()

# Response that is easy to debug
class IndentedResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


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

    Path("Repositories/CAD/index.dat").touch(exist_ok=True)
    with open("Repositories/CAD/index.dat", "r+") as f:
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        data["folders"][payload["meta"]["forgeFolderId"]] = set()

        try:
            data = json.load(f, cls=SetDecoder)
        # incase we switch to pickle later on
        except EOFError:
            pass
        except JSONDecodeError:
            # ToDo: Implement reindexing
            print("JSON wouldn't decode. Probably tampered, re-indexing...")

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
        f.seek(0)
        f.truncate()
        json.dump(data, f, cls=SetEncoder, indent=4)

    # Data is sane and can be decoded, so from this we can construct all necessary combinators
    # print(json.loads(json.dumps(payload["combinator"]), cls=CLSDecoder))
    return "OK"


@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: dict = Body(...),
):
    with open("Repositories/CAD/taxonomy.dat", "w+") as f:
        json.dump(payload, f, cls=SetEncoder, indent=4)


@app.post("/request/assembly")
async def synthesize_assembly(
    payload: dict = Body(...),
):
    taxonomy = Subtypes(
        json.load(open("Repositories/CAD/taxonomy.dat", "r"), cls=SetDecoder)
    )
    gamma = FiniteCombinatoryLogic(
        RepositoryBuilder.add_all_to_repository(), taxonomy, processes=1
    )
    result = gamma.inhabit(json.loads(json.dumps(payload), cls=CLSDecoder))
    if result.size() != 0:
        request_id = uuid4()
        p = Path(os.path.join("Results", "CAD", str(request_id)))
        p.mkdir(parents=True, exist_ok=True)
        # Maybe also add an index.dat to results, priority low
        with (p / f"result.dat").open("w+") as f:
            json.dump(result, f, cls=CLSEncoder, indent=4)
        if result.size() != -1:
            for i in range(result.size()):
                with (p / f"{i}.json").open("w+") as f:
                    json.dump(result.evaluated[i].to_dict(), f, indent=4)
        return str(request_id)
    else:
        return "FAIL"


@app.get("/results", response_class=IndentedResponse)
async def list_result_ids():
    cad_dir = "Results/CAD"
    return [
        item
        for item in os.listdir(cad_dir)
        if os.path.isdir(os.path.join(cad_dir, item))
    ]


@app.get("/results/{request_id}", response_class=IndentedResponse)
async def results_for_id(request_id: str):
    results = []
    for filename in glob.glob(os.path.join(f"Results/CAD/{request_id}", "*.json")):
        with open(os.path.join(os.getcwd(), filename), "r") as f:
            results.append(json.load(f))
    return results


@app.get("/results/{request_id}/{result_id}", response_class=IndentedResponse)
async def results_for_id(request_id: str, result_id: int):
    result = json.load(
        open(os.path.join(f"Results/CAD/{request_id}", "result.dat"), "r"),
        cls=CLSDecoder,
    )
    return result.evaluated[result_id].to_dict()
