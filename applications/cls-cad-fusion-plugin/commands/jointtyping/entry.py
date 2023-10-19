import json
import os
import traceback
from datetime import datetime

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import (
    generate_id,
    invert_map,
    load_project_taxonomy_to_config,
    update_taxonomy_in_backend,
)

app = adsk.core.Application.get()
ui = app.userInterface

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
PALETTE_URL = f"{config.SERVER_URL}/static/unrolledTaxonomyDisplay/index.html"
PALETTE_URL = PALETTE_URL.replace("\\", "/")
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")

local_handlers = []
type_text_box_input: adsk.core.TextBoxCommandInput = None
parts_type_selection_browser_input: adsk.core.BrowserCommandInput = None
kinding_selection_drop_down_input: adsk.core.DropDownCommandInput = None
name_string_value_input: adsk.core.ValueInput = None
provides_type_text_box_input: adsk.core.TextBoxCommandInput = None
joint_connect_type_input: adsk.core.ButtonRowCommandInput = None
reset_bool_value_input: adsk.core.BoolValueCommandInput = None


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    control2 = panel.controls.addCommand(ui.commandDefinitions.itemById("JointOrigin"))
    control2.isPromoted = True

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
selected_joint_origins = []
(
    req_formats,
    req_attributes,
    req_parts,
    provides_formats,
    provides_parts,
    provides_attributes,
) = ([] for i in range(6))
kinding = "Light"
typing = "Blocked"


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f"{CMD_NAME} Command Created Event")

    load_project_taxonomy_to_config()

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

    global type_text_box_input, parts_type_selection_browser_input, kinding_selection_drop_down_input, name_string_value_input, provides_type_text_box_input, joint_connect_type_input, reset_bool_value_input

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
    joint_connect_type_input.listItems.add(
        "Rigid", False, os.path.join(ICON_FOLDER, "Rigid")
    )
    joint_connect_type_input.listItems.item(0).isSelected = True
    joint_connect_type_input.listItems.add(
        "Revolute", False, os.path.join(ICON_FOLDER, "Revolute")
    )

    type_text_box_input = selection_tab_inputs.addTextBoxCommandInput(
        "typeTextBox", "Requires Type", "", 2, True
    )
    provides_type_text_box_input = selection_tab_inputs.addTextBoxCommandInput(
        "providesTypeTextBox", "Provides Type", "", 2, True
    )
    reset_bool_value_input = selection_tab_inputs.addBoolValueInput(
        "resetAttribsBoolInput", "Reset Typing", True
    )
    name_string_value_input = selection_tab_inputs.addStringValueInput(
        "nameTextBox", "Set Name", ""
    )
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
    global req_attributes, req_formats, req_parts, provides_formats, selected_joint_origins
    if design and selected_joint_origin:
        try:
            provides_formats = [
                config.inverted_mappings["formats"][x]
                for x in json.loads(
                    selected_joint_origin.attributes.itemByName(
                        "CLS-JOINT", "ProvidesFormats"
                    ).value
                )
            ]
            req_attributes = [
                config.inverted_mappings["attributes"][x]
                for x in json.loads(
                    selected_joint_origin.attributes.itemByName(
                        "CLS-JOINT", "RequiresAttributes"
                    ).value
                )
            ]
            req_formats = [
                config.inverted_mappings["formats"][x]
                for x in json.loads(
                    selected_joint_origin.attributes.itemByName(
                        "CLS-JOINT", "RequiresFormats"
                    ).value
                )
            ]
            req_parts = [
                config.inverted_mappings["parts"][x]
                for x in json.loads(
                    selected_joint_origin.attributes.itemByName(
                        "CLS-JOINT", "RequiresParts"
                    ).value
                )
            ]
            if (
                selected_joint_origin.attributes.itemByName(
                    "CLS-JOINT", "JointConnectType"
                ).value
                == "Revolute"
            ):
                joint_connect_type_input.listItems.item(1).isSelected = True
            # If nothing went wrong here, properly generate the text
            type_text_box_input.text = f'({"∩".join(filter(None,["∩".join(req_formats),"∩".join(req_parts),"∩".join(req_attributes)]))})'.replace(
                " ∩ ()", ""
            )
            provides_type_text_box_input.text = f'({"∩".join(filter(None, ["∩".join(provides_formats),"∩".join(provides_parts), "∩".join(provides_attributes)]))})'.replace(
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
    pass


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    if args.input.id == "resetAttribsBoolInput":
        global reset_bool_value_input, req_formats, req_attributes, req_parts, provides_formats, provides_parts, provides_attributes
        if reset_bool_value_input.value:
            (
                req_formats,
                req_attributes,
                req_parts,
                provides_attributes,
                provides_formats,
                provides_parts,
            ) = ([], [], [], [], [], [])


def palette_navigating(args: adsk.core.NavigationEventArgs):
    futil.log(f"{CMD_NAME}: Palette navigating event.")

    url = args.navigationURL

    log_msg = f"User is attempting to navigate to {url}\n"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    if url.startswith("http"):
        args.launchExternally = True


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f"{CMD_NAME}: Palette incoming event.")
    message_data = json.loads(html_args.data)
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
        provides_type_text_box_input.text = f'({"∩".join(filter(None, ["∩".join(provides_formats),"∩".join(provides_parts), "∩".join(provides_attributes)]))})'.replace(
            " ∩ ()", ""
        )
    if message_action == "updateDataNotification":
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
        update_taxonomy_in_backend()

    if message_action == "renameDataNotification":
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomy_id = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomy_id = "attributes"
        elif (
            html_args.browserCommandInput.id == FORMATTYPES_ID
            or html_args.browserCommandInput.id == FORMATPROVIDESTYPES_ID
        ):
            taxonomy_id = "formats"
        print("Updating mapping")
        config.mappings[taxonomy_id][message_data[1]] = config.mappings[
            taxonomy_id
        ].pop(message_data[0])
        config.inverted_mappings = invert_map(config.mappings)
        update_taxonomy_in_backend()

    if message_action == "readyNotification":
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

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Execute Event")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    global typing, kinding, selected_joint_origins, name_string_value_input, parts_type_selection_browser_input, joint_connect_type_input, reset_bool_value_input
    global req_formats, req_attributes, req_parts, provides_formats, provides_parts, provides_attributes

    print("Trying to sync")
    parts_type_selection_browser_input.sendInfoToHTML("returnTaxonomyDataMessage", "{}")

    jo_uuid = str(generate_id())
    for jo in selected_joint_origins:
        jo.attributes.add(
            "CLS-JOINT",
            "RequiresFormats",
            json.dumps([config.mappings["formats"][x] for x in req_formats]),
        )
        jo.attributes.add(
            "CLS-JOINT",
            "RequiresParts",
            json.dumps([config.mappings["parts"][x] for x in req_parts]),
        )
        jo.attributes.add(
            "CLS-JOINT",
            "RequiresAttributes",
            json.dumps([config.mappings["attributes"][x] for x in req_attributes]),
        )
        jo.attributes.add(
            "CLS-JOINT",
            "ProvidesFormats",
            json.dumps([config.mappings["formats"][x] for x in provides_formats]),
        )
        jo.attributes.add(
            "CLS-JOINT", "JointConnectType", joint_connect_type_input.selectedItem.name
        )

        if not jo.attributes.itemByName("CLS-INFO", "UUID"):
            print("Added UUID to %s" % jo.name)
            jo.name = "Typed Joint"
            jo.attributes.add("CLS-INFO", "UUID", jo_uuid)

    update_type_information_graphics()
    try:
        design.selectionSets.add(
            selected_joint_origins, name_string_value_input.value or "Typed Joint Set"
        )
    except RuntimeError:
        traceback.print_exc()
    finally:
        selected_joint_origins = []
        (
            req_formats,
            req_attributes,
            req_parts,
            provides_attributes,
            provides_formats,
            provides_parts,
        ) = ([], [], [], [], [], [])


def update_type_information_graphics():
    config.custom_graphics_displaying = True
    cmd = ui.commandDefinitions.itemById(
        f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display"
    )
    cmd.execute()
    cmd.execute()


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
