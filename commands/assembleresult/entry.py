import json
import os
from collections import deque
from collections.abc import Callable
from datetime import datetime
from functools import partial

import adsk.core
from adsk.fusion import DesignTypes

from ... import config
from ...lib import fusion360utils as futil
from ...lib.general_utils import generate_id, wrapped_forge_call

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_assemble_results"
CMD_NAME = "Assemble"
CMD_Description = "Assembly synthesized results."
PALETTE_NAME = "Pick results for assembly"
IS_PROMOTED = True

PALETTE_ID = "ResultSelector"

PALETTE_URL = "http://localhost:8000/static/assembleResult/index.html"

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace("\\", "/")

# Set a default docking behavior for the palette
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight

WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

progress_dialog = None

USE_NO_HISTORY = True

# Readability
SubAssembly = dict
# These do not receive a state and neither do they output one.
# This is due to the state being implicitly given bz Fusion360 itself.
AssemblyInstruction = Callable[[], list["AssemblyInstruction"]]


# Executed when add-in is run.
def start():
    """
    Creates the promoted "Assemble Result" command in the CLS-CAD tab.
    Registers the commandCreated handler.

    Returns:

    """
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER
    )

    # Add command created handler. The function passed here will be executed when the command is executed.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar.
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    """
    Removes this command from the CLS-CAD tab. Also removes the associated palette.

    Returns:

    """
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
    """
    Called when the user clicks the command in CLS-CAD tab.
    Registers execute and destroy handlers.

    Args:
        args: A CommandCreatedEventArgs that allows access to the commands properties and inputs.

    Returns:

    """
    futil.log(f"{CMD_NAME}: Command created event.")

    # Create the event handlers you will need for this instance of the command
    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )


def command_execute(args: adsk.core.CommandEventArgs):
    """
    Executes immediately when the command is clicked in the CLS-CAD tab, since there are no inputs.
    If the palette does not already exist, it is created.
    The palette is sets to be visible and docked.

    Args:
        args: A CommandEventArgs that allows access to the commands properties and inputs.

    Returns:

    """
    futil.log(f"{CMD_NAME}: Command execute event.")

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
        futil.add_handler(palette.closed, palette_closed)
        futil.add_handler(palette.navigatingURL, palette_navigating)
        futil.add_handler(palette.incomingFromHTML, palette_incoming)
        futil.log(
            f"{CMD_NAME}: Created a new palette: ID = {palette.id}, Name = {palette.name}"
        )

    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True


# Use this to handle a user closing your palette.
def palette_closed(args: adsk.core.UserInterfaceGeneralEventArgs):
    """
    Logs that the palette was closed by the user.

    Args:
        args: Unused

    Returns:

    """
    futil.log(f"{CMD_NAME}: Palette was closed.")


# Use this to handle a user navigating to a new page in your palette.
def palette_navigating(args: adsk.core.NavigationEventArgs):
    """
    Logs that the palette url has changed.

    Args:
        args:

    Returns:

    """
    futil.log(f"{CMD_NAME}: Palette navigating event.")

    # Get the URL the user is navigating to:
    url = args.navigationURL

    log_msg = f"User is attempting to navigate to {url}\n"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    # Check if url is an external site and open in user's default browser.
    if url.startswith("http"):
        args.launchExternally = True


