import os

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import json

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_download_taxonomy"
CMD_NAME = "Download Taxonomy"
CMD_DESCRIPTION = "Download Taxonomy to current workspace"
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "TAXONOMY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

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
    file_dlg = ui.createFileDialog()
    file_dlg.isMultiSelectEnabled = True
    file_dlg.filter = "*.taxonomy"
    file_dlg.title = "Export taxonomy to file (for sharing)"
    dlg_result = file_dlg.showSave()
    if dlg_result == adsk.core.DialogResults.DialogOK:
        json.dump(
            {"taxonomies": config.taxonomies, "mappings": config.mappings},
            open(file_dlg.filename, "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=4,
        )
    else:
        return


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
