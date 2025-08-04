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

# TODO: open cheapest synthesis as active design -> still outstanding

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_request_synthesis_optmizer"
CMD_NAME = "Request Synthesis Optimizer"
CMD_DESCRIPTION = "Put in a synthesis request and progress optimizer"
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

local_handlers = []
request_parts, request_attributes = [], []
counted_parts, counted_attributes, counted_formats = [], [], []
counted_types = {}
selected_text = adsk.core.StringValueCommandInput.cast(None)
requested_vector = []


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
    global requested_vector
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )

    load_project_taxonomy_to_config()
    # Register the command inputs
    cmd_inputs = args.command.commandInputs

    
    motor_count = cmd_inputs.addIntegerSpinnerCommandInput(
        "Dynamixel_parts", "Motor Count", 0, 7, 1, 1
    )
    extrusions = cmd_inputs.addIntegerSpinnerCommandInput(
        "40mm_attributes", "Extrusion Count", 0, 5, 1, 1
    )
    requested_vector = [
        motor_count.value,
        extrusions.value
    ]


    

def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    cmd = args.firingEvent.sender
    inputs = cmd.commandInputs

    motor_count_input = inputs.itemById("Dynamixel_parts")
    extrusions_input = inputs.itemById("40mm_attributes")

    motor_count = motor_count_input.value
    extrusions = extrusions_input.value

    input_vector = [motor_count, extrusions]

    synthesize_with_vector(input_vector)
    print("DONE")


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Cleans up all collected data after the user has pressed the "Okay" button.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    global requested_vector
    requested_vector = []
    futil.log(f"{CMD_NAME} Command Destroy Event")

def synthesize_with_vector(input_vector):
    """
    This method requests a synthesis from the backend using a predicate vector.
    input_vector[0] = #of Dynamixel motors parts
    input_vector[1] = #of 40mm attributes -> extrusions
    
    :param input_vector: The input vector to use for the synthesis.
    return:
    """
    request_dict = {
        "target": ["Base_parts"],
        "partCounts": [
            {
                "partNumber": input_vector[0],
                "partCountName": "Dynamixel_parts",
                "partType": ["Dynamixel_parts"],
            },
            {
                "partNumber": input_vector[1],
                "partCountName": "40mm_attributes",
                "partType": ["40mm_attributes"]
            }
        ],
        "optimizeAssembly": "True",
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
    response = response.read().decode()
    print(response)
    # if response == "FAIL" tell optimizer bad score
    return response

