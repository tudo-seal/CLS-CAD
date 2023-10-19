import json
import os
import traceback

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ..assembleresult import entry as assemble_result

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display"
CMD_NAME = "Toggle Display"
CMD_DESCRIPTION = "Toggle Display of Typing (default off)."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "VIZ"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
DISABLED_ICON_FOLDER = os.path.join(os.path.dirname(__file__), "disabled-resources", "")

local_handlers = []
isDisplaying = False


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.inputChanged, command_input_changed, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )


def command_execute_preview(args: adsk.core.CommandEventHandler):
    return


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Execute Event")
    if assemble_result.NO_GRAPHICS:
        return

    global isDisplaying
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if config.custom_graphics_displaying:
        for i in range(design.rootComponent.customGraphicsGroups.count):
            design.rootComponent.customGraphicsGroups.item(0).deleteMe()
            config.custom_graphics_displaying = False

    else:
        graphics = design.rootComponent.customGraphicsGroups.add()
        for jointTyping in design.findAttributes("CLS-INFO", "UUID"):
            try:
                jo = jointTyping.parent
                jo_uuid = jo.attributes.itemByName("CLS-INFO", "UUID").value

                tmatrix = adsk.core.Matrix3D.create()
                tmatrix.setWithCoordinateSystem(
                    jo.geometry.origin,
                    jo.geometry.secondaryAxisVector,
                    jo.geometry.thirdAxisVector,
                    jo.geometry.primaryAxisVector,
                )
                # ToDo: Also respect x and y offsets
                offset = jo.geometry.primaryAxisVector.copy()
                offset.normalize()
                offset.scaleBy(
                    (1 if not jo.isFlipped else -1)
                    * ((jo.offsetZ.value if jo.offsetZ else 0) + 0.05)
                )
                offset.add(tmatrix.translation)
                tmatrix.translation = offset
                custom_text = graphics.addText(
                    f'Requires: {"∩".join([config.inverted_mappings["formats"][x] for x in json.loads(jo.attributes.itemByName("CLS-JOINT", "RequiresFormats").value)] + [config.inverted_mappings["parts"][x] for x in json.loads(jo.attributes.itemByName("CLS-JOINT", "RequiresParts").value)] + [config.inverted_mappings["attributes"][x] for x in json.loads(jo.attributes.itemByName("CLS-JOINT", "RequiresAttributes").value)]) or "None"}\n Provides: {"∩".join([config.inverted_mappings["formats"][x] for x in json.loads(jo.attributes.itemByName("CLS-JOINT", "ProvidesFormats").value)]) or "None"}',
                    "Courier New",
                    0.2,
                    tmatrix,
                )
                config.custom_text_dict[jo_uuid] = custom_text
            except:
                traceback.print_exc()
        config.custom_graphics_displaying = True


def command_preview(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    futil.log(
        f"{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}"
    )


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
