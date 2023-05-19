import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path

import uvicorn
from bcls import (
    Constructor,
    FiniteCombinatoryLogic,
    Subtypes,
    Type,
    enumerate_terms,
    enumerate_terms_of_size,
    interpret_term,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTasks
from starlette.staticfiles import StaticFiles

from cls_cps.database.commands import (
    get_all_projects_in_results,
    get_all_result_ids_for_project,
    get_result_for_id,
    get_taxonomy_for_project,
    init_database,
    upsert_part,
    upsert_result,
    upsert_taxonomy,
)
from cls_cps.hypermapper_tools.hypermapper_compatibility import (
    create_hypermapper_config,
    wrapped_synthesis_optimization_function,
)
from cls_cps.hypermapper_tools.hypermapper_visualisation import (
    compute_pareto_front,
    visualize_pareto_front,
)
from cls_cps.repository_builder import RepositoryBuilder
from cls_cps.responses import FastResponse
from cls_cps.schemas import PartInf, SynthesisRequestInf, TaxonomyInf
from cls_cps.util.hrid import generate_id
from cls_cps.util.json_operations import (
    invert_taxonomy,
    postprocess,
    suffix_taxonomy_and_add_mirror,
)

no_hypermapper = False
try:
    from hypermapper import optimizer
except ImportError:
    no_hypermapper = True

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
init_database()

cache = {}


@app.post("/submit/part")
async def save_part(
    payload: PartInf,
):
    upsert_part(payload.dict(by_alias=True))
    return "OK"


@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: TaxonomyInf,
):
    upsert_taxonomy(payload.dict(by_alias=True))


@app.post("/request/assembly/optimization")
async def request_optimization(
    payload: SynthesisRequestInf,
):
    if no_hypermapper:
        return "Unsupported."
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
    payload: SynthesisRequestInf, background_tasks: BackgroundTasks
):
    taxonomy = Subtypes(
        suffix_taxonomy_and_add_mirror(get_taxonomy_for_project(payload.forgeProjectId))
    )
    gamma = FiniteCombinatoryLogic(
        RepositoryBuilder.add_all_to_repository(
            payload.forgeProjectId,
            blacklist=payload.blacklist,
            connect_uuid=payload.sourceUuid,
            taxonomy=taxonomy,
            propagated_types=payload.propagate,
        ),
        taxonomy,
    )

    query = Type.intersect(
        [Constructor(x) for x in payload.target]
        + [
            Type.intersect([Constructor(tpe) for tpe in tpe_list])
            for tpe_list in payload.propagate
        ],
    )

    result = gamma.inhabit(query)
    terms = []
    from timeit import default_timer as timer

    start = timer()

    if payload.depths:
        for depth in payload.depths:
            terms.extend(
                enumerate_terms_of_size(
                    query, result, term_size=depth, max_count=payload.resultsPerDepth
                )
            )
    else:
        terms.extend(enumerate_terms(query, result, max_count=100))
    print(timer() - start)
    interpreted_terms = [postprocess(interpret_term(term)) for term in terms]
    print(timer() - start)

    if not interpreted_terms:
        return "FAIL"

    request_id = generate_id()
    background_tasks.add_task(
        upsert_result,
        {
            "_id": request_id,
            "forgeProjectId": payload.forgeProjectId,
            "name": payload.name,
            "timestamp": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(interpreted_terms),
            "interpretedTerms": interpreted_terms,
        },
    )
    return str(request_id)


@app.get("/data/taxonomy/{project_id}", response_class=FastResponse)
async def get_taxonomy(project_id: str):
    return invert_taxonomy(get_taxonomy_for_project(project_id))


@app.get("/results", response_class=FastResponse)
async def list_result_ids():
    return get_all_projects_in_results()


@app.get("/results/{project_id}", response_class=FastResponse)
async def list_result_ids(project_id: str):
    return [dict(x, id=x["_id"]) for x in get_all_result_ids_for_project(project_id)]


@app.get("/results/{project_id}/{request_id}", response_class=FastResponse)
async def results_for_id(
    project_id: str,
    request_id: str,
    skip: int | None = None,
    limit: int | None = None,
):
    if limit == 0:
        return []

    if request_id not in cache:
        cache[request_id] = get_result_for_id(request_id)["interpretedTerms"]
    results = cache[request_id]

    if skip is not None and limit is not None:
        return FastResponse(
            [
                results[result_id]
                for result_id in range(
                    skip if skip < len(results) else len(results) - 1,
                    skip + limit if (skip + limit) <= len(results) else len(results),
                )
            ]
        )
    else:
        return results


@app.get("/results/{project_id}/{request_id}/{result_id}", response_class=FastResponse)
async def results_for_id(project_id: str, request_id: str, result_id: int):
    if request_id not in cache:
        cache[request_id] = get_result_for_id(request_id)["interpretedTerms"]
    results = cache[request_id]
    if result_id < len(results) or len(results) == -1:
        return FastResponse(results[result_id])
    else:
        return ""


# Finally, mount webpage for root.
app.mount("/", StaticFiles(directory="static/welcomePage", html=True), name="landing")


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("main:app", reload=True)
