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
IS_PROMOTED = False
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []
request_content = []
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


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers all important
    handlers for the command.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    global request_content
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )

    # Register the command inputs

    request_content = []  # result, synthesis_vector, experiment_id

    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    (experiment_id, cancelled) = ui.inputBox(
            "Please enter experiment id to update bo for",
            "Update Optimizer for experiment ID",
            "",
    )
    if cancelled:
        return

    (vector_used, cancelled) = ui.inputBox(
            "Please enter the vector used for the experiment (comma separated, e.g. 1,0,1,1,0,0,1,0)",
            "Update Optimizer with vector used",
            "",
    )
    vector_used = [int(x) for x in vector_used.split(",") if x.isdigit()]
    if cancelled:
        return

    (result_score, cancelled) = ui.inputBox(
            "Please enter the result score for the experiment",
            "Update Optimizer with result score",
            "",
    )
    if cancelled:
        return
    request_content = [
        float(result_score),
        vector_used,
        experiment_id
    ]

def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global request_content
    request_dict = {
        "result": request_content[0],
        "synthesis_vector": request_content[1],
        "experiment_id": request_content[2],
    }
    payload = json.dumps(
        request_dict,
        indent=4,
    ).encode("utf-8")
    print("Send request")
    print(request_dict)
    req = urllib.request.Request("http://127.0.0.1:8000/bo/update-with-result")
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
    global local_handlers, request_attributes, request_parts, request_content
    request_parts = []
    request_attributes = []
    local_handlers = []
    request_content = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
