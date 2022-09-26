import os
from datetime import datetime
from pathlib import Path

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.cls_python_compat import *
from ...lib.general_utils import *

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_manage_part"
CMD_NAME = "Manage Part"
CMD_DESCRIPTION = "Annotate Parts with Cost and Availability information."
IS_PROMOTED = True

WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "MANAGE"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"


# Resource location
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


joint_origin = adsk.fusion.JointOrigin.cast(None)

# Initializing like this is nice but not necessary I guess
cost_value_input = adsk.core.ValueInput.cast(None)
availability_value_input = adsk.core.FloatSliderCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    global cost_value_input, availability_value_input

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Created Event")

    # Load appropriate taxonomies
    load_project_taxonomy_to_config()

    # Handlers
    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    # futil.add_handler(args.command.inputChanged,
    #                   command_input_changed,
    #                   local_handlers=local_handlers)
    futil.add_handler(
        args.command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.activate, command_activate, local_handlers=local_handlers
    )

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    # UI DEF
    cost_value_input = inputs.addValueInput(
        "costValue",
        "Price per Unit",
        "dol",
        adsk.core.ValueInput.createByString(
            getattr(
                design.rootComponent.attributes.itemByName("CLS-PART", "COST"),
                "value",
                "1.0",
            )
        ),
    )
    availability_value_input = inputs.addFloatSliderCommandInput(
        "availabilityValue", "Projected Availability", "", 0, 100, False
    )
    availability_value_input.valueOne = float(
        getattr(
            design.rootComponent.attributes.itemByName("CLS-PART", "AVAILABILITY"),
            "value",
            "100.0",
        )
    )


def command_execute_preview(args: adsk.core.CommandEventHandler):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)


def command_activate(args: adsk.core.CommandEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    app.log("In command_activate event handler.")


# EXECUTE
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f"{CMD_NAME} Command Execute Event")

    global cost_value_input, availability_value_input
    inputs = args.command.commandInputs
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root_comp = design.rootComponent
    root_comp.attributes.add(
        "CLS-PART",
        "COST",
        f"{cost_value_input.value}",
    )
    print(f"{cost_value_input.value}")
    root_comp.attributes.add(
        "CLS-PART",
        "AVAILABILITY",
        f"{availability_value_input.valueOne}",
    )
    print(f"{availability_value_input.valueOne}")


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, provides_attributes, provides_parts
    provides_parts = []
    provides_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
