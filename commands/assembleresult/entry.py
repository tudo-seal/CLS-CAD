import json
import os
from datetime import datetime
from functools import partial
from timeit import default_timer as timer

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
PALETTE_URL = f"{config.SERVER_URL}/static/assembleResult/index.html"
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SYNTH_ASSEMBLY"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")
USE_NO_HISTORY = True

local_handlers = []
progress_dialog: adsk.core.ProgressDialog = None


def start():
    """
    Creates the promoted "Assemble Result" command in the CLS-CAD tab.
    Registers the commandCreated handler.

    Returns:

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
    Removes this command from the CLS-CAD tab. Also removes the associated palette.

    Returns:

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
        futil.add_handler(palette.incomingFromHTML, palette_incoming)
        futil.log(
            f"{CMD_NAME}: Created a new palette: ID = {palette.id}, Name = {palette.name}"
        )

    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True


def center_in_window():
    app = adsk.core.Application.get()
    ui = app.userInterface
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent

    ui.activeSelections.clear()
    ui.activeSelections.add(root)
    find_cmd = ui.commandDefinitions.itemById("FindInWindow")
    find_cmd.execute()
    do_events_for_duration(0.2)
    ui.activeSelections.clear()
    do_events_for_duration(0.2)


def do_events_for_duration(duration: float):
    start_time = timer()
    while timer() - start_time < duration:
        adsk.doEvents()


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


def create_ground_joint(ground_joint):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    joints = root.joints
    joint_input = joints.createInput(
        ground_joint,
        adsk.fusion.JointGeometry.createByPoint(
            design.rootComponent.originConstructionPoint
        ),
    )
    joint_input.isFlipped = True
    joints.add(joint_input).isLightBulbOn = False


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
    futil.log(f"{CMD_NAME}: Palette incoming event.")

    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.name}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    # Read message sent from palette javascript and react appropriately.
    if message_action == "assembleMessage":
        palettes = ui.palettes
        palette = palettes.itemById(PALETTE_ID)
        palette.isVisible = False

        (name, cancelled) = ui.inputBox(
            "Please pick a name to describe the result.",
            "Synthesized Result Name",
            generate_id(),
        )
        if cancelled:
            return

        global progress_dialog
        progress_dialog = ui.createProgressDialog()
        progress_dialog.show(
            "Assembly Progress", "Preparing project for synthesized assemblies...", 0, 1
        )

        request_folder = create_results_folder(progress_dialog)

        progress_dialog.message = "Creating new assembly document..."

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if USE_NO_HISTORY:
            design.designType = DesignTypes.DirectDesignType

        doc.saveAs(
            name, request_folder, "Automatically synthesized assembly.", "Synthesized"
        )
        ui.commandDefinitions.itemById(
            "VisibilityOverrideCommand"
        ).controlDefinition.listItems.item(9).isSelected = False
        root = design.rootComponent
        for forge_document_id, infos in message_data["quantities"].items():
            do_events_for_duration(0.2)
            document = app.data.findFileById(forge_document_id)
            progress_dialog.progressValue = 0
            progress_dialog.maximumValue = infos["count"]
            progress_dialog.message = f"Inserting all instances of {document.name}..."
            inserted_occurrence = root.occurrences.addByInsert(
                document,
                adsk.core.Matrix3D.create(),
                True,
            )
            progress_dialog.progressValue = 1
            if infos["count"] > 1:
                parts_container = root.occurrences.addNewComponent(
                    adsk.core.Matrix3D.create()
                )
                parts_container.component.name = (
                    f"{inserted_occurrence.name} Quantity:{infos}"
                )
            for i in range(infos["count"] - 1):
                copied_occurrence = root.occurrences.addNewComponentCopy(
                    inserted_occurrence.component, adsk.core.Matrix3D.create()
                )
                copied_occurrence.breakLink()
                copied_occurrence.moveToComponent(parts_container)
                progress_dialog.progressValue += 1
            inserted_occurrence.breakLink()
            if infos["count"] > 1:
                inserted_occurrence.moveToComponent(parts_container)

        progress_dialog.message = "Creating all Joints..."
        progress_dialog.progressValue = 0
        for joint_info in message_data["instructions"]:
            target, source, count, motion = (
                joint_info["target"],
                joint_info["source"],
                joint_info["count"],
                joint_info["motion"],
            )

            attributes = design.findAttributes("CLS-INFO", "UUID")
            targets = [x.parent for x in attributes if x.value == target]
            sources = [x.parent for x in attributes if x.value == source]
            for i in range(count):
                adsk.doEvents()
                if target == "origin":
                    create_ground_joint(sources[i])
                else:
                    create_joint_from_typed_joint_origins(
                        targets[i], sources[i], motion
                    )
            center_in_window()

            progress_dialog.hide()

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


def create_result_class_folder(progress_dialog, name="User Picked Name"):
    results_folder = create_results_folder(progress_dialog)
    request_folder = wrapped_forge_call(
        partial(
            results_folder.dataFolders.itemByName,
            name,
        ),
        progress_dialog,
    )
    if not request_folder:
        request_folder = wrapped_forge_call(
            partial(results_folder.dataFolders.add, name),
            progress_dialog,
        )
    return request_folder


def create_results_folder(progress_dialog):
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
        results_folder = wrapped_forge_call(
            partial(root_folder_children.add, "Synthesized Assemblies"),
            progress_dialog,
        )
    return results_folder


def create_joint_from_typed_joint_origins(
    target_joint_origin, source_joint_origin, motion
):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    target_joint_origin.attributes.add("CLS-INFO", "UUID", generate_id())
    source_joint_origin.attributes.add("CLS-INFO", "UUID", generate_id())
    joints = root.joints
    joint_input = joints.createInput(target_joint_origin, source_joint_origin)
    joint_input.isFlipped = True
    if motion == "Revolute":
        joint_input.setAsRevoluteJointMotion(
            adsk.fusion.JointDirections.ZAxisJointDirection
        )
    new_joint = joints.add(joint_input)
    new_joint.isLightBulbOn = False if motion == "Rigid" else True


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
