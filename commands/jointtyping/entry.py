import json
import os
from datetime import datetime
from pathlib import Path

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    generate_id,
    load_project_taxonomy_to_config,
    winapi_path,
)

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_type_joint"
CMD_NAME = "Typed Joint"
CMD_DESCRIPTION = "Annotate joint origins with a combinatorial term, allowing combinatory logic to connect parts automatically."
IS_PROMOTED = True

WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "TYPES"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"

PARTTYPES_ID = "partsTaxonomyBrowser"
FORMATTYPES_ID = "formatsTaxonomyBrowser"
FORMATPROVIDESTYPES_ID = "providesFormatsTaxonomyBrowser"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser"

# Specify the full path to the local html. You can also use a web URL
# such as 'https://www.autodesk.com/'
PALETTE_URL = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "resources",
    "html",
    "unrolledTaxonomyDisplay",
    "index.html",
)

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace("\\", "/")

# Resource location
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

# Executed when add-in is run.


def start():
    # Command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    control2 = panel.controls.addCommand(ui.commandDefinitions.itemById("JointOrigin"))
    control2.isPromoted = True

    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


joint_origin = adsk.fusion.JointOrigin.cast(None)

# Unsure if this is a better approach than iterating over the actual selection_input
selected_joint_origins = []
# Initializing like this is nice but not necessary I guess
# typeTextBoxInput = adsk.core.TextBoxCommandInput.cast(None)
# nameStringValueInput = adsk.core.StringValueCommandInput.cast(None)
# partsTypeSelectionBrowserInput = adsk.core.BrowserCommandInput.cast(None)

(
    req_formats,
    req_attributes,
    req_parts,
    provides_formats,
    provides_parts,
    provides_attributes,
) = ([], [], [], [], [], [])

kinding = "Light"
typing = "Blocked"


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Created Event")

    # Load appropriate taxonomies
    load_project_taxonomy_to_config()

    # Handlers
    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    # futil.add_handler(args.command.inputChanged,
    #                   command_input_changed,
    #                   local_handlers=local_handlers)
    futil.add_handler(
        args.command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.preSelectMouseMove,
        command_preselect_mousemove,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.preSelect, command_preselect, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.preSelectEnd, command_preselect_end, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.executePreview,
        command_execute_preview,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.select, command_select, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.unselect, command_unselect, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.navigatingURL, palette_navigating, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.incomingFromHTML, palette_incoming, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.activate, command_activate, local_handlers=local_handlers
    )

    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(600, 800)
    args.command.setDialogInitialSize(600, 800)

    # UI DEF
    global type_text_box_input, parts_type_selection_browser_input, kinding_selection_drop_down_input, name_string_value_input, provides_type_text_box_input, joint_connect_type_input

    selection_tab = inputs.addTabCommandInput("selectionTab", "Select/Configure Joint")
    requires_tab = inputs.addTabCommandInput("requiresTab", "Select Required Type")
    provides_tab = inputs.addTabCommandInput("providesTab", "Select Provided Type")
    selection_tab_inputs = selection_tab.children
    requires_tab_inputs = requires_tab.children
    provides_tab_inputs = provides_tab.children

    selection_input = selection_tab_inputs.addSelectionInput(
        "selection", "Select", "Basic select command input"
    )
    selection_input.setSelectionLimits(0)
    selection_input.addSelectionFilter("JointOrigins")

    joint_connect_type_input = selection_tab_inputs.addButtonRowCommandInput(
        "jointTypeSelection", "Joint Type", False
    )
    joint_connect_type_input.listItems.add("Rigid", False, "resources")
    joint_connect_type_input.listItems.item(0).isSelected = True
    joint_connect_type_input.listItems.add("Revolute", False, "resources")

    type_text_box_input = selection_tab_inputs.addTextBoxCommandInput(
        "typeTextBox", "Requires Type", "", 2, True
    )
    provides_type_text_box_input = selection_tab_inputs.addTextBoxCommandInput(
        "providesTypeTextBox", "Provides Type", "", 2, True
    )
    name_string_value_input = selection_tab_inputs.addStringValueInput(
        "nameTextBox", "Set Name", ""
    )

    # group_typing_cmd_input = inputs.addGroupCommandInput('typingGroup', 'Typing')
    # group_typing_cmd_input.is_expanded = True
    # group_typing_children = group_typing_cmd_input.children
    formats_type_selection_browser_input = requires_tab_inputs.addBrowserCommandInput(
        id=FORMATTYPES_ID,
        name="Select format/format family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    parts_type_selection_browser_input = requires_tab_inputs.addBrowserCommandInput(
        id=PARTTYPES_ID,
        name="Select part/part family",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )
    attributes_type_selection_browser_input = (
        requires_tab_inputs.addBrowserCommandInput(
            id=ATTRIBUTETYPES_ID,
            name="Select attributes/attribute family",
            htmlFileURL=PALETTE_URL,
            minimumHeight=300,
        )
    )

    # Mot synced with other formats browser, figure that out still
    provides_type_selection_browser_input = provides_tab_inputs.addBrowserCommandInput(
        id=FORMATPROVIDESTYPES_ID,
        name="Select format present at joint",
        htmlFileURL=PALETTE_URL,
        minimumHeight=300,
    )


