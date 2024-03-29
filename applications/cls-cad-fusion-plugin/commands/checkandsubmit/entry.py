import urllib.request

import adsk.core

from ... import config
from ...lib import fusion360utils as futil
from ...lib.cls_python_compat import *
from ...lib.general_utils import *

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_cns"
CMD_NAME = "Submit"
CMD_Description = "Check and Submit part to repository."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "CRAWL"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
ROOT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..")


local_handlers = []


def start():
    """
    Creates the promoted "Check and Submit" command in the CLS-CAD tab.

    Registers the commandCreated handler.
    :return:
    """
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER
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


type_text_box_input = adsk.core.TextBoxCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers execute, destroy
    and most importantly validate handlers.

    :param args: A CommandCreatedEventArgs that allows access to the commands properties
        and inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Created Event")
    global type_text_box_input

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.validateInputs, command_validate, local_handlers=local_handlers
    )

    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(800, 800)
    args.command.setDialogInitialSize(800, 800)

    type_text_box_input = inputs.addTextBoxCommandInput(
        "typeTextBox", "Issues", "", 1, True
    )

    type_text_box_input.numRows = 12


def command_execute(args: adsk.core.CommandEventArgs):
    """
    This method is called when the user clicks the "OK" button. It concatenates the
    singular taxonomies into a combined one. For details see ~create_backend_taxonomy.
    It assembles the JSON representing the part. For details see ~create_backend_json.
    These types are then intersected. A constructor with the ordered UUIDs as string
    acts as guard per configuration.

    The method connects to the backend at /submit/part and submit/taxonomy and posts the
    created JSON files.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    part_dict = create_backend_json()

    req = urllib.request.Request("http://127.0.0.1:8000/submit/part")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    payload = json.dumps(
        part_dict,
        cls=CLSEncoder,
        indent=4,
    ).encode("utf-8")
    req.add_header("Content-Length", len(payload))
    try:
        response = urllib.request.urlopen(req, payload)
        print(response)
    except HTTPError as err:
        print(err.code)
        print(err.reason)

    load_project_taxonomy_to_config()

    # why not also update the taxonomy in the backend while we are at it?
    update_taxonomy_in_backend()
    app = adsk.core.Application.get()
    app.activeDocument.save("Saved by CLS-CAD: Submitted to backend.")


def create_backend_json():
    """
    Assembles the JSON representing the part by creating a type for every "provides"
    joint. Duplicate UUIDs are removed and instead added as "count" to the
    jointOrderInfo objects.

    :return: The created JSON/dict.
    """
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    provides_attributes = json.loads(
        getattr(
            design.rootComponent.attributes.itemByName(
                "CLS-PART", "ProvidesAttributes"
            ),
            "value",
            "[]",
        )
    )
    provides_parts = json.loads(
        getattr(
            design.rootComponent.attributes.itemByName("CLS-PART", "ProvidesParts"),
            "value",
            "[]",
        )
    )
    jo_infos = []
    # For each unique uuid (treated as one)
    for joint_typing in list(
        {x.value: x for x in design.findAttributes("CLS-INFO", "UUID")}.values()
    ):
        jo = joint_typing.parent
        jo_uuid = jo.attributes.itemByName("CLS-INFO", "UUID").value
        jo_req_formats = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresFormats").value
        )
        jo_req_parts = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresParts").value
        )
        jo_req_attributes = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresAttributes").value
        )
        jo_prov_formats = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "ProvidesFormats").value
        )
        jo_connect_type = (
            jo.attributes.itemByName("CLS-JOINT", "JointConnectType").value
            if jo.attributes.itemByName("CLS-JOINT", "JointConnectType")
            else "Rigid"
        )
        jo_infos.append(
            (
                jo_uuid,
                [
                    config.inverted_mappings["formats"][s] + "_formats"
                    for s in jo_req_formats
                ]
                + [
                    config.inverted_mappings["parts"][s] + "_parts"
                    for s in jo_req_parts
                ]
                + [
                    config.inverted_mappings["attributes"][s] + "_attributes"
                    for s in jo_req_attributes
                ],
                [
                    config.inverted_mappings["attributes"][s] + "_attributes"
                    for s in provides_attributes
                ]
                + [
                    config.inverted_mappings["parts"][s] + "_parts"
                    for s in provides_parts
                ]
                + [
                    config.inverted_mappings["formats"][s] + "_formats"
                    for s in jo_prov_formats
                ],
                jo_connect_type,
                len(jo_prov_formats),
            )
        )
    part_dict = {
        "_id": app.activeDocument.dataFile.id,
        "configurations": [],
        "meta": {},
        "jointOrigins": {},
    }

    # Only add to top-level intersection per provide
    # Needs slight change if provides ever becomes a real array
    for provides_uuid in [x[0] for x in jo_infos if x[4]]:
        requires_uuids = [x[0] for x in jo_infos if x[0] != provides_uuid]
        part_dict["configurations"].append(
            {
                "requiresJointOrigins": requires_uuids,
                "providesJointOrigin": provides_uuid,
            }
        )

    part_dict["meta"]["name"] = app.activeDocument.name
    part_dict["meta"]["forgeProjectId"] = app.activeDocument.dataFile.parentProject.id
    part_dict["meta"]["forgeFolderId"] = app.activeDocument.dataFile.parentFolder.id
    part_dict["meta"]["forgeDocumentId"] = app.activeDocument.dataFile.id
    part_dict["meta"]["cost"] = float(
        getattr(
            design.rootComponent.attributes.itemByName("CLS-PART", "COST"),
            "value",
            "1.0",
        )
    )
    part_dict["meta"]["availability"] = (
        float(
            getattr(
                design.rootComponent.attributes.itemByName("CLS-PART", "AVAILABILITY"),
                "value",
                "100.0",
            )
        )
        / 100.0
    )

    for info in jo_infos:
        part_dict["jointOrigins"][info[0]] = {
            "motion": info[3],
            "count": sum(
                cnt_uuid.value == info[0]
                for cnt_uuid in design.findAttributes("CLS-INFO", "UUID")
            ),
            "requires": info[1] if info[1] else [],
            "provides": info[2] if info[4] else [],
        }
    return part_dict


def command_validate(args: adsk.core.ValidateInputsEventArgs):
    """
    The method checks if there is at least one JointOrigin present that has received a
    ProvidesFormat. This implies the part can be connected at that JointOrigin, making
    it usable.

    :param args: adsk.core.ValidateInputsEventArgs: state.
    :return:
    """
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    global type_text_box_input
    if design.findAttributes("CLS-JOINT", "ProvidesFormats"):
        type_text_box_input.formatted_text = ""
        args.areInputsValid = True
    else:
        type_text_box_input.formatted_text = 'Parts need to at least provide one joint origin that has a  "Provides" type.'
        args.areInputsValid = False
    futil.log(f"{CMD_NAME} Command Preview Event")


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Logs that the command was destroyed (window closed). Currently, does not clean up
    anything.

    :param args: adsk.core.CommandEventArgs: inputs.
    :return:
    """
    global local_handlers
    local_handlers = []
    futil.log(f"{CMD_NAME} Command Destroy Event")
