from decouple import config
from pymongo import MongoClient
from pymongo.collection import Collection

database = None
parts: Collection = None
taxonomies: Collection = None
results: Collection = None


def init_database():
    connection_url = (
        f"mongodb+srv://{config('MONGO_USER')}:{config('MONGO_PASS')}"
        "@cls-cps.oe5u2ie.mongodb.net/?retryWrites=true&w=majority"
    )
    global database, parts, taxonomies, results
    database = MongoClient(connection_url)["cls_cps"]
    parts = database["parts"]
    taxonomies = database["taxonomies"]
    results = database["results"]


def upsert_part(part: dict):
    global parts
    parts.replace_one({"_id": part["_id"]}, part, upsert=True)


def upsert_taxonomy(taxonomy: dict):
    global taxonomies
    taxonomies.replace_one({"_id": taxonomy["_id"]}, taxonomy, upsert=True)


def upsert_result(result: dict):
    global results
    results.replace_one({"_id": result["_id"]}, result, upsert=True)


def get_all_parts_for_project(forge_project_id: str):
    global parts
    return parts.find({"meta.forgeProjectId": forge_project_id})


def get_all_projects_in_results():
    global results
    return results.distinct("forgeProjectId")


def get_all_result_ids_for_project(forge_project_id: str):
    global results
    return results.find({"forgeProjectId": forge_project_id}, {"interpretedTerms": 0})


def get_result_for_id(result_id: str):
    global results
    return results.find_one({"_id": result_id})


def get_taxonomy_for_project(forge_project_id: str):
    global taxonomies
    return taxonomies.find_one({"_id": forge_project_id})