def command_execute_preview(args: adsk.core.CommandEventHandler):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design:
        pass


def command_activate(args: adsk.core.CommandEventArgs):
    app = adsk.core.Application.get()
    app.log("In command_activate event handler.")


def command_select(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selected_joint_origin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    global req_attributes, req_formats, req_parts, provides_formats
    if design and selected_joint_origin:
        try:
            type_text_box_input.text = (
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "RequiresString"
                ).value
                or "None"
            )
            provides_type_text_box_input.text = (
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "ProvidesString"
                ).value
                or "None"
            )
            provides_formats = json.loads(
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "ProvidesFormats"
                ).value
            )
            req_attributes = json.loads(
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "RequiresAttributes"
                ).value
            )
            req_formats = json.loads(
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "RequiresFormats"
                ).value
            )
            req_parts = json.loads(
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "RequiresParts"
                ).value
            )
            # If nothing went wrong here, properly generate the text
            type_text_box_input.text = f'({"∩".join(filter(None,["∩".join(req_formats),"∩".join(req_parts),"∩".join(req_attributes)]))})'.replace(
                " ∩ ()", ""
            )
            provides_type_text_box_input.text = f'({"∩".join(filter(None,["∩".join(provides_formats),"∩".join(provides_parts),"∩".join(provides_attributes)]))})'.replace(
                " ∩ ()", ""
            )
        except:
            pass
        selected_joint_origins.append(selected_joint_origin)


