# Here you define the commands that will be added to your add-in.
import os

import adsk.core

from .. import config
from ..lib import fusion360utils as futil
from .assembleresult import entry as assemble_result
from .attributestaxonomyediting import entry as attributes_taxonomy_editing
from .checkandsubmit import entry as check_and_submit
from .downloadtaxonomy import entry as download_taxonomy
from .exportproject import entry as export_project
from .formatstaxonomyediting import entry as formats_taxonomy_editing
from .jointtyping import entry as joint_typing
from .partmanagement import entry as part_management
from .partstaxonomyediting import entry as parts_taxonomy_editing
from .parttyping import entry as part_typing
from .requestsynthesis import entry as request_synthesis
from .togglecustomgraphics import entry as toggle_custom_graphics
from .typecrawlingproject import entry as type_crawling_project
from .uploadtaxonomy import entry as upload_taxonomy
from .uuidupdatecrawlingproject import entry as uuid_update_crawling_project

app = adsk.core.Application.get()
ui = app.userInterface

ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..")

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    joint_typing,
    part_typing,
    part_management,
    check_and_submit,
    type_crawling_project,
    export_project,
    uuid_update_crawling_project,
    toggle_custom_graphics,
    upload_taxonomy,
    download_taxonomy,
    formats_taxonomy_editing,
    parts_taxonomy_editing,
    attributes_taxonomy_editing,
    request_synthesis,
    assemble_result,
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


def add_panel(
    parent_tab: adsk.core.ToolbarTab, panel_id: str, panel_name: str
) -> adsk.core.ToolbarPanel:
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

    futil.add_handler(
        app.documentOpened, application_document_opened, local_handlers=local_handlers
    )
    add_panel(main_tab, "TYPES", "Typing Tools")
    add_panel(main_tab, "MANAGE", "Management Tools")
    add_panel(main_tab, "CRAWL", "Setup Tools")
    add_panel(main_tab, "TAXONOMY", "Taxonomy")
    add_panel(main_tab, "VIZ", "Visualisation")
    add_panel(main_tab, "SYNTH_ASSEMBLY", "Synthesis Results")
    for command in commands:
        command.start()


def application_document_opened(args: adsk.core.DocumentEventArgs):
    # Restore custom graphics
    config.custom_graphics_displaying = False
    cmd = ui.commandDefinitions.itemById(
        f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display"
    )
    cmd.execute()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()
