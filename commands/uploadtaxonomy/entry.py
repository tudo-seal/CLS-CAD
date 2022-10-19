import os

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import winapi_path

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_upload_taxonomy"
CMD_NAME = "Upload Taxonomy"
CMD_DESCRIPTION = "Upload Taxonomy to current workspace"
IS_PROMOTED = True

WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "TAXONOMY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"

# Resources
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

isDisplaying = False


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
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
    futil.log(f"{CMD_NAME} Command Created Event")

    # Handlers
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

    # No UI


def command_execute_preview(args: adsk.core.CommandEventHandler):
    return


def upload_taxonomy_to_forge(taxonomy_folder, taxonomy_name: str):
    taxonomy_folder.uploadFile(
        winapi_path(
            os.path.join(
                config.ROOT_FOLDER,
                "Taxonomies",
                "CAD",
                app.activeDocument.dataFile.parentProject.id.replace(":", "-"),
                f"{taxonomy_name}.taxonomy",
            )
        )
    )


def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f"{CMD_NAME} Command Execute Event")

    # If file active, use that files project, else use current sidebar project
    root_folder_children = (
        app.activeDocument.dataFile.parentProject.rootFolder.dataFolders
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.rootFolder.dataFolders
    )
    taxonomy_folder = (
        root_folder_children.itemByName("Taxonomies")
        if root_folder_children.itemByName("Taxonomies")
        else root_folder_children.add("Taxonomies")
    )
    upload_taxonomy_to_forge(taxonomy_folder, "attributes")
    upload_taxonomy_to_forge(taxonomy_folder, "parts")
    upload_taxonomy_to_forge(taxonomy_folder, "formats")


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
