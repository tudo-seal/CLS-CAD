from datetime import datetime

import adsk.core

from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    config,
    json,
    load_project_taxonomy_to_config,
    os,
    update_taxonomy_in_backend,
)

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_type_part"
CMD_NAME = "Typed Part"
CMD_DESCRIPTION = "Annotate Parts with Attribute and Type information."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "TYPES"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
PARTTYPES_ID = "partsTaxonomyBrowser_Part"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser_Part"
PALETTE_URL = f"{config.SERVER_URL}/static/unrolledTaxonomyDisplay/index.html"
PALETTE_URL = PALETTE_URL.replace("\\", "/")
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []
provides_parts, provides_attributes = [], []


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
    global type_text_box_input, parts_type_selection_browser_input, provides_parts, provides_attributes

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
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    provides_attributes = [
        config.inverted_mappings["attributes"][x]
        for x in json.loads(
            design.rootComponent.attributes.itemByName(
                "CLS-PART", "ProvidesAttributes"
            ).value
            if design.rootComponent.attributes.itemByName(
                "CLS-PART", "ProvidesAttributes"
            )
            else "[]"
        )
    ]
    provides_parts = [
        config.inverted_mappings["parts"][x]
        for x in json.loads(
            design.rootComponent.attributes.itemByName(
                "CLS-PART", "ProvidesParts"
            ).value
            if design.rootComponent.attributes.itemByName("CLS-PART", "ProvidesParts")
            else "[]"
        )
    ]

    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    type_text_box_input = inputs.addTextBoxCommandInput(
        "typeTextBox", "Part Type", "", 1, True
    )
    type_text_box_input.numRows = 12

    parts_type_selection_browser_input = inputs.addBrowserCommandInput(
        id=PARTTYPES_ID,
        name="Select part/part family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    attributes_type_selection_browser_input = inputs.addBrowserCommandInput(
        id=ATTRIBUTETYPES_ID,
        name="Select attributes/attribute family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )


def command_execute_preview(args: adsk.core.CommandEventHandler):
    type_text_box_input.text = generate_type_text()


def command_activate(args: adsk.core.CommandEventArgs):
    app = adsk.core.Application.get()
    app.log("In command_activate event handler.")


def generate_type_text():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    typed_jos = []
    guarded_types = []
    global provides_parts, provides_attributes
    for joint_typing in list(
        {x.value: x for x in design.findAttributes("CLS-INFO", "UUID")}.values()
    ):
        jo = joint_typing.parent
        req_string = "∩".join(
            [
                config.inverted_mappings["formats"][x]
                for x in json.loads(
                    jo.attributes.itemByName("CLS-JOINT", "RequiresFormats").value
                )
            ]
            + [
                config.inverted_mappings["parts"][x]
                for x in json.loads(
                    jo.attributes.itemByName("CLS-JOINT", "RequiresParts").value
                )
            ]
            + [
                config.inverted_mappings["attributes"][x]
                for x in json.loads(
                    jo.attributes.itemByName("CLS-JOINT", "RequiresAttributes").value
                )
            ]
        )
        prov_string = "∩".join(
            [
                config.inverted_mappings["formats"][x]
                for x in json.loads(
                    jo.attributes.itemByName("CLS-JOINT", "ProvidesFormats").value
                )
            ]
        )
        typed_jos.append((req_string, prov_string))
    print(typed_jos)
    for joInfo in typed_jos:
        if joInfo[1].strip() == "":
            continue
        req_list = [x[0] for x in typed_jos if x != joInfo]
        guarded_types.append(
            "("
            + " → ".join(req_list)
            + " → ("
            + joInfo[1]
            + f' ∩ ({"∩".join(provides_parts)}) ∩ ({"∩".join(provides_attributes)}))'
        )
    return (
        """<style>
                pre {
                    white-space:pre-wrap;
                    tab-size: 2;
                    display: block;
                    line-height: 100%;
                    font-family: Courier;
                }
                </style><pre>"""
        + ") ∩ \n".join(guarded_types).replace(" ∩ ()", "")
        + "</pre>"
    )


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f"{CMD_NAME}: Palette incoming event.")
    print("Incoming")
    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)
    global provides_parts, provides_attributes
    if message_action == "selectionNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            provides_parts = message_data["selections"]
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            provides_attributes = message_data["selections"]
        type_text_box_input.formattedText = generate_type_text()

    if message_action == "updateDataNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_id = "attributes"
        config.taxonomies[taxonomy_id] = message_data
        update_taxonomy_in_backend()

    if message_action == "renameDataNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_id = "attributes"
            taxonomy_id = "formats"
        config.mappings[taxonomy_id][message_data[1]] = config.mappings[
            taxonomy_id
        ].pop(message_data[0])

    if message_action == "readyNotification":
        taxonomy_id = None
        taxonomy_data_message = None
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_data_message = config.taxonomies["parts"]
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_data_message = config.taxonomies["attributes"]
            taxonomy_id = "attributes"
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

    global provides_attributes, provides_parts
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root_comp = design.rootComponent
    root_comp.attributes.add(
        "CLS-PART",
        "ProvidesAttributes",
        json.dumps([config.mappings["attributes"][x] for x in provides_attributes]),
    )
    root_comp.attributes.add(
        "CLS-PART",
        "ProvidesParts",
        json.dumps([config.mappings["parts"][x] for x in provides_parts]),
    )


def command_preview(args: adsk.core.CommandEventArgs):
    type_text_box_input.formattedText = generate_type_text()
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, provides_attributes, provides_parts
    provides_parts = []
    provides_attributes = []
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
