import json
import adsk.core
import os
import inspect
import copy
from ...lib import fusion360utils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_type_joint'
CMD_NAME = 'Typed Joint'
CMD_Description = 'Annotate joint origins with a combinatorial term, allowing combinatory logic to connect parts automatically.'
IS_PROMOTED = True

# Using "global" variables by referencing values from /config.py
PALETTE_ID = config.sample_palette_id

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'TYPES'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

# Executed when add-in is run.
def start():
    # Command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Register
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    control2 = panel.controls.addCommand(ui.commandDefinitions.itemById("JointOrigin"))
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

selectedEdges = []


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # Handlers
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

    futil.add_handler(args.command.preSelectMouseMove, command_preSelectMouseMove, local_handlers=local_handlers)
    futil.add_handler(args.command.preSelect, command_preSelect, local_handlers=local_handlers)
    futil.add_handler(args.command.preSelectEnd, command_preSelectEnd, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_executePreview, local_handlers=local_handlers)
    futil.add_handler(args.command.select, command_select, local_handlers=local_handlers)

    inputs = args.command.commandInputs

    # UI DEF

    selectionInput = inputs.addSelectionInput('selection', 'Select', 'Basic select command input')
    selectionInput.setSelectionLimits(0)
    selectionInput.addSelectionFilter("JointOrigins")

    # Selecting types will probably have to be done by means of a palette, since we need some big filtering

def command_executePreview(args: adsk.core.CommandEventHandler):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design:
        cggroup = design.rootComponent.customGraphicsGroups.add()
        for i in range(0, len(selectedEdges)):
            edge = adsk.fusion.BRepEdge.cast(selectedEdges[i])
            transform = adsk.core.Matrix3D.create()
            transform.translation = edge.pointOnEdge.asVector()
            cgtext = cggroup.addText(str(i+1), 'Arial Black', 1, transform)
            cgtext.color = adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(0,255,0,255))

def command_select(args: adsk.core.SelectionEventArgs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedJoint = adsk.fusion.JointOrigin.cast(args.selection.entity) 
    joint = selectedJoint
    

def command_preSelectMouseMove(args: adsk.core.SelectionEventArgs):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
    selectedFace = adsk.fusion.BRepEdge.cast(args.selection.entity) 
    if design and selectedEdge:
        group = design.rootComponent.customGraphicsGroups.add()
        group.id = str(selectedEdge.tempId)
        cgcurve = group.addCurve(selectedEdge.geometry)
        cgcurve.color = adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(255,0,0,255))
        cgcurve.weight = 10  

def command_preSelect(args: adsk.core.SelectionEventArgs):
    selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity)
    if selectedEdge:
        args.additionalEntities = selectedEdge.tangentiallyConnectedEdges 

def command_preSelectEnd(args: adsk.core.SelectionEventArgs):        
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
    if design and selectedEdge:
        for group in design.rootComponent.customGraphicsGroups:
            if group.id == str(selectedEdge.tempId):
                group.deleteMe()
                break



# EXECUTE
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs


    # Get inputs
    selection_input: adsk.core.SelectionCommandInput = inputs.itemById('selection')


    # All this obv. still has to check for if there already is a custom graphics object for that JointOrigin
    design = adsk.fusion.Design.cast(app.activeProduct)
    graphics = design.rootComponent.customGraphicsGroups.add()

    billBoard = adsk.fusion.CustomGraphicsBillBoard.create(adsk.core.Point3D.create(0,0,0))
    billBoard.billBoardStyle = adsk.fusion.CustomGraphicsBillBoardStyles.ScreenBillBoardStyle

    jo = adsk.fusion.JointOrigin.cast(selection_input.selection(0).entity)
    
    # TODO Query for all already set up joint origins and read custom graphics to them on launch
    for jointTyping in design.findAttributes("CLS","JointTyping"):
            jointTyping.parent
            print("Query Result: " + jointTyping.value)
    jo.attributes.add("CLS","JointTyping", "Any type")
    jo.attributes.add("CLS","UID", "ReallylongUID")
    

    jo.name = 'Typed Joint'
    coord_array = [jo.geometry.origin.x,jo.geometry.origin.y,jo.geometry.origin.z]
    coords = adsk.fusion.CustomGraphicsCoordinates.create(coord_array)
    points = graphics.addPointSet(coords, [0], 
                   adsk.fusion.CustomGraphicsPointTypes.UserDefinedCustomGraphicsPointType,
                   ICON_FOLDER + '/lambda.png')

    tmatrix = adsk.core.Matrix3D.create()
    tmatrix.setWithCoordinateSystem(jo.geometry.origin,jo.geometry.secondaryAxisVector,jo.geometry.thirdAxisVector,jo.geometry.primaryAxisVector)
    offset = jo.geometry.primaryAxisVector.copy()
    offset.normalize()
    offset.scaleBy(0.05)
    offset.add(tmatrix.translation)
    tmatrix.translation = offset
    graphicsText = graphics.addText("Type: ...\n Kinding: ...", 'Arial', 0.5, tmatrix)
    #Should probably be a toggle under visualisation section
    #graphicsText.billBoarding = billBoard


def command_preview(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    futil.log(f'{CMD_NAME} Command Preview Event')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')