# Validation is optional, because we know the UUIDs exist, and if they don't
# the backend is out of date, making the only fix to recrawl or reupdate part
def create_part_insert_instruction(target: str, data: str):
    """
    For the given target and data (a connection), checks and creates the specified connections.
    For that connection, inserts the part contained in data for every matching target UUID found.
    If that count is more than one, create a new Component to hold the inserted parts.
    Create a joint (rigid or revolute) between the target UUID joint origin and the data's "provides" UUID joint origin.
    Then, new UUIDs are assigned to these JointOrigins, to prevent them being "reused".

    The assembly is DFS traversal of the result JSON object/tree, as the recursion happens on every connection,
    not after the loop completes. This avoids edge-cases of identical parts with different subtrees being present.
    This DFS traversal is handled by create_initial_instructions, this method only creates the Callables.

    Args:
        data: Contains the data of the part to insert and connect.
        target: Contains the UUID of the Joint Origin to connect to.

    Returns:

    """

    def instruction():
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        global progress_dialog
        additional_instructions: list["AssemblyInstruction"] = list()

        progress_dialog.show("Assembly Progress", "Initialising layer...", 0, 1)
        attributes = design.findAttributes("CLS-INFO", "UUID")
        joint_origins_1 = [x.parent for x in attributes if x.value == target]
        progress_dialog.message = "Inserting Components..."
        progress_dialog.maximumValue = len(joint_origins_1)
        progress_dialog.progressValue = 0
        inserted_design = root.occurrences.addByInsert(
            app.data.findFileById(data["forgeDocumentId"]),
            adsk.core.Matrix3D.create(),
            True,
        )
        progress_dialog.progressValue += 1
        if len(joint_origins_1) > 1:
            assembly_layer_container = root.occurrences.addNewComponent(
                adsk.core.Matrix3D.create()
            )
            assembly_layer_container.component.name = inserted_design.name + " Group"
            for i in range(len(joint_origins_1) - 1):
                copied_occurrence = root.occurrences.addExistingComponent(
                    inserted_design.component, adsk.core.Matrix3D.create()
                )
                copied_occurrence.breakLink()
                copied_occurrence.moveToComponent(assembly_layer_container)
                progress_dialog.progressValue += 1
        if USE_NO_HISTORY:
            inserted_design.breakLink()
        # Fusion360 forbids ordering these differently
        if len(joint_origins_1) > 1:
            inserted_design.moveToComponent(assembly_layer_container)

        # Re-query for newly inserted
        attributes = design.findAttributes("CLS-INFO", "UUID")
        joint_origins_2 = [x.parent for x in attributes if x.value == data["provides"]]
        if len(joint_origins_1) != len(joint_origins_2):
            print("Critical Error")
            ui.messageBox(
                f'Critical Error. Number Required: {len(joint_origins_1)}  for {target}\n Number Provided: {len(joint_origins_2)} for {data["provides"]}'
            )
            joint_origins_2 = [
                x.parent for x in attributes if x.value == data["provides"]
            ]
            print(len(joint_origins_2))
            return

        # This is a completely different design, so the uuids need to be changed to be unique
        uuid_requires = str(generate_id())
        uuid_provides = str(generate_id())
        progress_dialog.message = "Setting new attributes..."
        progress_dialog.maximumValue = len(joint_origins_1) * 2
        progress_dialog.progressValue = 0
        for joint_origin in joint_origins_1:
            joint_origin.attributes.add("CLS-INFO", "UUID", uuid_requires)
            progress_dialog.progressValue += 1
        for joint_origin in joint_origins_2:
            joint_origin.attributes.add("CLS-INFO", "UUID", uuid_provides)
            progress_dialog.progressValue += 1

        # Create all joints
        progress_dialog.message = "Creating joints..."
        progress_dialog.maximumValue = len(joint_origins_1)
        progress_dialog.progressValue = 0
        for requires, provides in zip(joint_origins_1, joint_origins_2):
            joints = root.joints
            joint_input = joints.createInput(provides, requires)
            joint_input.isFlipped = True
            if data["motion"] == "Revolute":
                joint_input.setAsRevoluteJointMotion(
                    adsk.fusion.JointDirections.ZAxisJointDirection
                )
            joints.add(joint_input)
            progress_dialog.progressValue += 1
        # This is in outer, because inner just targets all UUIDs
        # If the previous step inserted six times, the next step
        # Will have six requires present instead of one
        progress_dialog.message = "Proceeding to next layer..."
        progress_dialog.maximumValue = 1000
        progress_dialog.progressValue = 0
        for i in range(1000):
            progress_dialog.progressValue += 1
        progress_dialog.message = ""
        progress_dialog.progressValue = 0
        progress_dialog.hide()
        # Post-Processing and Assembly DSL features would live here
        return additional_instructions

    return instruction


def assembly_machine(instructions: deque[AssemblyInstruction]):
    while instructions:
        instructions.extendleft(instructions.popleft()())


def create_initial_instructions(
    sub_assembly: SubAssembly,
    instructions: deque["AssemblyInstruction"] = None,
):
    if not instructions:
        instructions = deque()
    for key, value in sub_assembly["connections"].items():
        instructions.append(create_part_insert_instruction(key, value))
        create_initial_instructions(value, instructions)
    return instructions


