import os
import urllib
from datetime import datetime

import adsk.core

from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    config,
    json
)

app = adsk.core.Application.get()
ui = app.userInterface
# TODO unused
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_launch_bo"
CMD_NAME = "Launch BO Backend"
CMD_DESCRIPTION = "Launches the Bayesian Optimization Framework in Backend"
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
PARTTYPES_ID = "partsTaxonomyBrowser_Part"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser_Part"
PROP_FORMATS_ID = "propformatsTaxonomyBrowser_Part"
PROP_PARTS_ID = "proppartsTaxonomyBrowser_Part"
PROP_ATTRIBUTES_ID = "propattributesTaxonomyBrowser_Part"
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
    global experiment_id_box_input

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

    experiment_id_box_input = inputs.addValueInput(
        "experimentId",
        "Experiment Id",
        "",
        adsk.core.ValueInput.createByString("" + str(datetime.now().timestamp()) + "")
    )

def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global experiment_id_box_input
    app = adsk.core.Application.get()
    project_id = app.activeDocument.dataFile.parentProject.id if app.activeDocument.dataFile is not None else app.data.activeProject.id
    experiment_id = experiment_id_box_input.value
    request_dict = {
        "experimentId": experiment_id,
        "forgeProjectId": project_id,
    }
    payload = json.dumps(
        request_dict,
        indent=4,
    ).encode("utf-8")
    print("Send request")
    print(request_dict)
    req = urllib.request.Request(f"http://127.0.0.1:8000/bo/{project_id}/{experiment_id}/init-bo-machine")
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
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
