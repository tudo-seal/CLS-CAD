# Here you define the commands that will be added to your add-in.
import json
import adsk.core
import os

from ..lib import fusion360utils as futil
from .. import config

# TODO Import the modules corresponding to the commands you created.
# If you want to add an additional command, duplicate one of the existing directories and import it here.
# You need to use aliases (import "entry" as "my_module") assuming you have the default module named "entry".
from .jointTyping import entry as jointTyping
from .typeCrawlingProject import entry as typeCrawlingProject
from .typeCrawlingHub import entry as typeCrawlingHub
from .toggleCustomGraphics import entry as toggleCustomGraphics

app = adsk.core.Application.get()
ui = app.userInterface

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    jointTyping,
    typeCrawlingProject,
    typeCrawlingHub,
    toggleCustomGraphics
]

def addTab() -> adsk.core.ToolbarTab:
    designWorkspace = ui.workspaces.itemById("FusionSolidEnvironment")

    if designWorkspace:
        allDesignTabs = designWorkspace.toolbarTabs
        if allDesignTabs.count > 0:
            newTab = allDesignTabs.itemById("CLSCAD")

            if newTab is None:
                newTab = allDesignTabs.add("CLSCAD", "CLS-CAD")
            return newTab
    return None

def addPanel(parentTab: adsk.core.ToolbarTab, panelId: str, panelName: str)-> adsk.core.ToolbarPanel:
    newPanel = parentTab.toolbarPanels.itemById(panelId)

    if newPanel is None:
        newPanel = parentTab.toolbarPanels.add(panelId, panelName)

    return newPanel


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    mainTab = addTab()
    if not mainTab.isActive:
        mainTab.activate
    addPanel(mainTab,"TYPES", "Typing Tools")
    addPanel(mainTab,"CRAWL", "Setup Tools")
    addPanel(mainTab,"VIZ", "Visualisation")
    for command in commands:
        command.start()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()