import json
import adsk.core
import os
import inspect
import copy
from ...lib import fusion360utils as futil
from ... import config
import uuid

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_type_joint'
CMD_NAME = 'Typed Joint'
CMD_Description = 'Annotate joint origins with a combinatorial term, allowing combinatory logic to connect parts automatically.'
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'TYPES'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

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

    control2 = panel.controls.addCommand(
        ui.commandDefinitions.itemById("JointOrigin"))
    control2.isPromoted = True

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

# Unsure if this is a better approach than iterating over the actual selection_input
selectedJointOrigins = []
typeTextBoxInput = adsk.core.TextBoxCommandInput.cast(None)
nameTextBoxInput = adsk.core.TextBoxCommandInput.cast(None)
typeSelectionDropDownInput = adsk.core.DropDownCommandInput.cast(None)
kindingSelectionDropDownInput = adsk.core.DropDownCommandInput.cast(None)

kinding = "Light"
typing = "Blocked"


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

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
    futil.add_handler(args.command.preSelectMouseMove,
                      command_preSelectMouseMove,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.preSelect,
                      command_preSelect,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.preSelectEnd,
                      command_preSelectEnd,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview,
                      command_executePreview,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.select,
                      command_select,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.unselect,
                      command_unselect,
                      local_handlers=local_handlers)

    inputs = args.command.commandInputs

    # UI DEF

    selectionInput = inputs.addSelectionInput('selection', 'Select',
                                              'Basic select command input')
    selectionInput.setSelectionLimits(0)
    selectionInput.addSelectionFilter("JointOrigins")

    global typeTextBoxInput, typeSelectionDropDownInput, kindingSelectionDropDownInput, nameTextBoxInput

    typeTextBoxInput = inputs.addTextBoxCommandInput('typeTextBox', 'Part Type',
                                                     '', 2, True)
    nameTextBoxInput = inputs.addTextBoxCommandInput('nameTextBox', 'Set Name',
                                                     '', 2, False)

    groupTypingCmdInput = inputs.addGroupCommandInput('typingGroup', 'Typing')
    groupTypingCmdInput.isExpanded = True
    groupTypingChildren = groupTypingCmdInput.children

    typeSelectionDropDownInput = groupTypingChildren.addDropDownCommandInput(
        'typeSelection', 'Typing',
        adsk.core.DropDownStyles.TextListDropDownStyle)
    typeSelectionDropDownInput.maxVisibleItems = 5
    typeSelectionDropDownInputItems = typeSelectionDropDownInput.listItems
    typeSelectionDropDownInputItems.add('Blocked', True, '')
    typeSelectionDropDownInputItems.add('Palette', False, '')
    typeSelectionDropDownInputItems.add('Shelf', False, '')

    kindingSelectionDropDownInput = groupTypingChildren.addDropDownCommandInput(
        'kindingSelection', 'Kinding',
        adsk.core.DropDownStyles.TextListDropDownStyle)
    kindingSelectionDropDownInput.maxVisibleItems = 5
    kindingSelectionDropDownInputItems = kindingSelectionDropDownInput.listItems
    kindingSelectionDropDownInputItems.add('Light', True, '')
    kindingSelectionDropDownInputItems.add('Medium', False, '')
    kindingSelectionDropDownInputItems.add('Heavy', False, '')

    # Selecting types will probably have to be done by means of a palette, since we need some big filtering


def command_executePreview(args: adsk.core.CommandEventHandler):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design:
        cggroup = design.rootComponent.customGraphicsGroups.add()
        pass


