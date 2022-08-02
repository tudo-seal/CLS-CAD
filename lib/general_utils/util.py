import json
import os
from pathlib import Path

import adsk

from ... import config

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def load_project_taxonomy_to_config():
    app = adsk.core.Application.get()
    path_part_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            app.activeDocument.dataFile.parentProject.id,
            "parts.taxonomy",
        )
    )
    path_format_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            app.activeDocument.dataFile.parentProject.id,
            "formats.taxonomy",
        )
    )
    path_attribute_taxonomy = Path(
        os.path.join(
            ROOT_FOLDER,
            "Taxonomies",
            "CAD",
            app.activeDocument.dataFile.parentProject.id,
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
