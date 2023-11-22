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
counted_parts, counted_attributes, counted_formats = [], [], []
counted_types = {}
selected_text = adsk.core.StringValueCommandInput.cast(None)
_rowNumber = 0


def add_row_to_table(table_input):
    """
    Adds a row to the table for specifying the synthesis constraints.

    :param table_input:
    :return:
    """
    global _rowNumber, counted_parts, counted_formats, counted_attributes, counted_types, selected_text
    cmd_inputs = adsk.core.CommandInputs.cast(table_input.commandInputs)

    text_input = cmd_inputs.addStringValueInput(
        f"text{_rowNumber}",
        "",
        " ∩ ".join(
            [x for x in [*counted_parts, *counted_attributes, *counted_formats]]
        ),
    )
    text_input.isReadOnly = True
    spinner_input = cmd_inputs.addIntegerSpinnerCommandInput(
        f"typeamount{_rowNumber}", "Amount", 0, 100, 1, 1
    )

    row = table_input.rowCount
    table_input.addCommandInput(text_input, row, 1)
    table_input.addCommandInput(spinner_input, row, 2)

    counted_types[row] = (
        [f"{x}_parts" for x in counted_parts]
        + [f"{x}_formats" for x in counted_formats]
        + [f"{x}_attributes" for x in counted_attributes],
        spinner_input,
    )
    selected_text.value = ""
    counted_parts, counted_attributes, counted_formats = [], [], []
    _rowNumber = _rowNumber + 1


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


joint_origin = adsk.fusion.JointOrigin.cast(None)

type_text_box_input = adsk.core.TextBoxCommandInput.cast(None)
parts_type_selection_browser_input = adsk.core.BrowserCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers all important
    handlers for the command.

    :param args: adsk.core.CommandCreatedEventArgs:
    :return:
    """
    global type_text_box_input, parts_type_selection_browser_input, request_parts, request_attributes, counted_parts, counted_attributes, counted_formats, selected_text

    futil.log(f"{CMD_NAME} Command Created Event")

    load_project_taxonomy_to_config()

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.inputChanged, input_changed, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.incomingFromHTML, palette_incoming, local_handlers=local_handlers
    )

    request_attributes = []
    request_parts = []
    counted_parts, counted_attributes, counted_formats = [], [], []
    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    request_tab = inputs.addTabCommandInput("requestTab", "Select Requested Type")
    counted_tab = inputs.addTabCommandInput("countedTab", "Select counted Types")
    request_tab_inputs = request_tab.children
    counted_tab_inputs = counted_tab.children

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
    counted_tab_inputs.addBrowserCommandInput(
        id=PROP_FORMATS_ID,
        name="Select formats/format family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    counted_tab_inputs.addBrowserCommandInput(
        id=PROP_PARTS_ID,
        name="Select parts/part family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    counted_tab_inputs.addBrowserCommandInput(
        id=PROP_ATTRIBUTES_ID,
        name="Select attributes/attribute family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    selected_text = counted_tab_inputs.addStringValueInput(
        f"selected_constraints_request",
        "",
        "",
    )
    selected_text.isReadOnly = True

    table_input = counted_tab_inputs.addTableCommandInput(
        "amount_table", "Constraints", 2, "4:1"
    )
    add_button_input = counted_tab_inputs.addBoolValueInput(
        "table_add", "Add", False, "", True
    )
    table_input.addToolbarCommandInput(add_button_input)
    delete_button_input = counted_tab_inputs.addBoolValueInput(
        "table_delete", "Delete", False, "", True
    )
    table_input.addToolbarCommandInput(delete_button_input)


def input_changed(args: adsk.core.InputChangedEventArgs):
    """
    Fires when any of the command inputs changes. Used to respond to any changes or
    button clicks with regard to the synthesis constraints table.

    :param args: adsk.core.InputChangedEventArgs: The event data containing info on
        which input has changed.
    :return:
    """
    global counted_types
    table_input: adsk.core.TableCommandInput = args.inputs.itemById("amount_table")
    if args.input.id == "table_add":
        add_row_to_table(table_input)
    elif args.input.id == "table_delete":
        if table_input.selectedRow == -1:
            ui.messageBox("Select one row to delete.")
        else:
            counted_types.pop(table_input.selectedRow)
            table_input.deleteRow(table_input.selectedRow)


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    """
    Handles incoming messages from the JavaScript portion of the palette. Receives an
    "updateDataNotification", "renameDataNotification", or "selectionNotification", that
    contain the JSON representation of data instructing the add-in to rename a type
    internally, update a taxonomy with new data, or add an element from the palette to
    the currently selected types for the synthesis request.

    :param html_args: adsk.core.HTMLEventArgs: The received HTML event containing data.
    :return:
    """
    futil.log(f"{CMD_NAME}: Palette incoming event.")
    print("Incoming")
    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)
    global request_parts, request_attributes, counted_parts, counted_attributes, counted_formats, selected_text
    if message_action == "selectionNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            request_parts = message_data["selections"]
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            request_attributes = message_data["selections"]
        elif html_args.browserCommandInput.id == PROP_FORMATS_ID:
            counted_formats = message_data["selections"]
        elif html_args.browserCommandInput.id == PROP_ATTRIBUTES_ID:
            counted_attributes = message_data["selections"]
        elif html_args.browserCommandInput.id == PROP_PARTS_ID:
            counted_parts = message_data["selections"]

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

    selected_text.value = " ∩ ".join(
        [x for x in [*counted_parts, *counted_attributes, *counted_formats]]
    )
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


def winapi_path(dos_path, encoding=None):
    """
    Encodes a path into a winapi compatible path, this is important for longer paths
    that exceed the standard char limit.

    :param dos_path: The path to encode.
    :param encoding: Default value = None) The encoding to use.
    :return:
    """
    if not isinstance(dos_path, str) and encoding is not None:
        dos_path = dos_path.decode(encoding)
    path = os.path.abspath(dos_path)
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It generates a JSON from
    the collected information (selected types in palettes and table),describing a
    synthesis request, and sends it to the backend.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    global request_attributes, request_parts
    app = adsk.core.Application.get()
    request_dict = {
        "target": [f"{x}_parts" for x in request_parts]
        + [f"{x}_attributes" for x in request_attributes]
        + [f"Has_{x}_parts" for x in counted_parts]
        + [f"Has_{x}_formats" for x in counted_formats]
        + [f"Has_{x}_attributes" for x in counted_attributes],
        "partCounts": [
            {
                "partNumber": counted_type[1].value,
                "partCountName": "-".join(counted_type[0]),
                "partType": counted_type[0],
            }
            for _, counted_type in counted_types.items()
        ],
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
    print(response.read().decode())


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Cleans up all collected data after the user has pressed the "Okay" button.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    global local_handlers, request_attributes, request_parts
    request_parts = []
    request_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
