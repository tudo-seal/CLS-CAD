import json
import os
import uuid
from datetime import datetime

import adsk.core
from adsk.fusion import DesignTypes

from ... import config
from ...lib import fusion360utils as futil

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_assemble_results"
CMD_NAME = "Assemble"
CMD_Description = "Assembly synthesized results."
PALETTE_NAME = "Pick results for assembly"
IS_PROMOTED = True

PALETTE_ID = "ResultSelector"

PALETTE_URL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "html", "index.html"
)

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace("\\", "/")

# Set a default docking behavior for the palette
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight

WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

progressDialog = None

USE_NO_HISTORY = True


# Executed when add-in is run.
def start():
    """
    Creates the promoted assemble result command in the CLS-CAD tab.
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
    if palette is None:
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
def assemble_recursively(part: dict):
    """
    For the given part, checks the specified connections.
    For each connection, inserts that part for every matching UUID found.
    If that count is more than one, create a new Component to hold the inserted parts.
    Create a joint (rigid or revolute) between the matching UUID joint origin and the "provides" UUID joint origin.
    Then, new UUIDs are assigned to these JointOrigins, to prevent them being "reused".

    The assembly is DFS traversal of the result JSON object/tree, as the recursion happens on every connection,
    not after the loop completes. This avoids edge-cases of identical parts with different sub-trees being present.

    Args:
        part: Contains the current part of the assembly that is being processed.

    Returns:

    """
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    global progressDialog

    for key, value in part["connections"].items():
        progressDialog.show("Assembly Progress", "Initialising layer...", 0, 1)
        attributes = design.findAttributes("CLS-INFO", "UUID")
        joint_origins_1 = [x.parent for x in attributes if x.value == key]
        progressDialog.message = "Inserting Components..."
        progressDialog.maximumValue = len(joint_origins_1)
        progressDialog.progressValue = 0
        insertedDesign = root.occurrences.addByInsert(
            app.data.findFileById(value["forgeDocumentId"]),
            adsk.core.Matrix3D.create(),
            True,
        )
        progressDialog.progressValue += 1
        if len(joint_origins_1) > 1:
            assembly_layer_container = root.occurrences.addNewComponent(
                adsk.core.Matrix3D.create()
            )
            assembly_layer_container.component.name = insertedDesign.name + " Group"
            for i in range(len(joint_origins_1) - 1):
                copiedOccurence = root.occurrences.addExistingComponent(
                    insertedDesign.component, adsk.core.Matrix3D.create()
                )
                copiedOccurence.breakLink()
                copiedOccurence.moveToComponent(assembly_layer_container)
                progressDialog.progressValue += 1
        if USE_NO_HISTORY:
            insertedDesign.breakLink()
        # Fusion360 forbids ordering these differently
        if len(joint_origins_1) > 1:
            insertedDesign.moveToComponent(assembly_layer_container)

        # Re-query for newly inserted
        attributes = design.findAttributes("CLS-INFO", "UUID")
        joint_origins_2 = [x.parent for x in attributes if x.value == value["provides"]]
        if len(joint_origins_1) != len(joint_origins_2):
            print("Critical Error")
            ui.messageBox(
                f'Critical Error. Number Required: {len(joint_origins_1)}  for {key}\n Number Provided: {len(joint_origins_2)} for {value["provides"]}'
            )
            joint_origins_2 = [
                x.parent for x in attributes if x.value == value["provides"]
            ]
            print(len(joint_origins_2))
            return

        # This is a completely different design, so the uuids need to be changed to be unique
        uuid_requires = str(uuid.uuid4())
        uuid_provides = str(uuid.uuid4())
        progressDialog.message = "Setting new attributes..."
        progressDialog.maximumValue = len(joint_origins_1) * 2
        progressDialog.progressValue = 0
        for joint_origin in joint_origins_1:
            joint_origin.attributes.add("CLS-INFO", "UUID", uuid_requires)
            progressDialog.progressValue += 1
        for joint_origin in joint_origins_2:
            joint_origin.attributes.add("CLS-INFO", "UUID", uuid_provides)
            progressDialog.progressValue += 1

        # Create all joints
        progressDialog.message = "Creating joints..."
        progressDialog.maximumValue = len(joint_origins_1)
        progressDialog.progressValue = 0
        for requires, provides in zip(joint_origins_1, joint_origins_2):
            joints = root.joints
            joint_input = joints.createInput(provides, requires)
            joint_input.isFlipped = True
            if value["motion"] == "Revolute":
                joint_input.setAsRevoluteJointMotion(
                    adsk.fusion.JointDirections.ZAxisJointDirection
                )
            joints.add(joint_input)
            progressDialog.progressValue += 1
        # This is in outer, because inner just targets all UUIDs
        # If the previous step inserted six times, the next step
        # Will have six requires present instead of one
        progressDialog.message = "Proceeding to next layer..."
        progressDialog.maximumValue = 1000
        progressDialog.progressValue = 0
        for i in range(1000):
            progressDialog.progressValue += 1
        progressDialog.message = ""
        progressDialog.progressValue = 0
        progressDialog.hide()
        assemble_recursively(value)


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
        root_folder_children = (
            app.activeDocument.dataFile.parentProject.rootFolder.dataFolders
            if app.activeDocument.dataFile is not None
            else app.data.activeProject.rootFolder.dataFolders
        )
        results_folder = (
            root_folder_children.itemByName("Synthesized Assemblies")
            if root_folder_children.itemByName("Synthesized Assemblies")
            else root_folder_children.add("Synthesized Assemblies")
        )
        request_folder = (
            results_folder.dataFolders.itemByName("User Picked Name")
            if results_folder.dataFolders.itemByName("User Picked Name")
            else results_folder.dataFolders.add("User Picked Name")
        )
        global progressDialog
        progressDialog = ui.createProgressDialog()
        progressDialog.show(
            "Assembly Progress", "Creating new assembly document...", 0, 1
        )
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        # Naming and stuff will need to be cleaned up, and multi-assembly
        doc.saveAs(str(uuid.uuid4()), request_folder, "", "")
        progressDialog.progressValue = 1
        progressDialog.message = "Inserting assembly base..."
        progressDialog.progressValue = 0
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        root.occurrences.addByInsert(
            app.data.findFileById(message_data["forgeDocumentId"]),
            adsk.core.Matrix3D.create(),
            False,
        )
        progressDialog.progressValue = 1
        progressDialog.message = "Verifying base provides count..."
        progressDialog.progressValue = 0

        attributes = design.findAttributes("CLS-INFO", "UUID")
        root_joint_origin = [
            x.parent for x in attributes if x.value == message_data["provides"]
        ]
        if len(root_joint_origin) == 1:
            progressDialog.progressValue = 1
            progressDialog.message = "Anchoring base..."
            progressDialog.progressValue = 0
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
            progressDialog.progressValue = 1
            progressDialog.message = "Beginning assembly..."
            progressDialog.progressValue = 0

            if USE_NO_HISTORY:
                design.designType = DesignTypes.DirectDesignType

            assemble_recursively(message_data)

            progressDialog.hide()
        else:
            # ToDo: Query Yes/No continue anyways
            ui.messageBox("Multiple root joint origins.")

    # Return value.
    now = datetime.now()
    currentTime = now.strftime("%H:%M:%S")
    html_args.returnData = f"OK - {currentTime}"


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
