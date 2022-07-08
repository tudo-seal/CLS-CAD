import json
import adsk.core
import os
import inspect
import copy
from ...lib import fusion360utils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display'
CMD_NAME = 'Toggle Display'
CMD_DESCRIPTION = 'Toggle Display of Typing (default off).'
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'VIZ'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resources
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

isDisplaying = False


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME,
                                                        CMD_DESCRIPTION,
                                                        ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)

    # UI Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    # Clean entire Panel
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # Handlers
    futil.add_handler(args.command.execute,
                      command_execute,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged,
                      command_input_changed,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview,
                      command_preview,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.destroy,
                      command_destroy,
                      local_handlers=local_handlers)

    # No UI


def command_execute_preview(args: adsk.core.CommandEventHandler):
    return


def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs
    print("Executed")
    global isDisplaying
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if config.custom_graphics_displaying:
        for i in range(design.rootComponent.customGraphicsGroups.count):
            print("Deleted")
            design.rootComponent.customGraphicsGroups.item(0).deleteMe()
            config.custom_graphics_displaying = False
    else:
        graphics = design.rootComponent.customGraphicsGroups.add()
        for jointTyping in design.findAttributes("CLS-INFO", "UUID"):
            jo = jointTyping.parent
            jo_uuid = jo.attributes.itemByName("CLS-INFO", "UUID").value
            tmatrix = adsk.core.Matrix3D.create()
            tmatrix.setWithCoordinateSystem(jo.geometry.origin,
                                            jo.geometry.secondaryAxisVector,
                                            jo.geometry.thirdAxisVector,
                                            jo.geometry.primaryAxisVector)
            offset = jo.geometry.primaryAxisVector.copy()
            offset.normalize()
            offset.scaleBy(0.05)
            offset.add(tmatrix.translation)
            tmatrix.translation = offset
            custom_text = graphics.addText(
                f'Requires: {jo.attributes.itemByName("CLS-JOINT", "RequiresString").value}\n Provides: {jo.attributes.itemByName("CLS-JOINT", "ProvidesString").value or "None"}',
                'Courier New', 0.2, tmatrix)
            config.custom_text_dict[jo_uuid] = custom_text
            config.custom_graphics_displaying = True

    # Recompute or hide all custom graphic objects


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    futil.log(
        f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}'
    )


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')