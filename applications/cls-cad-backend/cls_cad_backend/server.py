import mimetypes
import os
import sys
from collections import defaultdict
from datetime import datetime
from timeit import default_timer as timer

from cls_cad_backend.database.commands import (
    get_all_projects_in_results,
    get_all_result_ids_for_project,
    get_result_for_id_in_project,
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
    suffix_and_merge_taxonomy,
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
    """
    Takes a part payload in JSON form and inserts it into the database as is. It is indexed by a unique ID, usually the
    Fusion 360 file identifier.

    :param payload: The payload containing project, folder and part ids, as well as type information.
    :return: Returns "OK" when successful, else returns a 422 response code if payload didn't pass validation.
    """
    upsert_part(payload.model_dump(by_alias=True))
    print(payload.model_dump(by_alias=True))
    return "OK"


@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: TaxonomyInf,
) -> str:
    """
    Takes a taxonomy payload in JSON form and inserts it into the database as is. It is indexed by a unique ID, usually
    the Fusion 360 project identifier.

    :param payload: The payload containing the taxonomy, split into three distinct taxonomies.
    :return: Returns "OK" when successful, else returns a 422 response code if payload didn't pass validation.
    """
    upsert_taxonomy(payload.model_dump(by_alias=True))
    return "OK"


@app.post("/request/assembly")
async def synthesize_assembly(
    payload: SynthesisRequestInf, background_tasks: BackgroundTasks
):
    """
    Takes a payload describing a synthesis request as JSON. Builds a repository and a query and then executes PiCLS.
    Results (if present) get enumerated (up to 100) and then post-processed into assembly instructions for the
    Fusion 360 Add-In to execute. A background task inserts the results bundled in a single JSON Object into the
    database.

    :param payload: The payload containing target types and constraints for the synthesis request.
    :param background_tasks: The background tasks to asynchronously insert into the database.
    :return: A JSON containing a result id and metadata, or FAIL if there are no results.
    """
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
    taxonomy = Subtypes(
        suffix_and_merge_taxonomy(get_taxonomy_for_project(payload.forgeProjectId))
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
        subtypes=taxonomy,
        literals=literals,
    )

    result = gamma.inhabit(query)

    terms = []
    terms.extend(enumerate_terms(query, result, max_count=100))
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
    """
    Retrieves the taxonomy and inverts subtype and supertype (Add-In uses Keys as Supertypes, CLS uses Keys as Subtype,
    for multiple inheritance).

    :param project_id: The project id for which a taxonomy should be retrieved.
    :return: The inverted taxonomy for the project id if present. If not present, an empty default taxonomy.
    """
    return invert_taxonomy(get_taxonomy_for_project(project_id))


@app.get("/results", response_class=FastResponse)
async def list_result_ids():
    """
    Lists all project ids for which synthesis results are found in the database.

    :return: The list of project ids. An empty list if no results exist.
    """
    return get_all_projects_in_results()


@app.get("/results/{project_id}", response_class=FastResponse)
async def list_project_ids(project_id: str):
    """
    Lists all result metadata for a specific project id.

    :param project_id: The project id for which to list metadata.
    :return: A list of JSON objects describing the individual results. Each object has an "id" key.
    """
    return [dict(x, id=x["_id"]) for x in get_all_result_ids_for_project(project_id)]


async def cache_request(request_id, project_id: str):
    """
    Caches a specific synthesis result. Since these can be several Mb of JSON data, this avoids unnecessary database
    accesses.

    :param project_id: The id of the project of the result to be cached.
    :param request_id: The id of the result to be cached.
    :return: The JSON data of the result.
    """
    if f"{request_id}_{project_id}" not in cache:
        cache[f"{request_id}_{project_id}"] = get_result_for_id_in_project(
            request_id, project_id
        )["interpretedTerms"]
    results = cache[f"{request_id}_{project_id}"]
    return results


@app.get("/results/{project_id}/{request_id}/maxcounts", response_class=FastResponse)
async def maximum_counts_for_id(
    project_id: str,
    request_id: str,
):
    """
    Computes the maximum amount of a part across all assemblies contained in a synthesis result.
    This is used to create a template file that contains enough parts to assemble any assembly from the results.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :return: A JSON object containing all the maximum counts. "Invalid" if the request or project ids were invalid.
    """
    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
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
    """
    Returns the assemblies contained in a synthesis result.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :param skip: How many assemblies to skip from the start.
    :param limit: How many assemblies to return.
    :return: A list of assemblies of size up to limit. "Invalid" if the request or project ids were invalid.
    """
    if limit == 0:
        return []

    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
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
    """
    Returns a single assembly from a synthesis result.
    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :param result_id: The index of the assembly in the result.
    :return: The assembly, or "" if the index did not exist. "Invalid" if the request or project ids were invalid.
    """
    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
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
