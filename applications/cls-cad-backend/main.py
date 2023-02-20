from __future__ import annotations

import glob
import json
import mimetypes
import os
from collections import defaultdict
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hypermapper import optimizer
from starlette.staticfiles import StaticFiles

from cls_python import CLSDecoder, CLSEncoder, FiniteCombinatoryLogic, Subtypes
from hypermapper_tools.hypermapper_compatibility import (
    create_hypermapper_config,
    wrapped_synthesis_optimization_function,
)
from hypermapper_tools.hypermapper_visualisation import (
    compute_pareto_front,
    visualize_pareto_front,
)
from repository_builder import RepositoryBuilder
from responses import FastResponse
from schemas import PartInf, SynthesisRequestInf, TaxonomyInf
from util.hrid import generate_id
from util.set_json import SetDecoder, SetEncoder

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app = FastAPI(title="CLS-CPS (Cyberphysical System Synthesis Backend)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mimetypes.init()
mimetypes.add_type("application/javascript", ".js")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the CLS-CPS backend. Head to /docs for information about endpoints."
    }


@app.post("/submit/part")
async def save_part(
    payload: PartInf,
):
    p = Path(
        os.path.join(
            "Repositories",
            "CAD",
            payload.meta.forgeProjectId,
            payload.meta.forgeFolderId,
        ).replace(":", "-")
    )
    p.mkdir(parents=True, exist_ok=True)
    with (p / payload.meta.forgeDocumentId.replace(":", "-")).open("w+") as f:
        json.dump(payload.dict(), f, indent=4, cls=SetEncoder)

    Path("Repositories/CAD/index.dat").touch(exist_ok=True)
    with open("Repositories/CAD/index.dat", "r+") as f:
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        try:
            data = json.load(f, cls=SetDecoder)
        # incase we switch to pickle later on
        except EOFError:
            pass
        except JSONDecodeError:
            # ToDo: Implement reindexing
            print("JSON wouldn't decode. Probably tampered, re-indexing...")

        data["folders"][payload.meta.forgeFolderId] = set()
        data["projects"].setdefault(
            payload.meta.forgeProjectId,
            {
                "folders": set(),
                "documents": set(),
            },
        )

        data["parts"][payload.meta.forgeDocumentId] = {
            "forgeProjectId": payload.meta.forgeProjectId,
            "forgeFolderId": payload.meta.forgeFolderId,
            "name": payload.meta.partName,
        }
        data["projects"][payload.meta.forgeProjectId]["folders"].add(
            payload.meta.forgeFolderId
        )
        data["projects"][payload.meta.forgeProjectId]["documents"].add(
            payload.meta.forgeDocumentId
        )
        data["folders"][payload.meta.forgeFolderId].add(payload.meta.forgeDocumentId)
        f.seek(0)
        f.truncate()
        json.dump(data, f, cls=SetEncoder, indent=4)

    return "OK"


@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: TaxonomyInf,
):
    p = Path(
        os.path.join(
            "Taxonomies",
            "CAD",
            payload.forgeProjectId,
        ).replace(":", "-")
    )
    p.mkdir(parents=True, exist_ok=True)
    with open(f"Taxonomies/CAD/{payload.forgeProjectId}/taxonomy.dat", "w+") as f:
        json.dump(payload.taxonomy, f, cls=SetEncoder, indent=4)


@app.post("/request/assembly/optimization")
async def request_optimization(
    payload: SynthesisRequestInf,
):
    request_id = str(generate_id())
    p = Path(os.path.join("Results", "Hypermapper", payload.forgeProjectId, request_id))
    p.mkdir(parents=True, exist_ok=True)
    with open(
        f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}/hypermapper_config.json",
        "w+",
    ) as f:
        json.dump(
            create_hypermapper_config(
                request_id, payload.forgeProjectId, [json.dumps(payload.target)]
            ),
            f,
            indent=4,
        )

    optimizer.optimize(
        f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}/hypermapper_config.json",
        wrapped_synthesis_optimization_function,
    )
    df = compute_pareto_front(
        f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}"
    )
    visualize_pareto_front(
        df, f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}"
    )
    return "OK."


