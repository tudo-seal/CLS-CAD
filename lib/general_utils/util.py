import json
import os
import urllib
import urllib.request
from collections import defaultdict
from collections.abc import Callable
from urllib.error import HTTPError

import adsk

from ... import config
from ..fusion360utils import app

ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")


def wrapped_forge_call(forge_call: Callable, progress_dialog=None):
    """
    Attempts to get array from forge object until it succeeds.
    What can I say, for some reason that part of the API is super flaky.

    Args:
        forge_call:

    Returns:

    """
    success = False
    once = True
    if progress_dialog is not None:
        previous_max = progress_dialog.maximumValue
        previous_progress = progress_dialog.progressValue
        previous_msg = progress_dialog.message
    while not success:
        try:
            request = forge_call()
            success = True
        except RuntimeError:
            success = False
            if (progress_dialog is not None) and once:
                once = False
                progress_dialog.message = (
                    progress_dialog.message + "\n\nWaiting for ADSK Forge..."
                )
                progress_dialog.maximumValue = 1000
                progress_dialog.progressValue = 0
            if progress_dialog is not None:
                progress_dialog.progressValue += (
                    1 if progress_dialog.progressValue < 999 else -1
                )
    if progress_dialog is not None:
        progress_dialog.maximumValue = previous_max
        progress_dialog.progressValue = previous_progress
        progress_dialog.message = previous_msg
    return request


def invert_sub_taxonomy(sub_taxonomy):
    subtypes = defaultdict(list)
    for key, values in sub_taxonomy.items():
        for value in values:
            subtypes[value].append(key)
    return subtypes


def load_project_taxonomy_to_config():
    app = adsk.core.Application.get()
    active_id = (
        app.activeDocument.dataFile.parentProject.id
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.id
    )

    config.taxonomies = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(f"{config.SERVER_URL}/data/taxonomy/{active_id}")
        )
        .read()
        .decode("utf-8")
    )


def winapi_path(dos_path, encoding=None):
    if not isinstance(dos_path, str) and encoding is not None:
        dos_path = dos_path.decode(encoding)
    path = os.path.abspath(dos_path)
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def update_taxonomy_in_backend():
    payload_dict = create_backend_taxonomy()
    req = urllib.request.Request("http://127.0.0.1:8000/submit/taxonomy")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    payload = json.dumps(payload_dict, indent=4).encode("utf-8")
    req.add_header("Content-Length", len(payload))
    try:
        response = urllib.request.urlopen(req, payload)
        print(response)
    except HTTPError as err:
        print(err.code)
        print(err.reason)


def create_backend_taxonomy():
    """
    Creates a taxonomy in the format that the backend expects. Each individual taxonomy is suffixed with its identifier,
    guaranteeing that namespaces don't overlap. The Forge ProjectID is also added to the JSON.

    Returns: The created JSON/dict.

    """
    suffixed_taxonomy = {}
    for key, value in config.taxonomies.items():
        suffixed_taxonomy[key] = invert_sub_taxonomy(value)
    payload_dict = {
        "_id": app.activeDocument.dataFile.parentProject.id,
        "taxonomies": suffixed_taxonomy,
        "forgeProjectId": app.activeDocument.dataFile.parentProject.id
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.id,
    }
    return payload_dict
