import adsk.core

from ...lib import fusion360utils as futil
from ...lib.cls_python_compat import *
from ...lib.general_utils import *
from ..checkandsubmit.entry import create_backend_json

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_crawl_project"
CMD_NAME = "Crawl Project"
CMD_DESCRIPTION = "Crawl project files and collect all types."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "CRAWL"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")


local_handlers = []
progress_dialog: adsk.core.ProgressDialog = None


def start():
    """
    Creates the promoted "Crawl Project" command in the CLS-CAD tab.

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

    :param folders: adsk.core.DataFolders: The set of folders to recursively crawl.
    :return:
    """
    global progress_dialog
    for folder in wrapped_forge_call(folders.asArray, progress_dialog):
        progress_dialog.progressValue = 0
        progress_dialog.message = f'Preparing to process Folder "{folder.name}"...'
        # ignore auto-generated content
        if folder.name in ["Synthesized Assemblies", "Taxonomies"]:
            continue
        submit_files_in_folder(folder)
        recursively_submit(folder.dataFolders)


def submit_files_in_folder(folder):
    """
    Open all files contained in a folder and submit them the backend by calling the
    CheckAndSubmit command.

    :param folder: The folder in which to submit all files.
    :return:
    """
    global progress_dialog
    folder_data_files = wrapped_forge_call(folder.dataFiles.asArray, progress_dialog)
    for file in folder_data_files:
        if not file.fileExtension == "f3d":
            continue
        progress_dialog.maximumValue = len(folder_data_files)
        progress_dialog.message = (
            f'Folder "{folder.name}" contains {len(folder_data_files)} files.\n\n'
            f"Processing..."
        )
        app = adsk.core.Application.get()
        document = app.documents.open(file)
        design = adsk.fusion.Design.cast(app.activeProduct)
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
            document.close(False)
        else:
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
        "been made/a new project has been setup or imported.\nEach file in the project will be opened. Eligible parts "
        "will be submitted to the server, non-eligible parts will be added to an error report.\n\n"
        "Do you wish to continue?",
        "Proceed to Crawl",
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

        load_project_taxonomy_to_config()

        submit_files_in_folder(root_folder)
        recursively_submit(root_folder.dataFolders)

        progress_dialog.hide()
        update_taxonomy_in_backend()


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
