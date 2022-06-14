# Here you define the commands that will be added to your add-in.
import json
from pathlib import Path
import adsk.core
import os

from ..lib import fusion360utils as futil
from .. import config

# TODO Import the modules corresponding to the commands you created.
# If you want to add an additional command, duplicate one of the existing directories and import it here.
# You need to use aliases (import "entry" as "my_module") assuming you have the default module named "entry".
from .jointTyping import entry as jointTyping
from .partTyping import entry as partTyping
from .typeCrawlingProject import entry as typeCrawlingProject
from .typeCrawlingHub import entry as typeCrawlingHub
from .toggleCustomGraphics import entry as toggleCustomGraphics
from .taxonomyEditing import entry as taxonomyEditing

app = adsk.core.Application.get()
ui = app.userInterface

ROOT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    jointTyping, partTyping, typeCrawlingProject, typeCrawlingHub,
    toggleCustomGraphics, taxonomyEditing
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


def addPanel(parentTab: adsk.core.ToolbarTab, panelId: str,
             panelName: str) -> adsk.core.ToolbarPanel:
    newPanel = parentTab.toolbarPanels.itemById(panelId)

    if newPanel is None:
        newPanel = parentTab.toolbarPanels.add(panelId, panelName)

    return newPanel


local_handlers = []


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    mainTab = addTab()
    if not mainTab.isActive:
        mainTab.activate

    pathPartTaxonomy = Path(os.path.join(ROOT_FOLDER, "parts.taxonomy"))
    pathFormatTaxonomy = Path(os.path.join(ROOT_FOLDER, "formats.taxonomy"))
    pathAttributeTaxonomy = Path(
        os.path.join(ROOT_FOLDER, "attributes.taxonomy"))

    if pathPartTaxonomy.is_file():
        with open(pathPartTaxonomy) as json_file:
            config.taxonomies["parts"] = json.load(json_file)
    if pathFormatTaxonomy.is_file():
        with open(pathFormatTaxonomy) as json_file:
            config.taxonomies["formats"] = json.load(json_file)
    if pathAttributeTaxonomy.is_file():
        with open(pathAttributeTaxonomy) as json_file:
            config.taxonomies["attributes"] = json.load(json_file)

    futil.add_handler(app.documentOpened,
                      application_documentOpened,
                      local_handlers=local_handlers)
    addPanel(mainTab, "TYPES", "Typing Tools")
    addPanel(mainTab, "CRAWL", "Setup Tools")
    addPanel(mainTab, "TAXONOMY", "Taxonomy")
    addPanel(mainTab, "VIZ", "Visualisation")
    for command in commands:
        command.start()


def application_documentOpened(args: adsk.core.DocumentEventArgs):
    # Restore custom graphics
    config.customGraphicsDisplaying = False
    cmd = ui.commandDefinitions.itemById(
        f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_toggle_display')
    cmd.execute()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()