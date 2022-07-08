# Here you define the commands that will be added to your add-in.
import json
from pathlib import Path
import adsk.core
import os

from ..lib import fusion360utils as futil
from .. import config

# TODO Import the modules corresponding to the commands you created.
# If you want to add an additional command, duplicate one of the existing directories and import it here.
# You need to use aliases (import "entry" as "my_module") assuming you have the default module named "entry".
from .jointtyping import entry as joint_typing
from .parttyping import entry as part_typing
from .typecrawlingproject import entry as type_crawling_project
from .typecrawlinghub import entry as type_crawling_hub
from .checkAndSubmit import entry as check_and_submit
from .togglecustomgraphics import entry as toggle_custom_graphics
from .taxonomyediting import entry as taxonomy_editing

app = adsk.core.Application.get()
ui = app.userInterface

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    joint_typing,part_typing,check_and_submit,type_crawling_project,
type_crawling_hub,toggle_custom_graphics,taxonomy_editing
]


def add_tab() -> adsk.core.ToolbarTab:
    design_workspace = ui.workspaces.itemById("FusionSolidEnvironment")

    if design_workspace:
        all_design_tabs = design_workspace.toolbarTabs
        if all_design_tabs.count > 0:
            new_tab = all_design_tabs.itemById("CLSCAD")

            if new_tab is None:
                new_tab = all_design_tabs.add("CLSCAD", "CLS-CAD")
            return new_tab
    return None


def add_panel(parent_tab: adsk.core.ToolbarTab, panel_id: str,
             panel_name: str) -> adsk.core.ToolbarPanel:
    new_panel = parent_tab.toolbarPanels.itemById(panel_id)

    if new_panel is None:
        new_panel = parent_tab.toolbarPanels.add(panel_id, panel_name)

    return new_panel


local_handlers = []


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    main_tab = add_tab()
    if not main_tab.isActive:
        main_tab.activate

    path_part_taxonomy = Path(os.path.join(ROOT_FOLDER, "parts.taxonomy"))
    path_format_taxonomy = Path(os.path.join(ROOT_FOLDER, "formats.taxonomy"))
    path_attribute_taxonomy = Path(
        os.path.join(ROOT_FOLDER, "attributes.taxonomy"))

    if path_part_taxonomy.is_file():
        with open(path_part_taxonomy) as json_file:
            config.taxonomies["parts"] = json.load(json_file)
    if path_format_taxonomy.is_file():
        with open(path_format_taxonomy) as json_file:
            config.taxonomies["formats"] = json.load(json_file)
    if path_attribute_taxonomy.is_file():
        with open(path_attribute_taxonomy) as json_file:
            config.taxonomies["attributes"] = json.load(json_file)

    futil.add_handler(app.documentOpened,
                      application_document_opened,
                      local_handlers=local_handlers)
    add_panel(main_tab, "TYPES", "Typing Tools")
    add_panel(main_tab, "CRAWL", "Setup Tools")
    add_panel(main_tab, "TAXONOMY", "Taxonomy")
    add_panel(main_tab, "VIZ", "Visualisation")
    for command in commands:
        command.start()


def application_document_opened(args: adsk.core.DocumentEventArgs):
    # Restore custom graphics
    config.custom_graphics_displaying = False
    cmd = ui.commandDefinitions.itemById(
        f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display')
    cmd.execute()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()