import adsk.core
from adsk.fusion import DesignTypes

from ...lib import fusion360utils as futil
from ...lib.cls_python_compat import *
from ...lib.general_utils import *
from ..checkandsubmit.entry import create_backend_json

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_migrate_uuids"
CMD_NAME = "Migrate UUIDs and Fix Files"
CMD_DESCRIPTION = "Migrate UUIDs and fix nested components."
IS_PROMOTED = False
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "CRAWL"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")

local_handlers = []
progress_dialog: adsk.core.ProgressDialog = None


def start():
    """
    Creates the promoted "Migrate UUIDs" command in the CLS-CAD tab.

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


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Called when the user clicks the command in CLS-CAD tab. Registers execute and
    destroy handlers.

    :param args: adsk.core.CommandCreatedEventArgs: and inputs.
    :return:
    """
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )


def recursively_submit(folders: adsk.core.DataFolders):
    """
    For every passed DataFolder, all contained Files are opened that are f3d files. The
    corresponding JSON for the backend is created and submitted if the file is valid.
    (Provides at least one format) If the file is not valid, it is skipped. This may be
    changed to provide an error report in the future. The file traversal is DFS, after a
    single folder is done, its children are processed immediately.

    :param folders: adsk.core.DataFolders:
    :return:
    """
    global progress_dialog
    for folder in wrapped_forge_call(folders.asArray, progress_dialog):
        progress_dialog.progressValue = 0
        progress_dialog.message = f'Preparing to process Folder "{folder.name}"...'
        if folder.name in ["Synthesized Assemblies", "Taxonomies"]:
            continue
        submit_and_update_files_in_folder(folder)
        recursively_submit(folder.dataFolders)


def submit_and_update_files_in_folder(folder):
    """
    Open all files contained in a folder and submit them the backend by calling the
    CheckAndSubmit command.

    Before submitting, remove all nested subcomponents and flatten the assembly tree.
    :param folder: The folder in which to submit all files.
    :return:
    """
    global progress_dialog
    for file in wrapped_forge_call(folder.dataFiles.asArray, progress_dialog):
        if not file.fileExtension == "f3d":
            continue
        modified = False
        progress_dialog.maximumValue = len(
            wrapped_forge_call(folder.dataFiles.asArray, progress_dialog)
        )
        progress_dialog.message = (
            f'Folder "{folder.name}" contains {len(wrapped_forge_call(folder.dataFiles.asArray, progress_dialog))} files.\n\n'
            f"Processing..."
        )
        app = adsk.core.Application.get()
        document = app.documents.open(file)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if design.designType == DesignTypes.DirectDesignType:
            design.designType = DesignTypes.ParametricDesignType
        root_comp = design.rootComponent
        features = root_comp.features
        remove_features = features.removeFeatures
        while root_comp.allOccurrences.count > 0:
            occ = root_comp.allOccurrences.item(0)
            if occ.isReferencedComponent:
                occ.breakLink()

            while occ.bRepBodies.count > 0:
                body = occ.bRepBodies.item(0)
                body.moveToComponent(root_comp)
                modified = True
            remove_features.add(occ)

        for unique_attribute in list(
            {x.value: x for x in design.findAttributes("CLS-INFO", "UUID")}.values()
        ):
            new_uuid = generate_id()
            for attribute in [
                x
                for x in design.findAttributes("CLS-INFO", "UUID")
                if x.value == unique_attribute.value
            ]:
                attribute.value = new_uuid
            modified = True
        if design.findAttributes("CLS-JOINT", "ProvidesFormats"):
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
            document.save('Saved by "Migrate UUIDs and Fix Files"')
            document.close(False)
        else:
            if modified:
                document.save('Saved by "Migrate UUIDs and Fix Files"')
            document.close(False)
        progress_dialog.progressValue += 1


def command_execute(args: adsk.core.CommandEventArgs):
    """
    Executes immediately when user clicks the button in CLS-CAD tab as there are no
    command inputs. Prompts the user to confirm beginning the lengthy crawling process.
    Fetches the activeDocuments (priority, else active side browser position) projects
    root folder. Recursively traverses this initial set of folders.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    futil.log(f"{CMD_NAME} Command Execute Event")

    result = ui.messageBox(
        "This will take a considerable amount of time and is intended to be used when large changes to a project have "
        "been made/a old project has been setup or imported.\nEach file in the project will be opened. "
        "Eligible parts will be submitted to the server, non-eligible parts will be added to an error report.\n\n"
        "Do you wish to continue?",
        "Proceed to migrate and upload UUIDs?",
        adsk.core.MessageBoxButtonTypes.OKCancelButtonType,
    )
    if not result:
        global progress_dialog
        progress_dialog = ui.createProgressDialog()
        progress_dialog.show("Crawl Progress", "Beginning to crawl...", 0, 1)
        root_folder = (
            app.activeDocument.dataFile.parentProject.rootFolder
            if app.activeDocument.dataFile is not None
            else app.data.activeProject.rootFolder
        )
        submit_and_update_files_in_folder(root_folder)
        recursively_submit(root_folder.dataFolders)

        load_project_taxonomy_to_config()

        progress_dialog.message = "Sending current taxonomy to backend..."
        payload_dict = create_backend_taxonomy()
        req = urllib.request.Request("http://127.0.0.1:8000/submit/taxonomy")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        payload = json.dumps(payload_dict, indent=4).encode("utf-8")
        req.add_header("Content-Length", len(payload))

        progress_dialog.hide()


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
