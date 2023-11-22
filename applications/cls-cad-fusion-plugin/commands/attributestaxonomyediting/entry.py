import json
import os
from datetime import datetime

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    invert_map,
    load_project_taxonomy_to_config,
    update_taxonomy_in_backend,
)

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_attributes_taxonomy_edit"
CMD_NAME = "Edit Taxonomy"
CMD_DESCRIPTION = 'Allows editing of the "attributes" taxonomy'
PALETTE_NAME = "Taxonomy"
IS_PROMOTED = True
PALETTE_ID = "attributesTaxonomyBrowser_tax"
PALETTE_URL = f"{config.SERVER_URL}/static/editTaxonomyGraph/index.html"
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "TAXONOMY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []


def start():
    """
    Creates the promoted "Edit Taxonomy" command in the CLS-CAD tab, for the attribute
    taxonomy.

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
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    palette = ui.palettes.itemById(PALETTE_ID)

    if command_control:
        command_control.deleteMe()

    if command_definition:
        command_definition.deleteMe()
    if palette:
        palette.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers execute and
    destroy handlers.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    futil.log(f"{CMD_NAME}: Command created event.")
    load_project_taxonomy_to_config()
    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )


def command_execute(args: adsk.core.CommandEventArgs):
    """
    Executes immediately when the command is clicked in the CLS-CAD tab, since there are
    no inputs. If the palette does not already exist, it is created. The palette is set
    to be visible and docked.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    palettes = ui.palettes
    palette = palettes.itemById(PALETTE_ID)
    if palette is not None:
        palette.deleteMe()
        futil.log("Deleted palette.")

    if palette is None or not palette.isValid:
        palette = palettes.add(
            id=PALETTE_ID,
            name=PALETTE_NAME,
            htmlFileURL=PALETTE_URL,
            isVisible=True,
            showCloseButton=True,
            isResizable=True,
            width=1200,
            height=800,
            useNewWebBrowser=True,
        )
        futil.add_handler(palette.incomingFromHTML, palette_incoming)

    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)
    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True
    futil.log(f"{CMD_NAME}: Command execute event.")


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    """
    Handles incoming messages from the JavaScript portion of the palette. Receives an
    "taxonomyDataMessage" that contains the JSON representation of the attribute
    taxonomy.

    :param html_args: adsk.core.HTMLEventArgs: The received HTML event containing data.
    :return:
    """
    futil.log(f"{CMD_NAME}: Palette incoming event.")

    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    if message_action == "readyNotification":
        palette = ui.palettes.itemById(PALETTE_ID)
        # ADSK was injected, so now we send the payload
        taxonomy_data_message = config.taxonomies["attributes"]
        palette.sendInfoToHTML("taxonomyIDMessage", "attributes")
        palette.sendInfoToHTML("taxonomyDataMessage", json.dumps(taxonomy_data_message))

    if message_action == "taxonomyDataMessage":
        taxonomy_id = "attributes"
        config.taxonomies[taxonomy_id] = message_data
        update_taxonomy_in_backend()

    if message_action == "renameDataNotification":
        taxonomy_id = "attributes"
        print("Updating mapping")
        config.mappings[taxonomy_id][message_data[1]] = config.mappings[
            taxonomy_id
        ].pop(message_data[0])
        config.inverted_mappings = invert_map(config.mappings)
        update_taxonomy_in_backend()

    # Return value.
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Logs the command terminating. This is instantly the case upon clicking, as the
    command only opens the palette.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    futil.log(f"{CMD_NAME}: Command destroy event.")

    global local_handlers
    local_handlers = []
