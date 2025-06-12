import os
import urllib
from datetime import datetime

import adsk.core

from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    config,
    json,
    load_project_taxonomy_to_config,
    update_taxonomy_in_backend,
)

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_update_bo"
CMD_NAME = "Update Optimizer"
CMD_DESCRIPTION = "Updates the Bayesian Optimizer with the results from motion planning"
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
PARTTYPES_ID = "partsTaxonomyBrowser_Part"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser_Part"
PROP_FORMATS_ID = "propformatsTaxonomyBrowser_Part"
PROP_PARTS_ID = "proppartsTaxonomyBrowser_Part"
PROP_ATTRIBUTES_ID = "propattributesTaxonomyBrowser_Part"
PALETTE_URL = f"{config.SERVER_URL}/static/unrolledTaxonomyDisplay/index.html"
PALETTE_URL = PALETTE_URL.replace("\\", "/")
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []
request_parts, request_attributes = [], []
counted_parts, counted_attributes, counted_formats = [], [], []
counted_types = {}
selected_text = adsk.core.StringValueCommandInput.cast(None)

def start():
    """
    Creates the promoted "Request Synthesis" command in the CLS-CAD tab.

    Registers the commandCreated handler.
    :return:
    """
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    """
    Removes this command from the CLS-CAD tab along with all others it shares a panel
    with.

    This does not fail, even if the panel is emptied by multiple commands.
    :return:
    """
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    if command_definition:
        command_definition.deleteMe()


joint_origin = adsk.fusion.JointOrigin.cast(None)

type_text_box_input = adsk.core.TextBoxCommandInput.cast(None)
parts_type_selection_browser_input = adsk.core.BrowserCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers all important
    handlers for the command.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    global type_text_box_input, parts_type_selection_browser_input, request_parts, request_attributes, counted_parts, counted_attributes, counted_formats, selected_text

    futil.log(f"{CMD_NAME} Command Created Event")

def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global request_attributes, request_parts
    app = adsk.core.Application.get()
    request_dict = {
        "target": [f"{x}_parts" for x in request_parts]
        + [f"{x}_attributes" for x in request_attributes]
        + [f"Has_{x}_parts" for x in counted_parts]
        + [f"Has_{x}_formats" for x in counted_formats]
        + [f"Has_{x}_attributes" for x in counted_attributes],
        "partCounts": [
            {
                "partNumber": counted_type[1].value,
                "partCountName": "-".join(counted_type[0]),
                "partType": counted_type[0],
            }
            for _, counted_type in counted_types.items()
        ],
        "forgeProjectId": app.activeDocument.dataFile.parentProject.id
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.id,
    }
    payload = json.dumps(
        request_dict,
        indent=4,
    ).encode("utf-8")
    print("Send request")
    print(request_dict)
    req = urllib.request.Request("http://127.0.0.1:8000/request/assembly")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Content-Length", len(payload))
    response = urllib.request.urlopen(req, payload)
    print(response.read().decode())


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Cleans up all collected data after the user has pressed the "Okay" button.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    global local_handlers, request_attributes, request_parts
    request_parts = []
    request_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