def command_unselect(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selected_joint_origin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    global selected_joint_origins
    if design and selected_joint_origin:
        selected_joint_origins.append(selected_joint_origin)
        selected_joint_origins = [
            x for x in selected_joint_origins if x.id != selected_joint_origin.id
        ]


def command_preselect_mousemove(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selected_joint_origin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selected_joint_origin:
        pass


def command_preselect(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selected_joint_origin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selected_joint_origin:
        pass


def command_preselect_end(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selected_edge = adsk.fusion.BRepEdge.cast(args.selection.entity)
    if design and selected_edge:
        for group in design.rootComponent.customGraphicsGroups:
            if group.id == "the_relevant_group":
                group.deleteMe()
                break


# def command_input_changed(args: adsk.core.InputChangedEventArgs):
#     app = adsk.core.Application.get()
#     design = adsk.fusion.Design.cast(app.activeProduct)
#     if args.input.id == 'typeSelection':
#         global typing
#         typing = typeSelectionDropDownInput.selectedItem.name
#     if args.input.id == 'kindingSelection':
#         global kinding
#         kinding = kindingSelectionDropDownInput.selectedItem.name


def palette_navigating(args: adsk.core.NavigationEventArgs):
    futil.log(f"{CMD_NAME}: Palette navigating event.")

    url = args.navigationURL

    log_msg = f"User is attempting to navigate to {url}\n"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    if url.startswith("http"):
        args.launchExternally = True


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f"{CMD_NAME}: Palette incoming event.")
    app = adsk.core.Application.get()
    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)
    global req_formats, req_parts, req_attributes, provides_formats
    if message_action == "selectionNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            req_parts = message_data["selections"]
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            req_attributes = message_data["selections"]
        elif html_args.browserCommandInput.id == FORMATTYPES_ID:
            req_formats = message_data["selections"]
        elif html_args.browserCommandInput.id == FORMATPROVIDESTYPES_ID:
            provides_formats = message_data["selections"]
        type_text_box_input.text = f'({"∩".join(filter(None,["∩".join(req_formats),"∩".join(req_parts),"∩".join(req_attributes)]))})'.replace(
            " ∩ ()", ""
        )
        provides_type_text_box_input.text = f'({"∩".join(filter(None,["∩".join(provides_formats),"∩".join(provides_parts),"∩".join(provides_attributes)]))})'.replace(
            " ∩ ()", ""
        )
    if message_action == "updateDataNotification":
        # Update loaded and saved taxonomies

        # The browser IDs should be refactored into constants
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_id = "attributes"
        elif (
            html_args.browserCommandInput.id == FORMATTYPES_ID
            or html_args.browserCommandInput.id == FORMATPROVIDESTYPES_ID
        ):
            taxonomy_id = "formats"
        config.taxonomies[taxonomy_id] = message_data
        p = Path(
            winapi_path(
                os.path.join(
                    config.ROOT_FOLDER,
                    "Taxonomies",
                    "CAD",
                    app.activeDocument.dataFile.parentProject.id.replace(":", "-"),
                )
            )
        )
        p.mkdir(parents=True, exist_ok=True)
        with open(
            winapi_path(
                os.path.join(
                    ROOT_FOLDER,
                    "Taxonomies",
                    "CAD",
                    app.activeDocument.dataFile.parentProject.id.replace(":", "-"),
                    "%s.taxonomy" % taxonomy_id,
                )
            ),
            "w+",
        ) as f:
            json.dump(message_data, f, ensure_ascii=False, indent=4)

    if message_action == "readyNotification":
        # ADSK was injected, so now we send the payload
        taxonomy_id = None
        taxonomy_data_message = None
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_data_message = config.taxonomies["parts"]
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_data_message = config.taxonomies["attributes"]
            taxonomy_id = "attributes"
        elif (
            html_args.browserCommandInput.id == FORMATTYPES_ID
            or html_args.browserCommandInput.id == FORMATPROVIDESTYPES_ID
        ):
            taxonomy_data_message = config.taxonomies["formats"]
            taxonomy_id = "formats"
        html_args.browserCommandInput.sendInfoToHTML(
            "taxonomyDataMessage", json.dumps(taxonomy_data_message)
        )
        html_args.browserCommandInput.sendInfoToHTML("taxonomyIDMessage", taxonomy_id)

    # Return value.
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


# EXECUTE
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f"{CMD_NAME} Command Execute Event")

    inputs = args.command.commandInputs

    # Get inputs
    selection_input: adsk.core.SelectionCommandInput = inputs.itemById("selection")

    # All this obv. still has to check for if there already is a custom graphics object for that JointOrigin
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    bill_board = adsk.fusion.CustomGraphicsBillBoard.create(
        adsk.core.Point3D.create(0, 0, 0)
    )
    bill_board.billBoardStyle = (
        adsk.fusion.CustomGraphicsBillBoardStyles.ScreenBillBoardStyle
    )

    global typing, kinding, selected_joint_origins, name_string_value_input, parts_type_selection_browser_input, joint_connect_type_input
    global req_formats, req_attributes, req_parts, provides_formats, provides_parts, provides_attributes

    print("Trying to sync")
    parts_type_selection_browser_input.sendInfoToHTML("returnTaxonomyDataMessage", "{}")

    jo_uuid = str(generate_id())
    for jo in selected_joint_origins:

        # Add typing information as string (this is kinda okay, because we'll send it via JSON to the backend anyway)
        # Needs fixing
        jo.attributes.add(
            "CLS-JOINT",
            "RequiresString",
            type_text_box_input.text if type_text_box_input.text != "()" else "None",
        )
        jo.attributes.add(
            "CLS-JOINT",
            "ProvidesString",
            f'({"∩".join(provides_formats)})'.replace(" ∩ ()", "").replace("()", ""),
        )
        jo.attributes.add("CLS-JOINT", "RequiresFormats", json.dumps(req_formats))
        jo.attributes.add("CLS-JOINT", "RequiresParts", json.dumps(req_parts))
        jo.attributes.add("CLS-JOINT", "RequiresAttributes", json.dumps(req_attributes))
        jo.attributes.add("CLS-JOINT", "ProvidesFormats", json.dumps(provides_formats))
        jo.attributes.add(
            "CLS-JOINT", "JointConnectType", joint_connect_type_input.selectedItem.name
        )

        # The first time a joint is typed, assign a UUID and change its name
        if not jo.attributes.itemByName("CLS-INFO", "UUID"):
            print("Added UUID to %s" % jo.name)
            jo.attributes.add("CLS-INFO", "UUID", jo_uuid)
            jo.name = "Typed Joint"

        jo_uuid = jo.attributes.itemByName("CLS-INFO", "UUID").value

    ################################################
    ################################################
    # GRAPHICAL DISPLAY STUFF, IMPORTANT A BIT LATER
    # This could be done smarter, avoiding flicker, but this is a lot easier
    config.custom_graphics_displaying = True
    cmd = ui.commandDefinitions.itemById(
        f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display"
    )
    cmd.execute()
    cmd.execute()
    try:
        design.selectionSets.add(
            selected_joint_origins, name_string_value_input.value or "Typed Joint Set"
        )
    except:
        # ToDo: Figure out why this fails if there are nested components with JointOrigins (aka. the UI can do this manually, why can't we?)
        pass

    selected_joint_origins = []
    (
        req_formats,
        req_attributes,
        req_parts,
        provides_attributes,
        provides_formats,
        provides_parts,
    ) = ([], [], [], [], [], [])
    # Should probably be a toggle under visualisation section
    # graphicsText.billBoarding = billBoard


def command_preview(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, req_attributes, req_formats, req_parts, provides_attributes, provides_formats, provides_parts
    local_handlers = []
    (
        req_attributes,
        req_formats,
        req_parts,
        providesAttributes,
        provides_formats,
        providesParts,
    ) = ([], [], [], [], [], [])
    futil.log(f"{CMD_NAME} Command Destroy Event")
