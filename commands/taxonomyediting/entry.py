import json
import adsk.core
import os
from ...lib import fusion360utils as futil
from ... import config
from datetime import datetime

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_taxonomy_edit'
CMD_NAME = 'Edit Taxonomy'
CMD_DESCRIPTION = 'Allows selecting or adding new taxonomy from the taxonomy tree'
PALETTE_NAME = 'Taxonomy'
IS_PROMOTED = True

# Using "global" variables by referencing values from /config.py
PALETTE_ID = "partsTaxonomyBrowser_tax"

# Specify the full path to the local html. You can also use a web URL
# such as 'https://www.autodesk.com/'
PALETTE_URL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', 'html', 'index.html')

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace('\\', '/')

# Set a default docking behavior for the palette
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'TAXONOMY'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME,
                                                        CMD_DESCRIPTION,
                                                        ICON_FOLDER)

    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    palette = ui.palettes.itemById(PALETTE_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()
    # Delete the Palette
    if palette:
        palette.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}: Command created event.')

    palettes = ui.palettes
    palette = palettes.itemById(PALETTE_ID)
    if palette is None:
        palette = palettes.add(id=PALETTE_ID,
                               name=PALETTE_NAME,
                               htmlFileURL=PALETTE_URL,
                               isVisible=True,
                               showCloseButton=True,
                               isResizable=True,
                               width=1200,
                               height=800,
                               useNewWebBrowser=True)
        futil.add_handler(palette.closed, palette_closed)
        futil.add_handler(palette.navigatingURL, palette_navigating)
        futil.add_handler(palette.incomingFromHTML, palette_incoming)
    else:
        palette = ui.palettes.itemById(PALETTE_ID)
        # ADSK was injected, so now we send the payload
        taxonomy_data_message = config.taxonomies["parts"]
        palette.sendInfoToHTML("taxonomyDataMessage",
                               json.dumps(taxonomy_data_message))
    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)
    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}: Command execute event.')


def palette_closed(args: adsk.core.UserInterfaceGeneralEventArgs):

    futil.log(f'{CMD_NAME}: Palette was closed.')


def palette_navigating(args: adsk.core.NavigationEventArgs):
    futil.log(f'{CMD_NAME}: Palette navigating event.')

    url = args.navigationURL

    log_msg = f"User is attempting to navigate to {url}\n"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    if url.startswith("http"):
        args.launchExternally = True


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f'{CMD_NAME}: Palette incoming event.')

    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    if message_action == 'messageFromPalette':
        arg1 = message_data.get('arg1', 'arg1 not sent')
        arg2 = message_data.get('arg2', 'arg2 not sent')

    if message_action == 'readyNotification':
        palette = ui.palettes.itemById(PALETTE_ID)
        # ADSK was injected, so now we send the payload
        taxonomy_data_message = config.taxonomies["parts"]
        palette.sendInfoToHTML("taxonomyDataMessage",
                               json.dumps(taxonomy_data_message))
    # Return value.
    now = datetime.now()
    current_time = now.strftime('%H:%M:%S')
    html_args.returnData = f'OK - {current_time}'


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}: Command destroy event.')

    global local_handlers
    local_handlers = []
