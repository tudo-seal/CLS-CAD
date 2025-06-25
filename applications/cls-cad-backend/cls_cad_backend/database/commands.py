import configparser
import os
import zipfile
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno, showerror, showinfo
from tkinter.simpledialog import askstring

from montydb import MontyClient, set_storage
from pymongo import MongoClient, errors
from pymongo.collection import Collection

database: MontyClient | MongoClient
parts: Collection = None
taxonomies: Collection = None
results: Collection = None
storage_engine = "flatfile"


def init_database():  # pragma: no cover
    """
    Initialize the database for the backend. This can either be a remote MongoDB
    instance, or a local MontyDB instance. The configuration is done via the
    config.ini in this folder. If no configuration exists, the user is prompted
    graphically to create one.

    :return:
    """
    global database, parts, taxonomies, results
    application_path = os.path.dirname(__file__)
    config_path = os.path.join(application_path, "config.ini")
    container_path = os.path.join(application_path, "container")
    config = configparser.ConfigParser()
    if not os.path.exists(config_path) and not os.path.exists(container_path):
        is_remote = askyesno(
            "Connect to remote DB?",
            "Do you want to connect to a hosted MongoDB instance?",
        )
        connection_url: str | None = ""
        if is_remote:
            connection_url = askstring(
                "Remote URL",
                "Please enter the connection url (with user and password, stored locally in plain text): ",
            )
            try:
                database = MongoClient(connection_url, serverSelectionTimeoutMS=2000)
                database.server_info()
            except errors.ServerSelectionTimeoutError as err:
                showerror("Connection Error", "Could not connect to database. Exiting.")
                exit(0)
        else:
            database = MontyClient(os.path.join(application_path, "db"))
            if askyesno("Import", "Import an existing database?"):
                import_data = askopenfilename()
                if import_data:
                    with zipfile.ZipFile(import_data, "r") as zip_ref:
                        zip_ref.extractall(os.path.join(application_path, "db"))
                    set_storage(
                        os.path.join(application_path, "db"),
                        storage=storage_engine,
                        use_bson=True,
                        map_size="1073741824",
                    )
                else:
                    showinfo(
                        "Import", "No file selected, continuing with empty database"
                    )
        config["db"] = {"is_remote": is_remote, "connection_url": connection_url}
        with open(config_path, "w") as configfile:  # save
            config.write(configfile)
    elif os.path.exists(
        container_path
    ):  # pragma: no cover (don't check for docker image functionality, we probably want separate tests for that)
        set_storage(
            os.path.join(application_path, "db"),
            storage=storage_engine,
            use_bson=True,
            map_size="1073741824",
        )
        database = MontyClient(os.path.join(application_path, "db"))
    else:
        config.read(config_path)
        if config["db"]["is_remote"] and config["db"]["connection_url"] != "":
            try:
                database = MongoClient(
                    config["db"]["connection_url"], serverSelectionTimeoutMS=2000
                )
                database.server_info()
            except errors.ServerSelectionTimeoutError as err:
                showerror("Connection Error", "Could not connect to database. Exiting.")
                exit(0)
        else:
            set_storage(
                os.path.join(application_path, "db"),
                storage=storage_engine,
                use_bson=True,
                map_size="1073741824",
            )
            database = MontyClient(os.path.join(application_path, "db"))

    database = database["cls_cad_backend"]
    parts = database["parts"]
    taxonomies = database["taxonomies"]
    results = database["results"]


def switch_to_test_database() -> None:
    """
    For running test cases, a separate MontyDB instance is gets created by this method
    and attached to.

    :return:
    """
    global database, parts, taxonomies, results
    application_path = os.path.dirname(__file__)
    set_storage(
        os.path.join(application_path, "test_db"),
        storage=storage_engine,
        use_bson=True,
        map_size="1073741824",
    )
    database = MontyClient(os.path.join(application_path, "test_db"))
    database = database["cls_cad_backend"]
    parts = database["parts"]
    taxonomies = database["taxonomies"]
    results = database["results"]


def upsert_part(part: dict) -> None:
    """
    Inserts a part into the database, indexed on its _id.

    :param part: The JSON of the part, containing an _id field.
    :return:
    """
    global parts
    parts.replace_one({"_id": part["_id"]}, part, upsert=True)


def upsert_taxonomy(taxonomy: dict) -> None:
    """
    Inserts a taxonomy into the database, indexed on its _id.

    :param taxonomy: The JSON of the taxonomy, containing an _id field.
    :return:
    """
    global taxonomies
    taxonomies.replace_one({"_id": taxonomy["_id"]}, taxonomy, upsert=True)


def upsert_result(result: dict) -> None:
    """
    Inserts a result into the database, indexed on its _id.

    :param result: The JSON of the result, containing an _id field.
    :return:
    """
    global results
    results.replace_one({"_id": result["_id"]}, result, upsert=True)


def get_all_parts_for_project(forge_project_id: str):
    """
    Retrieves all part JSONs that match the corresponding project id.

    :param forge_project_id: The project id to match.
    :return: The set of matching part JSONs.
    """
    global parts
    return parts.find({"meta.forgeProjectId": forge_project_id})


def get_all_projects_in_results():
    """
    Return all project ids that have results.

    :return: The set of all project ids.
    """
    global results
    return results.distinct("forgeProjectId")


def get_all_result_ids_for_project(forge_project_id: str):
    """
    Get all results for a specific project id.

    :param forge_project_id: The project id to get results for.
    :return: The set of result JSON files.
    """
    global results
    return results.find(
        {"forgeProjectId": forge_project_id}, {"interpretedTerms": 0}
    ).sort("timestamp", -1)


def get_result_for_id_in_project(result_id: str, forge_project_id: str):
    """
    Get a single result contained within a specific project.

    :param result_id: The id of the results to retrieve.
    :param forge_project_id: The id of the project the result should be present in.
    :return: The JSON of the result to retrieve, or None if it does not exist.
    """
    global results
    return results.find_one({"_id": result_id, "forgeProjectId": forge_project_id})


def get_taxonomy_for_project(forge_project_id: str):
    """
    Retrieve the taxonomy associated in the database with a specific project id.

    :param forge_project_id: The id of the project to get the taxonomy for.
    :return: The taxonomy or None, if it does not exist.
    """
    global taxonomies
    return taxonomies.find_one({"_id": forge_project_id})
