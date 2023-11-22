import adsk.core

from ...lib import fusion360utils as futil
from ...lib.general_utils import config, load_project_taxonomy_to_config, os

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_manage_part"
CMD_NAME = "Manage Part"
CMD_DESCRIPTION = "Annotate Parts with Cost and Availability information."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "MANAGE"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []


def start():
    """
    Creates the promoted "Manage Part" command in the CLS-CAD tab.

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
cost_value_input = adsk.core.ValueInput.cast(None)
availability_value_input = adsk.core.FloatSliderCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers all important
    handlers for the command.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    global cost_value_input, availability_value_input

    futil.log(f"{CMD_NAME} Command Created Event")

    load_project_taxonomy_to_config()

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


def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It persists the
    configured cost and availability in the rootComponents attributes.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global cost_value_input, availability_value_input
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


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Logs that the command was destroyed (window closed). Currently, does not clean up
    anything.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    global local_handlers, provides_attributes, provides_parts
    provides_parts = []
    provides_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
