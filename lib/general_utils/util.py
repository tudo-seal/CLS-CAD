import json
import os
from pathlib import Path

import adsk

from ... import config

ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")


def wrapped_forge_as_array(forge_object, progress_dialog=None):
    """
    Attempts to get array from forge object until it succeeds.
    What can I say, for some reason that part of the API is super flaky.

    Args:
        forge_object:

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
            request = forge_object.asArray()
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


def load_project_taxonomy_to_config():
    app = adsk.core.Application.get()
    active_id = (
        app.activeDocument.dataFile.parentProject.id
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.id
    )
    path_part_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            active_id,
            "parts.taxonomy",
        )
    )
    path_format_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            active_id,
            "formats.taxonomy",
        )
    )
    path_attribute_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            active_id,
            "attributes.taxonomy",
        )
    )

    if path_part_taxonomy.is_file():
        with open(path_part_taxonomy) as json_file:
            config.taxonomies["parts"] = json.load(json_file)
    if path_format_taxonomy.is_file():
        with open(path_format_taxonomy) as json_file:
            config.taxonomies["formats"] = json.load(json_file)
    if path_attribute_taxonomy.is_file():
        with open(path_attribute_taxonomy) as json_file:
            config.taxonomies["attributes"] = json.load(json_file)


def winapi_path(dos_path, encoding=None):
    if not isinstance(dos_path, str) and encoding is not None:
        dos_path = dos_path.decode(encoding)
    path = os.path.abspath(dos_path)
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path
