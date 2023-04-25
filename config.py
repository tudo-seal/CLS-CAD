# Application Global Variables
# This module serves as a way to share variables across different
# modules (global variables).
import os

# Flag that indicates to run in Debug mode or not. When running in Debug mode
# more information is written to the Text Command window. Generally, it's useful
# to set this to True while developing an add-in and set it to False when you
# are ready to distribute it.
from collections import defaultdict

from .lib.general_utils import invert_map, load_project_taxonomy_to_config

DEBUG = True

# Gets the name of the add-in from the name of the folder the py file is in.
# This is used when defining unique internal names for various UI elements
# that need a unique name. It's also recommended to use a company name as
# part of the ID to better ensure the ID is unique.
ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = "ACME"
ROOT_FOLDER = os.path.join(os.path.dirname(__file__))
SERVER_URL = "http://127.0.0.1:8000"

# Palettes
taxonomy_palette_id = f"{COMPANY_NAME}_{ADDIN_NAME}_palette_taxonomy"

custom_text_dict = defaultdict(list)
custom_graphics_displaying = False

taxonomies = {}

mappings = {}

try:
    load_project_taxonomy_to_config()
    inverted_mappings = invert_map(mappings)
except:
    pass
