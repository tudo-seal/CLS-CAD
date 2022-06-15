from datetime import datetime
import json
from time import sleep
import adsk.core
import os
import inspect
import copy
from ...lib import fusion360utils as futil
from ... import config
import uuid
import collections

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_type_part'
CMD_NAME = 'Typed Part'
CMD_Description = 'Annotate Parts with Attribute and Type information.'
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'TYPES'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

PARTTYPES_ID = "partsTaxonomyBrowser_Part"
ATTRIBUTETYPES_ID = "attributesTaxonomyBrowser_Part"

# Specify the full path to the local html. You can also use a web URL
# such as 'https://www.autodesk.com/'
PALETTE_URL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                           "..", 'resources', 'html', "unrolledTaxonomyDisplay",
                           'index.html')

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace('\\', '/')

# Resource location
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', '')

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                           '..')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []
providesParts, providesAttributes = [], []

# Executed when add-in is run.


def start():
    # Command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME,
                                                        CMD_Description,
                                                        ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

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


jointOrigin = adsk.fusion.JointOrigin.cast(None)

#Initializing like this is nice but not necessary I guess
typeTextBoxInput = adsk.core.TextBoxCommandInput.cast(None)
partsTypeSelectionBrowserInput = adsk.core.BrowserCommandInput.cast(None)


def command_created(args: adsk.core.CommandCreatedEventArgs):
    global typeTextBoxInput, partsTypeSelectionBrowserInput, providesParts, providesAttributes

    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # Handlers
    futil.add_handler(args.command.execute,
                      command_execute,
                      local_handlers=local_handlers)
    # futil.add_handler(args.command.inputChanged,
    #                   command_input_changed,
    #                   local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview,
                      command_preview,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.destroy,
                      command_destroy,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.incomingFromHTML,
                      palette_incoming,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.activate,
                      command_activate,
                      local_handlers=local_handlers)

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    providesAttributes = json.loads(
        design.rootComponent.attributes.itemByName(
            "CLS-PART", "ProvidesAttributes").value if design.rootComponent.
        attributes.itemByName("CLS-PART", "ProvidesAttributes") else "")
    providesParts = json.loads(
        design.rootComponent.attributes.itemByName("CLS-PART", "ProvidesParts").
        value if design.rootComponent.attributes.
        itemByName("CLS-PART", "ProvidesParts") else "")

    inputs = args.command.commandInputs
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    # UI DEF

    typeTextBoxInput = inputs.addTextBoxCommandInput('typeTextBox', 'Part Type',
                                                     '', 1, True)
    typeTextBoxInput.numRows = 12

    #groupTypingCmdInput = inputs.addGroupCommandInput('typingGroup', 'Typing')
    #groupTypingCmdInput.isExpanded = True
    #groupTypingChildren = groupTypingCmdInput.children

    partsTypeSelectionBrowserInput = inputs.addBrowserCommandInput(
        id=PARTTYPES_ID,
        name='Select part/part family',
        htmlFileURL=PALETTE_URL,
        minimumHeight=300)
    attributesTypeSelectionBrowserInput = inputs.addBrowserCommandInput(
        id=ATTRIBUTETYPES_ID,
        name='Select attributes/attribute family',
        htmlFileURL=PALETTE_URL,
        minimumHeight=300)


def command_executePreview(args: adsk.core.CommandEventHandler):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    typeTextBoxInput.text = generateTypeText()


def command_activate(args: adsk.core.CommandEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    app.log('In command_activate event handler.')


def generateTypeText():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    typedJOs = []
    guardedTypes = []
    for jointTyping in design.findAttributes("CLS-INFO", "UUID"):
        jo = jointTyping.parent
        reqString = jo.attributes.itemByName("CLS-JOINT",
                                             "RequiresString").value
        provString = jo.attributes.itemByName("CLS-JOINT",
                                              "ProvidesString").value
        joUUID = jo.attributes.itemByName("CLS-INFO", "UUID").value[0:4]
        typedJOs.append((reqString, provString, joUUID))
    print(typedJOs)
    for joInfo in typedJOs:
        if joInfo[1].strip() == "":
            continue
        reqList = [x[0] for x in typedJOs if x != joInfo]
        uuidList = [x[2] for x in typedJOs if x != joInfo]
        guardedTypes.append(
            f'( Constructor(\"Config\",{"×".join(uuidList)}) ) → ' +
            "→".join(reqList) + " → ( " + joInfo[1] +
            f' ∩ ({"∩".join(providesParts)}) ∩ ({"∩".join(providesAttributes)}) )'
        )
    return """<style>
                pre {
                    white-space:pre-wrap;
                    tab-size: 2;
                    display: block;
                    line-height: 100%;
                    font-family: Courier;
                }
                </style><pre>""" + " ∩ \n".join(guardedTypes).replace(
        " ∩ ()", "") + "</pre>"


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f'{CMD_NAME}: Palette incoming event.')
    print("Incoming")
    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.objectType}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)
    global providesParts, providesAttributes
    if message_action == 'selectionNotification':
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            providesParts = message_data['selections']
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            providesAttributes = message_data['selections']
        typeTextBoxInput.formattedText = generateTypeText()
    if message_action == 'updateDataNotification':
        # Update loaded and saved taxonomies

        # The browser IDs should be refactored into constants
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomyID = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomyID = "attributes"
        config.taxonomies[taxonomyID] = message_data
        with open(os.path.join(ROOT_FOLDER, "%s.taxonomy" % taxonomyID),
                  "w+") as f:
            json.dump(message_data, f, ensure_ascii=False, indent=4)

    if message_action == 'readyNotification':
        # ADSK was injected, so now we send the payload
        taxonomyID = None
        taxonomyDataMessage = None
        if html_args.browserCommandInput.id == PARTTYPES_ID:
            taxonomyDataMessage = config.taxonomies["parts"]
            taxonomyID = "parts"
        elif html_args.browserCommandInput.id == ATTRIBUTETYPES_ID:
            taxonomyDataMessage = config.taxonomies["attributes"]
            taxonomyID = "attributes"
        html_args.browserCommandInput.sendInfoToHTML(
            "taxonomyDataMessage", json.dumps(taxonomyDataMessage))
        html_args.browserCommandInput.sendInfoToHTML("taxonomyIDMessage",
                                                     taxonomyID)

    # Return value.
    now = datetime.now()
    currentTime = now.strftime('%H:%M:%S')
    html_args.returnData = f'OK - {currentTime}'


# EXECUTE
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f'{CMD_NAME} Command Execute Event')

    global providesAttributes, providesParts
    inputs = args.command.commandInputs
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    rootComp = design.rootComponent
    rootComp.attributes.add(
        "CLS-PART",
        "ProvidesString",
        f'({"∩".join(providesParts)}) ∩ ({"∩".join(providesAttributes)})',
    )
    rootComp.attributes.add("CLS-PART", "ProvidesAttributes",
                            json.dumps(providesAttributes))
    rootComp.attributes.add("CLS-PART", "ProvidesParts",
                            json.dumps(providesParts))


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    typeTextBoxInput.formattedText = generateTypeText()
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, providesAttributes, providesParts
    providesParts = []
    providesAttributes = []
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')