def command_select(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedJointOrigin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selectedJointOrigin:
        try:
            typeTextBoxInput.text = selectedJointOrigin.attributes.itemByName(
                "CLS", "JointTyping").value
        except:
            pass
        selectedJointOrigins.append(selectedJointOrigin)


def command_unselect(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedJointOrigin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selectedJointOrigin:
        selectedJointOrigins.append(selectedJointOrigin)
        selectedJointOrigins = [
            x for x in selectedJointOrigins if x.id != selectedJointOrigin.id
        ]


def command_preSelectMouseMove(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedJointOrigin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selectedJointOrigin:
        cggroup = design.rootComponent.customGraphicsGroups.add()
        pass


def command_preSelect(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedJointOrigin = adsk.fusion.JointOrigin.cast(args.selection.entity)
    if design and selectedJointOrigin:
        pass


def command_preSelectEnd(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity)
    if design and selectedEdge:
        for group in design.rootComponent.customGraphicsGroups:
            if group.id == str("the_relevant_group"):
                group.deleteMe()
                break


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if args.input.id == 'typeSelection':
        global typing
        typing = typeSelectionDropDownInput.selectedItem.name
    if args.input.id == 'kindingSelection':
        global kinding
        kinding = kindingSelectionDropDownInput.selectedItem.name


# EXECUTE
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs

    # Get inputs
    selection_input: adsk.core.SelectionCommandInput = inputs.itemById(
        'selection')

    # All this obv. still has to check for if there already is a custom graphics object for that JointOrigin
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    graphics = design.rootComponent.customGraphicsGroups.add()

    billBoard = adsk.fusion.CustomGraphicsBillBoard.create(
        adsk.core.Point3D.create(0, 0, 0))
    billBoard.billBoardStyle = adsk.fusion.CustomGraphicsBillBoardStyles.ScreenBillBoardStyle

    global typing, kinding, selectedJointOrigins, nameTextBoxInput

    # TODO Query for all already set up joint origins and read custom graphics to them on launch
    for jointTyping in design.findAttributes("CLS", "JointTyping"):
        jointTyping.parent
        print("Query Result: " + jointTyping.value)

    selections = []
    for jo in selectedJointOrigins:

        # Add typing information as string (this is kinda okay, because we'll send it via JSON to the backend anyway)
        jo.attributes.add("CLS", "JointTyping", typing)

        # The first time a joint is typed, assign a UUID and change its name
        if not jo.attributes.itemByName("CLS", "UUID"):
            print("Added UUID to %s" % jo.name)
            jo.attributes.add("CLS", "UUID", str(uuid.uuid4()))
            jo.name = 'Typed Joint'

        jo_uuid = jo.attributes.itemByName("CLS", "UUID").value

        coord_array = [
            jo.geometry.origin.x, jo.geometry.origin.y, jo.geometry.origin.z
        ]
        coords = adsk.fusion.CustomGraphicsCoordinates.create(coord_array)
        points = graphics.addPointSet(
            coords, [0], adsk.fusion.CustomGraphicsPointTypes.
            UserDefinedCustomGraphicsPointType, ICON_FOLDER + '/lambda.png')
        if jo_uuid in config.customTextDict:
            config.customTextDict[
                jo_uuid].formattedText = "Type: %s\n Kinding: %s" % (typing,
                                                                     kinding)
        else:
            tmatrix = adsk.core.Matrix3D.create()
            tmatrix.setWithCoordinateSystem(jo.geometry.origin,
                                            jo.geometry.secondaryAxisVector,
                                            jo.geometry.thirdAxisVector,
                                            jo.geometry.primaryAxisVector)
            offset = jo.geometry.primaryAxisVector.copy()
            offset.normalize()
            offset.scaleBy(0.05)
            offset.add(tmatrix.translation)
            tmatrix.translation = offset
            customText = graphics.addText(
                "Type: %s\n Kinding: %s" % (typing, kinding), 'Arial', 0.2,
                tmatrix)
            config.customTextDict[jo_uuid] = customText

    design.selectionSets.add(selectedJointOrigins, nameTextBoxInput.text)

    selectedJointOrigins = []
    # Should probably be a toggle under visualisation section
    #graphicsText.billBoarding = billBoard


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')
