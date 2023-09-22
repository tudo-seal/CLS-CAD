import json
import os
import re
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
DISPLAY_TIME = True
NO_GRAPHICS = False
remaining_assemblies = 0
design: adsk.fusion.Design = adsk.fusion.Design.cast(None)
bucket_primed = False

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
    if NO_GRAPHICS:
        return
    global progress_dialog
    app = adsk.core.Application.get()
    ui = app.userInterface
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent

    progress = progress_dialog.progressValue
    progress_dialog.hide()
    ui.activeSelections.add(root)
    find_cmd = ui.commandDefinitions.itemById("FindInWindow")
    find_cmd.execute()
    do_events_for_duration(0.01)
    ui.activeSelections.clear()
    adsk.doEvents()
    progress_dialog.show(
        progress_dialog.title, progress_dialog.message, 0, progress_dialog.maximumValue
    )
    progress_dialog.progressValue = progress


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
    global design
    root = design.rootComponent
    joints = root.joints
    joint_input = joints.createInput(
        ground_joint,
        adsk.fusion.JointGeometry.createByPoint(
            design.rootComponent.originConstructionPoint
        ),
    )
    joint_input.isFlipped = True
    joint = joints.add(joint_input)
    joint.isLightBulbOn = False
    return joint


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

        create_assembly_document(message_data, name)

    if message_action == "assembleAllMessage":
        palettes = ui.palettes
        palette = palettes.itemById(PALETTE_ID)
        palette.isVisible = False

        result = ui.messageBox(
            "This will take a considerable amount of time depending on the number of results."
            "\n"
            "\n"
            "Do you wish to continue?",
            "Export",
            adsk.core.MessageBoxButtonTypes.OKCancelButtonType,
        )
        if result:
            return
        (name, cancelled) = ui.inputBox(
            "Please pick a name to describe the result.",
            "Synthesized Result Name",
            generate_id(),
        )
        if cancelled:
            return

        create_assembly_documents(
            message_data["results"], message_data["partcounts"], name
        )

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


def buckets_saved_handler(args: adsk.core.DataEventArgs):
    global bucket_primed
    if "Parts Template" in args.file.name and args.file.versionNumber == 2:
        bucket_primed = False


def create_assembly_documents(data, maxcounts, name):
    global progress_dialog, NO_GRAPHICS, design, bucket_primed
    bucket_primed = True
    NO_GRAPHICS = True
    progress_dialog = ui.createProgressDialog()
    progress_dialog.show(
        "Assembly Progress", "Preparing project for synthesized assemblies...", 0, 1
    )
    request_folder = create_results_folder(progress_dialog, name)
    progress_dialog.message = "Creating parts template for all assemblies..."
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(
        doc.products.itemByProductType("DesignProductType")
    )
    bucket_name = f"Parts Template"
    doc.saveAs(
        bucket_name,
        request_folder,
        "Automatically synthesized assembly base.",
        "Synthesized",
    )
    futil.add_handler(
        app.dataFileComplete, buckets_saved_handler, local_handlers=local_handlers
    )
    ui.commandDefinitions.itemById(
        "VisibilityOverrideCommand"
    ).controlDefinition.listItems.item(9).isSelected = False
    for forge_document_id, count in maxcounts.items():
        insert_part_into_bucket_from_quantity_information(forge_document_id, count)
    design.designType = DesignTypes.DirectDesignType
    progress_dialog.hide()
    doc.save("Part Template initialized.")
    while bucket_primed:
        adsk.doEvents()
    progress_dialog.show(
        "Assembly Progress",
        "Creating assemblies...",
        0,
        len(data),
    )
    progress_dialog.progressValue = 0
    bucket_datafile = doc.dataFile
    for i in range(len(data)):
        assembly_datafile = wrapped_forge_call(
            partial(bucket_datafile.copy, bucket_datafile.parentFolder)
        )
        assembly_datafile.name = f"Assembly {i}"
        # while not assembly_datafile.isComplete:
        #    adsk.doEvents()
        doc = app.documents.open(assembly_datafile)
        progress_dialog.progressValue = i + 1
        design = adsk.fusion.Design.cast(
            doc.products.itemByProductType("DesignProductType")
        )
        link_occurrences = create_links(data[i]["links"])
        move_part_to_links_from_instructions(data[i]["instructions"], link_occurrences)
        progress_dialog.maximumValue = data[i]["count"]
        create_joints_from_instructions(data[i]["instructions"])
        # Order is switched, internal F360 occurrence list gets very confused else
        remove_tagged_occurrences("Meta", "forgeDocumentId")
        for _, link_occurrence in link_occurrences.items():
            link_occurrence.isLightBulbOn = True
        doc.save("Finished assembly")
        doc.close(False)
        progress_dialog.hide()
        progress_dialog.show(
            "Assembly Progress",
            "Creating assemblies...",
            0,
            len(data),
        )
        progress_dialog.progressValue = i + 1
    NO_GRAPHICS = False
    progress_dialog.hide()


