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

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_request_current_optimal_vector"
CMD_NAME = "Request Current Optimal Vector"
CMD_DESCRIPTION = "Requests the current optimal vector for synthesis from the backend"
IS_PROMOTED = False
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


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers all important
    handlers for the command.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    global experiment_id

    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    (experiment_id, cancelled) = ui.inputBox(
            "Please enter experiment id to get new optimal vector for synthesis",
            "Request Current Optimal Vector",
            "",
    )
    if cancelled:
        return

def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global experiment_id
    app = adsk.core.Application.get()
    project_id = app.activeDocument.dataFile.parentProject.id if app.activeDocument.dataFile is not None else app.data.activeProject.id
    print("Send request")
    req = urllib.request.Request(f"http://127.0.0.1:8000/bo/{experiment_id}/optimal-vector")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    response = urllib.request.urlopen(req)
    print(response.read().decode())
    futil.log(f"Request for optimal vector sent for experiment {experiment_id} returned: {response.read().decode()}")


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Cleans up all collected data after the user has pressed the "Okay" button.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    global experiment_id
    experiment_id = None
    futil.log(f"{CMD_NAME} Command Destroy Event")