def create_offset_joint_origin_in_occurence(
    source_joint_origin, offset_vector, occurrence
):
    """
    Creates a JointOrigin that is offset from its parent geometry by specified vector.
    The JointOrigin is created in specified occurrence.

    Args:
        source_joint_origin: The JointOrigin the new JointOrigin is an offset copy off.
        offset_vector: The offset Vector3D {x, y, z}
        occurrence: The occurrence to create the JointOrigin in

    Returns:

    """
    joint_origin_input = occurrence.component.jointOrigins.createInput(
        source_joint_origin.geometry
    )
    joint_origin_input.offsetX = adsk.core.ValueInput.createByReal(offset_vector.x)
    joint_origin_input.offsetY = adsk.core.ValueInput.createByReal(offset_vector.y)
    joint_origin_input.offsetZ = adsk.core.ValueInput.createByReal(offset_vector.z)
    return occurrence.component.jointOrigins.add(joint_origin_input)


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    """
    Handles incoming messages from the JavaScript portion of the palette.
    Receives an "assembleMessage" that contains the JSON representation of the assembly as data.
    If not present, the necessary folders in the project are created.
    The initial part of the assembly is inserted and then assemble_recursively is called to start the assembly process.

    Sets the document to direct modeling mode during assembly to improve performance and avoid congested history.

    Args:
        html_args:

    Returns:

    """
    # General logging for debug.
    futil.log(f"{CMD_NAME}: Palette incoming event.")

    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.name}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    # TODO ******** Your palette reaction code here ********

    # Read message sent from palette javascript and react appropriately.
    if message_action == "assembleMessage":
        palettes = ui.palettes
        palette = palettes.itemById(PALETTE_ID)
        palette.isVisible = False

        global progress_dialog
        progress_dialog = ui.createProgressDialog()
        progress_dialog.show(
            "Assembly Progress", "Preparing project for synthesized assemblies...", 0, 1
        )

        root_folder_children = (
            app.activeDocument.dataFile.parentProject.rootFolder.dataFolders
            if app.activeDocument.dataFile is not None
            else app.data.activeProject.rootFolder.dataFolders
        )

        results_folder = wrapped_forge_call(
            partial(root_folder_children.itemByName, "Synthesized Assemblies"),
            progress_dialog,
        )
        if not results_folder:
            wrapped_forge_call(
                partial(root_folder_children.add, "Synthesized Assemblies"),
                progress_dialog,
            )
            results_folder = wrapped_forge_call(
                partial(root_folder_children.itemByName, "Synthesized Assemblies"),
                progress_dialog,
            )

        request_folder = wrapped_forge_call(
            partial(
                results_folder.dataFolders.itemByName,
                "User Picked Name",
            ),
            progress_dialog,
        )
        if not request_folder:
            wrapped_forge_call(
                partial(results_folder.dataFolders.add, "User Picked Name"),
                progress_dialog,
            )

        progress_dialog.message = "Creating new assembly document..."

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if USE_NO_HISTORY:
            design.designType = DesignTypes.DirectDesignType
        # Naming and stuff will need to be cleaned up, and multi-assembly
        doc.saveAs(str(generate_id()), request_folder, "", "")
        progress_dialog.progressValue = 1
        progress_dialog.message = "Inserting assembly base..."
        progress_dialog.progressValue = 0

        root = design.rootComponent
        inserted_document = root.occurrences.addByInsert(
            app.data.findFileById(message_data["forgeDocumentId"]),
            adsk.core.Matrix3D.create(),
            True,
        )
        inserted_document.breakLink()

        progress_dialog.progressValue = 1
        progress_dialog.message = "Verifying base provides count..."
        progress_dialog.progressValue = 0

        attributes = design.findAttributes("CLS-INFO", "UUID")
        root_joint_origin = [
            x.parent for x in attributes if x.value == message_data["provides"]
        ]
        print(len(root_joint_origin))
        if len(root_joint_origin) == 1:
            progress_dialog.progressValue = 1
            progress_dialog.message = "Anchoring base..."
            progress_dialog.progressValue = 0
            # Anchor base of assembly to origin (optional)
            joints = root.joints
            joint_input = joints.createInput(
                root_joint_origin[0],
                adsk.fusion.JointGeometry.createByPoint(
                    design.rootComponent.originConstructionPoint
                ),
            )
            joint_input.isFlipped = True
            joints.add(joint_input)
            progress_dialog.progressValue = 1
            progress_dialog.message = "Beginning assembly..."
            progress_dialog.progressValue = 0

            assembly_machine(create_initial_instructions(message_data))

            progress_dialog.hide()
        else:
            # ToDo: Query Yes/No continue anyways
            ui.messageBox("Multiple root joint origins.")

    if message_action == "readyNotification":
        # ADSK was injected, so now we send the payload
        futil.log("Got Ready, sending projectID")
        project_id = (
            app.activeDocument.dataFile.parentProject.id
            if app.activeDocument.dataFile is not None
            else app.data.activeProject.id
        )
        palettes = ui.palettes
        palette = palettes.itemById(PALETTE_ID)
        palette.sendInfoToHTML("projectIDMessage", project_id)

    # Return value.
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {current_time}"


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    Logs the command terminating. This is instantly the case upon clicking, as the command only opens the palette.

    Args:
        args: Unused

    Returns:

    """
    # General logging for debug.
    futil.log(f"{CMD_NAME}: Command destroy event.")

    global local_handlers
    local_handlers = []