def create_assembly_document(data, name):
    global progress_dialog, design
    total_time = timer()
    progress_dialog = ui.createProgressDialog()
    progress_dialog.show(
        "Assembly Progress", "Preparing project for synthesized assemblies...", 0, 1
    )
    request_folder = create_results_folder(progress_dialog, "Synthesized Assemblies")
    progress_dialog.message = "Creating new assembly document..."
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = doc.products.itemByProductType("DesignProductType")
    doc.saveAs(
        name, request_folder, "Automatically synthesized assembly.", "Synthesized"
    )
    ui.commandDefinitions.itemById(
        "VisibilityOverrideCommand"
    ).controlDefinition.listItems.item(9).isSelected = False
    for forge_document_id, infos in data["quantities"].items():
        if not NO_GRAPHICS:
            do_events_for_duration(0.05)
        insert_part_into_bucket_from_quantity_information(
            forge_document_id, infos["count"]
        )
    design.designType = DesignTypes.DirectDesignType
    link_occurrences = create_links(data["links"])
    move_part_to_links_from_instructions(data["instructions"], link_occurrences)
    remove_tagged_occurrences("Meta", "forgeDocumentId")
    progress_dialog.maximumValue = data["count"]
    create_joints_from_instructions(data["instructions"])
    progress_dialog.hide()
    total_time = timer() - total_time
    if DISPLAY_TIME:
        ui.messageBox(
            f"""
            Total time elapsed: {total_time}
        """,
            "Time Statistics",
        )


def insert_part_into_bucket_from_quantity_information(forge_document_id, count):
    global progress_dialog
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    document = app.data.findFileById(forge_document_id)
    progress_dialog.progressValue = 0
    progress_dialog.maximumValue = count
    progress_dialog.message = f"Inserting all instances of {document.name}..."

    parts_container = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    parts_container.isLightBulbOn = not NO_GRAPHICS
    inserted_occurrence = parts_container.component.occurrences.addByInsert(
        document,
        adsk.core.Matrix3D.create(),
        True,
    )
    parts_container.component.name = f"{inserted_occurrence.name}s Quantity:{count}"
    parts_container.attributes.add("Meta", "forgeDocumentId", forge_document_id)
    progress_dialog.progressValue = 1

    if count > 1:
        create_copies_of_part_in_container(count, inserted_occurrence, parts_container)
    metadata_occurrence = root.occurrences.addExistingComponent(
        inserted_occurrence.component, adsk.core.Matrix3D.create()
    )

    # Add back in the type information in assembly context
    metadata_occurrence.breakLink()
    parts_container_contents = parts_container.childOccurrences
    for i in range(metadata_occurrence.component.jointOrigins.count):
        attribute_uuid = metadata_occurrence.component.jointOrigins.item(
            i
        ).attributes.itemByName("CLS-INFO", "UUID")
        if attribute_uuid is None:
            continue
        uuid = attribute_uuid.value

        for k in range(count):
            parts_container_contents.item(k).component.jointOrigins.item(
                i
            ).createForAssemblyContext(parts_container_contents.item(k)).attributes.add(
                "CLS-INFO", "UUID", uuid
            )
    metadata_occurrence.deleteMe()


