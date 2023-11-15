import mimetypes
import os
import sys
from collections import defaultdict
from datetime import datetime
from timeit import default_timer as timer

from cls_cad_backend.database.commands import (
    get_all_projects_in_results,
    get_all_result_ids_for_project,
    get_result_for_id,
    get_taxonomy_for_project,
    init_database,
    upsert_part,
    upsert_result,
    upsert_taxonomy,
)
from cls_cad_backend.repository_builder import RepositoryBuilder, wrapped_counted_types
from cls_cad_backend.responses import FastResponse
from cls_cad_backend.schemas import PartInf, SynthesisRequestInf, TaxonomyInf
from cls_cad_backend.util.hrid import generate_id
from cls_cad_backend.util.json_operations import (
    invert_taxonomy,
    postprocess,
    suffix_taxonomy_and_add_mirror,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from picls import (
    Constructor,
    FiniteCombinatoryLogic,
    Subtypes,
    Type,
    enumerate_terms,
    interpret_term,
)
from picls.types import Literal, Omega
from starlette.background import BackgroundTasks
from starlette.staticfiles import StaticFiles

# no_hypermapper = False
# try:
#     from hypermapper import optimizer
#
#     from cls_cad_backend.hypermapper_tools.hypermapper_compatibility import (
#         create_hypermapper_config,
#         wrapped_synthesis_optimization_function,
#     )
#     from cls_cad_backend.hypermapper_tools.hypermapper_visualisation import (
#         compute_pareto_front,
#         visualize_pareto_front,
#     )
# except ImportError:
#     no_hypermapper = True

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app = FastAPI(title="CLS-CAD-BACKEND (Cyberphysical System Synthesis Backend)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mimetypes.init()
mimetypes.add_type("application/javascript", ".js")

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True),
    name="static",
)
init_database()

cache = {}


@app.post("/submit/part")
async def save_part(
    payload: PartInf,
) -> str:
    upsert_part(payload.model_dump(by_alias=True))
    print(payload.model_dump(by_alias=True))
    return "OK"


@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: TaxonomyInf,
) -> str:
    upsert_taxonomy(payload.model_dump(by_alias=True))
    return "OK"


# @app.post("/request/assembly/optimization")
# async def request_optimization(
#     payload: SynthesisRequestInf,
# ):
#     if no_hypermapper:
#         return "Unsupported."
#     request_id = str(generate_id())
#     p = Path(os.path.join("Results", "Hypermapper", payload.forgeProjectId, request_id))
#     p.mkdir(parents=True, exist_ok=True)
#     with open(
#         f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}/hypermapper_config.json",
#         "w+",
#     ) as f:
#         json.dump(
#             create_hypermapper_config(
#                 request_id, payload.forgeProjectId, [json.dumps(payload.target)]
#             ),
#             f,
#             indent=4,
#         )
#
#     optimizer.optimize(
#         f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}/hypermapper_config.json",
#         wrapped_synthesis_optimization_function,
#     )
#     df = compute_pareto_front(
#         f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}"
#     )
#     visualize_pareto_front(
#         df, f"Results/Hypermapper/{payload.forgeProjectId}/{request_id}"
#     )
#     return "OK."


@app.post("/request/assembly")
async def synthesize_assembly(
    payload: SynthesisRequestInf, background_tasks: BackgroundTasks
):
    take_time = timer()
    literals = {}
    part_count_type = Omega()
    if payload.partCounts:
        for partCount in payload.partCounts:
            literals[partCount.partCountName] = list(range(partCount.partNumber + 1))
        part_count_type = wrapped_counted_types(
            [Literal(c.partNumber, c.partCountName) for c in payload.partCounts]
        )

    query = Type.intersect([Constructor(x, part_count_type) for x in payload.target])
    # if payload.partCounts:
    #     for partCount in payload.partCounts:
    #         query = query & Literal(partCount.partNumber, partCount.partType)
    #         literals[partCount.partType] = list(range(partCount.partNumber + 1))

    taxonomy = Subtypes(
        suffix_taxonomy_and_add_mirror(get_taxonomy_for_project(payload.forgeProjectId))
    )

    repo = RepositoryBuilder.add_all_to_repository(
        payload.forgeProjectId,
        taxonomy=taxonomy,
        part_counts=[
            (p.partType, p.partNumber, p.partCountName) for p in payload.partCounts
        ]
        if payload.partCounts
        else None,
    )

    gamma = FiniteCombinatoryLogic(
        repo,
        taxonomy,
        literals=literals,
    )

    result = gamma.inhabit(query)
    terms = []

    terms.extend(enumerate_terms(query, result, max_count=100))
    # print(timer() - start)
    interpreted_terms = [postprocess(interpret_term(term)) for term in terms]

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
            "payload": payload.model_dump(),
        },
    )
    print(f"Took: {timer() - take_time}")
    return {
        "_id": request_id,
        "forgeProjectId": payload.forgeProjectId,
        "name": payload.name,
        "timestamp": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(interpreted_terms),
    }


@app.get("/data/taxonomy/{project_id}", response_class=FastResponse)
async def get_taxonomy(project_id: str):
    return invert_taxonomy(get_taxonomy_for_project(project_id))


@app.get("/results", response_class=FastResponse)
async def list_result_ids():
    return get_all_projects_in_results()


@app.get("/results/{project_id}", response_class=FastResponse)
async def list_project_ids(project_id: str):
    return [dict(x, id=x["_id"]) for x in get_all_result_ids_for_project(project_id)]


async def cache_request(request_id):
    if request_id not in cache:
        cache[request_id] = get_result_for_id(request_id)["interpretedTerms"]
    results = cache[request_id]
    return results


@app.get("/results/{project_id}/{request_id}/maxcounts", response_class=FastResponse)
async def maximum_counts_for_id(
    project_id: str,
    request_id: str,
):
    results = await cache_request(request_id)
    part_counts: defaultdict[int] = defaultdict(int)
    for result in results:
        for document_id, data in result["quantities"].items():
            part_counts[document_id] = (
                data["count"]
                if data["count"] > part_counts[document_id]
                else part_counts[document_id]
            )
    return FastResponse(part_counts)


@app.get("/results/{project_id}/{request_id}", response_class=FastResponse)
async def results_for_id(
    project_id: str,
    request_id: str,
    skip: int = 0,
    limit: int = sys.maxsize,
):
    if limit == 0:
        return []

    results = await cache_request(request_id)
    if (limit < 0 or limit > len(results)) and skip == 0:
        return FastResponse(results)

    return FastResponse(
        [
            results[result_id]
            for result_id in range(
                skip if skip < len(results) else len(results) - 1,
                skip + limit if (skip + limit) <= len(results) else len(results),
            )
        ]
    )


@app.get("/results/{project_id}/{request_id}/{result_id}", response_class=FastResponse)
async def results_for_result_id(project_id: str, request_id: str, result_id: int):
    results = await cache_request(request_id)
    if result_id < len(results) or len(results) == -1:
        return FastResponse(results[result_id])
    else:
        return ""


# Finally, mount webpage for root.
app.mount(
    "/",
    StaticFiles(
        directory=os.path.join(os.path.dirname(__file__), "static/welcomePage"),
        html=True,
    ),
    name="landing",
)
