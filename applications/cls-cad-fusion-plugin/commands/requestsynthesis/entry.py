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

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_request_synthesis"
CMD_NAME = "Request Synthesis"
CMD_DESCRIPTION = "Put in a synthesis request"
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
PARTTYPES_ID = "partsTaxonomyBrowser_Part"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser_Part"
PROP_FORMATS_ID = "propformatsTaxonomyBrowser_Part"
PROP_PARTS_ID = "proppartsTaxonomyBrowser_Part"
PROP_ATTRIBUTES_ID = "propattributesTaxonomyBrowser_Part"
PALETTE_URL = f"{config.SERVER_URL}/static/unrolledTaxonomyDisplay/index.html"
PALETTE_URL = PALETTE_URL.replace("\\", "/")
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []
request_parts, request_attributes = [], []
propagate_parts, propagate_attributes, propagate_formats = [], [], []


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


joint_origin = adsk.fusion.JointOrigin.cast(None)

type_text_box_input = adsk.core.TextBoxCommandInput.cast(None)
parts_type_selection_browser_input = adsk.core.BrowserCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    global type_text_box_input, parts_type_selection_browser_input, request_parts, request_attributes, propagate_parts, propagate_attributes, propagate_formats

    futil.log(f"{CMD_NAME} Command Created Event")

    load_project_taxonomy_to_config()

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.incomingFromHTML, palette_incoming, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.activate, command_activate, local_handlers=local_handlers
    )

    request_attributes = []
    request_parts = []
    propagate_parts, propagate_attributes, propagate_formats = [], [], []
    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    request_tab = inputs.addTabCommandInput("requestTab", "Select Requested Type")
    propagate_tab = inputs.addTabCommandInput("propagateTab", "Select Propagated Types")
    request_tab_inputs = request_tab.children
    propagate_tab_inputs = propagate_tab.children

    parts_type_selection_browser_input = request_tab_inputs.addBrowserCommandInput(
        id=PARTTYPES_ID,
        name="Select part/part family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    attributes_type_selection_browser_input = request_tab_inputs.addBrowserCommandInput(
        id=ATTRIBUTETYPES_ID,
        name="Select attributes/attribute family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    propagate_tab_inputs.addBrowserCommandInput(
        id=PROP_FORMATS_ID,
        name="Select formats/format family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    propagate_tab_inputs.addBrowserCommandInput(
        id=PROP_PARTS_ID,
        name="Select parts/part family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    propagate_tab_inputs.addBrowserCommandInput(
        id=PROP_ATTRIBUTES_ID,
        name="Select attributes/attribute family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )


def command_execute_preview(args: adsk.core.CommandEventHandler):
    pass


def command_activate(args: adsk.core.CommandEventArgs):
    app = adsk.core.Application.get()
    app.log("In command_activate event handler.")


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f"{CMD_NAME}: Palette incoming event.")
    print("Incoming")
    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)
    global request_parts, request_attributes, propagate_parts, propagate_attributes, propagate_formats
    if message_action == "selectionNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            request_parts = message_data["selections"]
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            request_attributes = message_data["selections"]
        elif html_args.browserCommandInput.id == PROP_FORMATS_ID:
            propagate_formats = message_data["selections"]
        elif html_args.browserCommandInput.id == PROP_ATTRIBUTES_ID:
            propagate_attributes = message_data["selections"]
        elif html_args.browserCommandInput.id == propagate_parts:
            propagate_parts = message_data["selections"]

    if message_action == "updateDataNotification":
        if (
            html_args.browserCommandInput.id == PARTTYPES_ID
            or html_args.browserCommandInput.id == PROP_PARTS_ID
        ):
            taxonomy_id = "parts"
        elif (
            html_args.browserCommandInput.id == ATTRIBUTETYPES_ID
            or html_args.browserCommandInput.id == PROP_ATTRIBUTES_ID
        ):
            taxonomy_id = "attributes"
        elif html_args.browserCommandInput.id == PROP_FORMATS_ID:
            taxonomy_id = "formats"
        config.taxonomies[taxonomy_id] = message_data
        update_taxonomy_in_backend()

    if message_action == "renameDataNotification":
        if (
            html_args.browserCommandInput.id == PARTTYPES_ID
            or html_args.browserCommandInput.id == PROP_PARTS_ID
        ):
            taxonomy_id = "parts"
        elif (
            html_args.browserCommandInput.id == ATTRIBUTETYPES_ID
            or html_args.browserCommandInput.id == PROP_ATTRIBUTES_ID
        ):
            taxonomy_id = "attributes"
        elif html_args.browserCommandInput.id == PROP_FORMATS_ID:
            taxonomy_id = "formats"
        config.mappings[taxonomy_id][message_data[1]] = config.mappings[
            taxonomy_id
        ].pop(message_data[0])

    if message_action == "readyNotification":
        taxonomy_id = None
        taxonomy_data_message = None
        if (
            html_args.browserCommandInput.id == PARTTYPES_ID
            or html_args.browserCommandInput.id == PROP_PARTS_ID
        ):
            taxonomy_data_message = config.taxonomies["parts"]
            taxonomy_id = "parts"
        elif (
            html_args.browserCommandInput.id == ATTRIBUTETYPES_ID
            or html_args.browserCommandInput.id == PROP_ATTRIBUTES_ID
        ):
            taxonomy_data_message = config.taxonomies["attributes"]
            taxonomy_id = "attributes"
        elif html_args.browserCommandInput.id == PROP_FORMATS_ID:
            taxonomy_data_message = config.taxonomies["formats"]
            taxonomy_id = "formats"

        html_args.browserCommandInput.sendInfoToHTML(
            "taxonomyDataMessage", json.dumps(taxonomy_data_message)
        )
        html_args.browserCommandInput.sendInfoToHTML("taxonomyIDMessage", taxonomy_id)

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


def winapi_path(dos_path, encoding=None):
    if not isinstance(dos_path, str) and encoding is not None:
        dos_path = dos_path.decode(encoding)
    path = os.path.abspath(dos_path)
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Execute Event")

    global request_attributes, request_parts
    app = adsk.core.Application.get()
    request_dict = {
        "target": [f"{x}_parts" for x in request_parts]
        + [f"{x}_attributes" for x in request_attributes]
        + [f"Has_{x}_parts" for x in propagate_parts]
        + [f"Has_{x}_formats" for x in propagate_formats]
        + [f"Has_{x}_attributes" for x in propagate_attributes],
        "propagate": [[f"Has_{x}_parts"] for x in propagate_parts]
        + [[f"Has_{x}_formats"] for x in propagate_formats]
        + [[f"Has_{x}_attributes"] for x in propagate_attributes],
        "forgeProjectId": app.activeDocument.dataFile.parentProject.id
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.id,
    }
    payload = json.dumps(
        request_dict,
        indent=4,
    ).encode("utf-8")
    print("Send request")
    req = urllib.request.Request("http://127.0.0.1:8000/request/assembly")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Content-Length", len(payload))
    response = urllib.request.urlopen(req, payload)
    print(response.read().decode())


def command_preview(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, request_attributes, request_parts
    request_parts = []
    request_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