def create_copies_of_part_in_container(count, inserted_occurrence, parts_container):
    global progress_dialog
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    object_collection_wrapper_for_part = adsk.core.ObjectCollection.create()
    object_collection_wrapper_for_part.add(inserted_occurrence)
    rectangular_pattern_features = (
        parts_container.component.features.rectangularPatternFeatures
    )
    quantity_one = adsk.core.ValueInput.createByString(str(count))
    distance_one = adsk.core.ValueInput.createByString("0 cm")
    quantity_two = adsk.core.ValueInput.createByString("1")
    distance_two = adsk.core.ValueInput.createByString("0 cm")
    rectangular_pattern_feature_input = rectangular_pattern_features.createInput(
        object_collection_wrapper_for_part,
        root.xConstructionAxis,
        quantity_one,
        distance_one,
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType,
    )
    rectangular_pattern_feature_input.setDirectionTwo(
        root.yConstructionAxis, quantity_two, distance_two
    )
    rectangular_pattern_features.add(rectangular_pattern_feature_input)
    for i in range(count - 1):
        progress_dialog.progressValue += 1


def create_links(count):
    app.activeDocument.dataFile
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    link_occurrences = {}
    for i in range(count):
        link = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        link.isLightBulbOn = not NO_GRAPHICS
        link.component.name = f"link_{i}"
        link_occurrences[f"link{i}"] = link
    return link_occurrences


def move_part_to_links_from_instructions(
    instructions, link_occurrences, group: str = "Meta", tag: str = "forgeDocumentId"
):
    global design
    for joint_info in instructions:
        link, move, count = (
            joint_info["link"],
            joint_info["move"],
            joint_info["count"],
        )
        bucket: adsk.fusion.Occurrence = [
            x.parent for x in design.findAttributes(group, tag) if x.value == move
        ][0]
        move_to = link_occurrences[link]
        if count > 1:
            move_to = link_occurrences[link].component.occurrences.addNewComponent(
                adsk.core.Matrix3D.create()
            )
            move_to.component.name = f"{re.sub(' v[0-9]+:*[0-9]*', '', bucket.childOccurrences.item(0).name)}s - Quantity:{count}"
        for i in range(count):
            bucket.childOccurrences
            bucket.childOccurrences.item(0).moveToComponent(move_to)


def remove_tagged_occurrences(group: str, tag: str):
    global design
    for bucket_occurrence in [x.parent for x in design.findAttributes(group, tag)]:
        bucket_occurrence.deleteMe()


def create_joints_from_instructions(instructions):
    global progress_dialog
    global design
    progress_dialog.message = "Creating all Joints..."
    progress_dialog.progressValue = 0
    for joint_info in instructions:
        target, source, count, motion, link_id = (
            joint_info["target"],
            joint_info["source"],
            joint_info["count"],
            joint_info["motion"],
            joint_info["link"],
        )

        attributes = design.findAttributes("CLS-INFO", "UUID")
        targets: list[adsk.fusion.JointOrigin] = [
            x.parent for x in attributes if x.value == target
        ]
        sources: list[adsk.fusion.JointOrigin] = [
            x.parent for x in attributes if x.value == source
        ]
        for i in range(count):
            if not NO_GRAPHICS:
                adsk.doEvents()
            if target == "origin":
                create_ground_joint(sources[i])
            else:
                create_joint_from_typed_joint_origins(targets[i], sources[i], motion)
            progress_dialog.progressValue += 1

        center_in_window()


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


def create_results_folder(progress_dialog, folder_name: str):
    root_folder_children = (
        app.activeDocument.dataFile.parentProject.rootFolder.dataFolders
        if app.activeDocument.dataFile is not None
        else app.data.activeProject.rootFolder.dataFolders
    )
    results_folder = wrapped_forge_call(
        partial(root_folder_children.itemByName, folder_name),
        progress_dialog,
    )
    if not results_folder:
        results_folder = wrapped_forge_call(
            partial(root_folder_children.add, folder_name),
            progress_dialog,
        )
    return results_folder


def create_joint_from_typed_joint_origins(
    target_joint_origin,
    source_joint_origin,
    motion,
    link: adsk.fusion.Occurrence = None,
):
    global design
    root = design.rootComponent
    target_joint_origin.attributes.add("CLS-INFO", "UUID", generate_id())
    source_joint_origin.attributes.add("CLS-INFO", "UUID", generate_id())
    joints = root.joints if not link else link.component.joints
    joint_input = joints.createInput(target_joint_origin, source_joint_origin)
    joint_input.isFlipped = True
    if motion == "Revolute":
        joint_input.setAsRevoluteJointMotion(
            adsk.fusion.JointDirections.ZAxisJointDirection
        )
    new_joint = joints.add(joint_input)
    new_joint.isLightBulbOn = False if motion == "Rigid" else True
    return new_joint


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
