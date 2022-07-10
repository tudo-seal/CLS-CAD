import json

import adsk.core
import os
import inspect
import copy
from ...lib.cls_python_compat import *
from ...lib import fusion360utils as futil
from ... import config
import urllib.request

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cns'
CMD_NAME = 'Súbmit'
CMD_Description = 'Check and Submit part to repository.'
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'CRAWL'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resources
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', '')

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                           '..')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME,
                                                        CMD_Description,
                                                        ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)

    # UI Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    #Clean entire Panel
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    for i in range(panel.controls.count):
        if panel.controls.item(0):
            panel.controls.item(0).deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


type_text_box_input = adsk.core.TextBoxCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')
    global type_text_box_input

    # Handlers
    futil.add_handler(args.command.execute,
                      command_execute,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged,
                      command_input_changed,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview,
                      command_preview,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.destroy,
                      command_destroy,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs,
                      command_validate,
                      local_handlers=local_handlers)

    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(800, 800)
    args.command.setDialogInitialSize(800, 800)

    # UI
    type_text_box_input = inputs.addTextBoxCommandInput('typeTextBox', 'Issues',
                                                        '', 1, True)

    type_text_box_input.numRows = 12


def winapi_path(dos_path, encoding=None):
    if (not isinstance(dos_path, str) and encoding is not None):
        dos_path = dos_path.decode(encoding)
    path = os.path.abspath(dos_path)
    if path.startswith(u"\\\\"):
        return u"\\\\?\\UNC\\" + path[2:]
    return u"\\\\?\\" + path


def command_execute_preview(args: adsk.core.CommandEventHandler):
    return


def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs

    # Get Inputs
    nesting_input: adsk.core.BoolValueCommandInput = inputs.itemById('nesting')

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    provides_attributes = json.loads(
        getattr(
            design.rootComponent.attributes.itemByName("CLS-PART",
                                                       "ProvidesAttributes"),
            "value", "[]"))
    provides_parts = json.loads(
        getattr(
            design.rootComponent.attributes.itemByName("CLS-PART",
                                                       "ProvidesParts"),
            "value", "[]"))

    #Demo of data interchange to backen
    jo_infos = []
    for joint_typing in design.findAttributes("CLS-INFO", "UUID"):
        jo = joint_typing.parent
        jo_uuid = jo.attributes.itemByName("CLS-INFO", "UUID").value
        jo_req_formats = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresFormats").value)
        jo_req_parts = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresParts").value)
        jo_req_attributes = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "RequiresAttributes").value)
        jo_prov_formats = json.loads(
            jo.attributes.itemByName("CLS-JOINT", "ProvidesFormats").value)
        jo_connect_type = jo.attributes.itemByName(
            "CLS-JOINT", "JointConnectType").value if jo.attributes.itemByName(
                "CLS-JOINT", "JointConnectType") else "Rigid"
        jo_infos.append(
            (jo_uuid, [s + "_formats" for s in jo_req_formats] +
             [s + "_parts" for s in jo_req_parts] +
             [s + "_attributes" for s in jo_req_attributes],
             [s + "_attributes" for s in provides_attributes] +
             [s + "_parts" for s in provides_parts] +
             [s + "_formats" for s in jo_prov_formats], jo_connect_type))
    configurations = []
    part_dict = {"partConfigs": []}
    for info in jo_infos:
        req_joints = [x for x in jo_infos if x != info]
        part_dict["partConfigs"].append({
            "jointOrderInfo": [{
                "uuid": x[0],
                "motion": x[3]
            } for x in req_joints],
            "provides": {
                "uuid": info[0],
                "motion": info[3]
            }
        })
        arrow = Type.intersect(info[2])
        for req_joint in req_joints:
            arrow = Arrow(Type.intersect(req_joint[1]), arrow)
        configurations.append(
            Arrow("_".join([x[0] for x in req_joints + [info]]), arrow))
    part_dict["combinator"] = CLSEncoder().default(
        Type.intersect(configurations))
    part_dict["meta"] = {}
    part_dict["meta"]["partName"] = app.activeDocument.name
    # this might be wrong and return the browsed ID
    part_dict["meta"][
        "forgeProjectId"] = app.activeDocument.dataFile.parentProject.id
    part_dict["meta"][
        "forgeFolderId"] = app.activeDocument.dataFile.parentFolder.id
    part_dict["meta"]["forgeDocumentId"] = app.activeDocument.dataFile.id

    with open(
            winapi_path(
                os.path.join(
                    ROOT_FOLDER, "_".join([
                        app.data.activeProject.id, app.data.activeFolder.id,
                        app.activeDocument.dataFile.id
                    ]).replace(":", "-") + ".json")), "w+") as f:
        json.dump(
            part_dict,
            f,
            cls=CLSEncoder,
            indent=4,
        )
    req = urllib.request.Request("http://127.0.0.1:8000/submit/part")
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    payload = json.dumps(
        part_dict,
        cls=CLSEncoder,
        indent=4,
    ).encode('utf-8')
    req.add_header('Content-Length', len(payload))
    response = urllib.request.urlopen(req, payload)
    print(response)

    #why not also update the taxonomy in the backend while we are at it?
    suffixed_taxonomy = {}
    print(config.taxonomies)
    for key, value in config.taxonomies.items():
        suffixed_taxonomy.update(TaxonomyConverter.convert(value, key))
    print(suffixed_taxonomy)
    req = urllib.request.Request("http://127.0.0.1:8000/submit/taxonomy")
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    payload = json.dumps(suffixed_taxonomy, indent=4).encode('utf-8')
    req.add_header('Content-Length', len(payload))
    response = urllib.request.urlopen(req, payload)
    print(response)


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_validate(args: adsk.core.ValidateInputsEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    global type_text_box_input
    if design.findAttributes("CLS-JOINT", "ProvidesFormats"):
        type_text_box_input.formatted_text = ""
        args.areInputsValid = True
    else:
        type_text_box_input.formatted_text = "Parts need to at least provide one joint origin that has a  \"Provides\" type."
        args.areInputsValid = False
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    futil.log(
        f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}'
    )


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')
