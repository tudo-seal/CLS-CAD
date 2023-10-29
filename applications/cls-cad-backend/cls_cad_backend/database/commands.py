import configparser
import os
import platform
import sys
import zipfile
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno, showerror, showinfo
from tkinter.simpledialog import askstring

from montydb import MontyClient, set_storage
from pymongo import MongoClient, errors
from pymongo.collection import Collection

database = None
parts: Collection = None
taxonomies: Collection = None
results: Collection = None
storage_engine = "flatfile" if any(platform.win32_ver()) else "lightning"


def init_database():
    global database, parts, taxonomies, results
    if "__compiled__" in globals():
        application_path = os.path.dirname(sys.argv[0])
    elif __file__:
        application_path = os.path.dirname(__file__)
    config_path = os.path.join(application_path, "config.ini")
    container_path = os.path.join(application_path, "container")
    config = configparser.ConfigParser()
    if not os.path.exists(config_path) and not os.path.exists(container_path):
        is_remote = askyesno(
            "Connect to remote DB?",
            "Do you want to connect to a hosted MongoDB instance?",
        )
        connection_url = ""
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
    elif os.path.exists(container_path):
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
    return results.find(
        {"forgeProjectId": forge_project_id}, {"interpretedTerms": 0}
    ).sort("timestamp", -1)


def get_result_for_id(result_id: str):
    global results
    return results.find_one({"_id": result_id})


def get_taxonomy_for_project(forge_project_id: str):
    global taxonomies
    return taxonomies.find_one({"_id": forge_project_id})