@app.post("/request/assembly")
async def synthesize_assembly(
    payload: SynthesisRequestInf,
):
    taxonomy = Subtypes(
        json.load(
            open(f"Taxonomies/CAD/{payload.forgeProjectId}/taxonomy.dat"),
            cls=SetDecoder,
        )
    )
    if payload.source and payload.sourceUuid:
        gamma = FiniteCombinatoryLogic(
            RepositoryBuilder.add_all_to_repository(
                payload.forgeProjectId,
                blacklist=payload.source,
                connect_uuid=payload.sourceUuid,
                taxonomy=taxonomy,
            ),
            taxonomy,
            processes=1,
        )
    else:
        gamma = FiniteCombinatoryLogic(
            RepositoryBuilder.add_all_to_repository(payload.forgeProjectId),
            taxonomy,
            processes=1,
        )
    result = gamma.inhabit(json.loads(json.dumps(payload.target), cls=CLSDecoder))

    if result.size() == 0:
        return "FAIL"

    request_id = generate_id()
    p = Path(os.path.join("Results", "CAD", payload.forgeProjectId, str(request_id)))
    p.mkdir(parents=True, exist_ok=True)
    with (p / f"result.info").open("w+") as f:
        json.dump(
            {
                "id": request_id,
                "name": payload.name,
                "timestamp": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                "count": result.size(),
            },
            f,
            indent=4,
        )
    # Maybe also add an index.dat to results, priority low
    with (p / f"result.dat").open("w+") as f:
        json.dump(result, f, cls=CLSEncoder, indent=4)
    if result.size() != -1:
        for i in range(result.size()):
            with (p / f"{i}.json").open("w+") as f:
                json.dump(result.evaluated[i].to_dict(), f, indent=4)
    return str(request_id)


@app.get("/results", response_class=FastResponse)
async def list_result_ids():
    cad_dir = "Results/CAD"
    return [
        item
        for item in os.listdir(cad_dir)
        if os.path.isdir(os.path.join(cad_dir, item))
    ]


@app.get("/results/{project_id}", response_class=FastResponse)
async def list_result_ids(project_id: str):
    cad_dir = f"Results/CAD/{project_id}"
    return [
        json.load(open(os.path.join(cad_dir, item, "result.info")))
        for item in os.listdir(cad_dir)
        if os.path.isdir(os.path.join(cad_dir, item))
    ]


@app.get("/results/{project_id}/{request_id}", response_class=FastResponse)
async def results_for_id(
    project_id: str,
    request_id: str,
    skip: int | None = None,
    limit: int | None = None,
):
    results = []
    if limit == 0:
        return results
    if skip is not None and limit is not None:
        result = json.load(
            open(
                os.path.join(f"Results/CAD/{project_id}/{request_id}", "result.dat"),
            ),
            cls=CLSDecoder,
        )

        return FastResponse(
            [
                result.evaluated[result_id].to_dict()
                for result_id in (
                    range(skip, skip + limit)
                    if result.size() == -1
                    else range(
                        skip if skip < result.size() else result.size() - 1,
                        skip + limit
                        if (skip + limit) <= result.size()
                        else result.size(),
                    )
                )
            ]
        )
    else:
        for filename in glob.glob(
            os.path.join(f"Results/CAD/{project_id}/{request_id}", "*.json")
        ):
            with open(os.path.join(os.getcwd(), filename)) as f:
                results.append(json.load(f))
        return results


@app.get("/results/{project_id}/{request_id}/{result_id}", response_class=FastResponse)
async def results_for_id(project_id: str, request_id: str, result_id: int):
    result = json.load(
        open(os.path.join(f"Results/CAD/{project_id}/{request_id}", "result.dat")),
        cls=CLSDecoder,
    )
    if result_id < result.size() or result.size() == -1:
        return FastResponse(result.evaluated[result_id].to_dict())
    else:
        return dict()
