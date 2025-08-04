import re
import shutil
import unicodedata
import fileinput
import sys
import shutil
import urllib
import adsk.core

from ...lib import fusion360utils as futil
from ...lib.cls_python_compat import *
from ...lib.general_utils import *
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
from xml.etree import ElementTree
from timeit import default_timer as timer

from ..requestsynthesisoptimizer.entry import synthesize_with_vector
from ..assemblecheapestresult.entry import request_cheapest
app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_run_experiment"
CMD_NAME = "Run Experiment"
CMD_DESCRIPTION = "Run the experiment with the current settings."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "CRAWL"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")


local_handlers = []
experiment_parameters = {
    "iterations": 5,
    "search_space_extrusions": (0, 5),
    "search_space_motors": (0, 7),
    "initial_state": None,
    "initial_n_points": 0,
}
progress_dialog: adsk.core.ProgressDialog = None
export_path = ""

def copy_occs(root):    
    """    
    duplicate all the components
    """    
    def copy_body(allOccs, occs):
        """    
        copy the old occs to new component
        """
        
        bodies = occs.bRepBodies
        transform = adsk.core.Matrix3D.create()
        
        # Create new components from occs
        # This support even when a component has some occses. 

        new_occs = allOccs.addNewComponent(transform)  # this create new occs
        if occs.component.name == 'base_link':
            occs.component.name = 'old_component'
            new_occs.component.name = 'base_link'
        else:
            new_occs.component.name = re.sub('[ :()]', '_', occs.name)
        new_occs = allOccs.item((allOccs.count-1))
        for i in range(bodies.count):
            body = bodies.item(i)
            body.copyToComponent(new_occs)
    
    allOccs = root.occurrences
    oldOccs = []
    coppy_list = [occs for occs in allOccs]
    for occs in coppy_list:
        if occs.bRepBodies.count > 0:
            copy_body(allOccs, occs)
            oldOccs.append(occs)

    for occs in oldOccs:
        occs.component.name = 'old_component'


def export_stl(design, save_dir, root, robot_name):  
    """
    export stl files into "sace_dir/"
    
    
    Parameters
    ----------
    design: adsk.fusion.Design.cast(product)
    save_dir: str
        directory path to save
    components: design.allComponents
    """
          
    # create a single exportManager instance
    exportMgr = design.exportManager
    # get the script location
    try: os.makedirs(save_dir + '/meshes')
    except: pass
    scriptDir = save_dir + '/meshes'  
    rootOccs = root.occurrences
    
    for occ in rootOccs:
        if 'old_component' not in occ.component.name:
            try:
                newName = re.sub('[ :()]', '_', occ.name)
                fileName = scriptDir + "/" + newName
                # create stl exportOptions
                stlExportOptions = exportMgr.createSTLExportOptions(occ, fileName)
                stlExportOptions.sendToPrintUtility = False
                stlExportOptions.isBinaryFormat = True
                # options are .MeshRefinementLow .MeshRefinementMedium .MeshRefinementHigh
                stlExportOptions.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
                exportMgr.execute(stlExportOptions)
            except:
                print('Component ' + occ.name + 'has something wrong.')


class Joint:
    def __init__(self, name, xyz, axis, parent, child, joint_type, upper_limit, lower_limit):
        """
        Attributes
        ----------
        name: str
            name of the joint
        type: str
            type of the joint(ex: rev)
        xyz: [x, y, z]
            coordinate of the joint
        axis: [x, y, z]
            coordinate of axis of the joint
        parent: str
            parent link
        child: str
            child link
        joint_xml: str
            generated xml describing about the joint
        tran_xml: str
            generated xml describing about the transmission
        """
        self.name = name
        self.type = joint_type
        self.xyz = xyz
        self.parent = parent
        self.child = child
        self.joint_xml = None
        self.tran_xml = None
        self.axis = axis  # for 'revolute' and 'continuous'
        self.upper_limit = upper_limit  # for 'revolute' and 'prismatic'
        self.lower_limit = lower_limit  # for 'revolute' and 'prismatic'
        
    def make_joint_xml(self):
        """
        Generate the joint_xml and hold it by self.joint_xml
        """
        joint = Element('joint')
        joint.attrib = {'name':self.name, 'type':self.type}
        
        origin = SubElement(joint, 'origin')
        origin.attrib = {'xyz':' '.join([str(_) for _ in self.xyz]), 'rpy':'0 0 0'}
        parent = SubElement(joint, 'parent')
        parent.attrib = {'link':self.parent}
        child = SubElement(joint, 'child')
        child.attrib = {'link':self.child}
        if self.type == 'revolute' or self.type == 'continuous' or self.type == 'prismatic':        
            axis = SubElement(joint, 'axis')
            axis.attrib = {'xyz':' '.join([str(_) for _ in self.axis])}
        if self.type == 'revolute' or self.type == 'prismatic':
            limit = SubElement(joint, 'limit')
            limit.attrib = {'upper': str(self.upper_limit), 'lower': str(self.lower_limit),
                            'effort': '100', 'velocity': '100'}
            
        self.joint_xml = "\n".join(prettify(joint).split("\n")[1:])

    def make_transmission_xml(self):
        """
        Generate the tran_xml and hold it by self.tran_xml
        
        
        Notes
        -----------
        mechanicalTransmission: 1
        type: transmission interface/SimpleTransmission
        hardwareInterface: PositionJointInterface        
        """        
        
        tran = Element('transmission')
        tran.attrib = {'name':self.name + '_tran'}
        
        joint_type = SubElement(tran, 'type')
        joint_type.text = 'transmission_interface/SimpleTransmission'
        
        joint = SubElement(tran, 'joint')
        joint.attrib = {'name':self.name}
        hardwareInterface_joint = SubElement(joint, 'hardwareInterface')
        hardwareInterface_joint.text = 'hardware_interface/EffortJointInterface'
        
        actuator = SubElement(tran, 'actuator')
        actuator.attrib = {'name':self.name + '_actr'}
        hardwareInterface_actr = SubElement(actuator, 'hardwareInterface')
        hardwareInterface_actr.text = 'hardware_interface/EffortJointInterface'
        mechanicalReduction = SubElement(actuator, 'mechanicalReduction')
        mechanicalReduction.text = '1'
        
        self.tran_xml = "\n".join(prettify(tran).split("\n")[1:])


def make_joints_dict(root, msg):
    """
    joints_dict holds parent, axis and xyz information of the joints
    
    
    Parameters
    ----------
    root: adsk.fusion.Design.cast(product)
        Root component
    msg: str
        Tell the status
        
    Returns
    ----------
    joints_dict: 
        {name: {type, axis, upper_limit, lower_limit, parent, child, xyz}}
    msg: str
        Tell the status
    """

    joint_type_list = [
    'fixed', 'revolute', 'prismatic', 'Cylinderical',
    'PinSlot', 'Planner', 'Ball']  # these are the names in urdf

    joints_dict = {}
    
    for joint in root.joints:
        joint_dict = {}
        joint_type = joint_type_list[joint.jointMotion.jointType]
        joint_dict['type'] = joint_type
        
        # switch by the type of the joint
        joint_dict['axis'] = [0, 0, 0]
        joint_dict['upper_limit'] = 0.0
        joint_dict['lower_limit'] = 0.0
        
        # support  "Revolute", "Rigid" and "Slider"
        if joint_type == 'revolute':
            joint_dict['axis'] = [round(i, 6) for i in \
                joint.jointMotion.rotationAxisVector.asArray()] ## In Fusion, exported axis is normalized.
            max_enabled = joint.jointMotion.rotationLimits.isMaximumValueEnabled
            min_enabled = joint.jointMotion.rotationLimits.isMinimumValueEnabled            
            if max_enabled and min_enabled:  
                joint_dict['upper_limit'] = round(joint.jointMotion.rotationLimits.maximumValue, 6)
                joint_dict['lower_limit'] = round(joint.jointMotion.rotationLimits.minimumValue, 6)
            elif max_enabled and not min_enabled:
                msg = joint.name + 'is not set its lower limit. Please set it and try again.'
                break
            elif not max_enabled and min_enabled:
                msg = joint.name + 'is not set its upper limit. Please set it and try again.'
                break
            else:  # if there is no angle limit
                joint_dict['type'] = 'continuous'
                
        elif joint_type == 'prismatic':
            joint_dict['axis'] = [round(i, 6) for i in \
                joint.jointMotion.slideDirectionVector.asArray()]  # Also normalized
            max_enabled = joint.jointMotion.slideLimits.isMaximumValueEnabled
            min_enabled = joint.jointMotion.slideLimits.isMinimumValueEnabled            
            if max_enabled and min_enabled:  
                joint_dict['upper_limit'] = round(joint.jointMotion.slideLimits.maximumValue/100, 6)
                joint_dict['lower_limit'] = round(joint.jointMotion.slideLimits.minimumValue/100, 6)
            elif max_enabled and not min_enabled:
                msg = joint.name + 'is not set its lower limit. Please set it and try again.'
                break
            elif not max_enabled and min_enabled:
                msg = joint.name + 'is not set its upper limit. Please set it and try again.'
                break
        elif joint_type == 'fixed':
            pass

        # occurenceTwo is none for 'link_0:1+base v1:1'
        if joint.occurrenceTwo is None or joint.occurrenceTwo.component.name == 'base_link': 
            joint_dict['parent'] = 'base_link'
            child_fullPathName = joint.occurrenceOne.fullPathName
            child_link_name = child_fullPathName[0:child_fullPathName.find('+')]
            # child_link_name = child_link_name[0:child_link_name.find(':')]
            joint_dict['child'] = re.sub('[ :()]', '_', child_link_name)
            
        else:
            parent_fullPathName = joint.occurrenceOne.fullPathName
            parent_link_name = parent_fullPathName[0:parent_fullPathName.find('+')]
            # parent_link_name = parent_link_name[0:parent_link_name.find(':')]
            joint_dict['parent'] = re.sub('[ :()]', '_', parent_link_name)
            # occurenceOne contains the relevant name for the joint
            child_fullPathName = joint.occurrenceTwo.fullPathName
            child_link_name = child_fullPathName[0:child_fullPathName.find('+')]
            # child_link_name = child_link_name[0:child_link_name.find(':')]
            joint_dict['child'] = re.sub('[ :()]', '_', child_link_name)

        
        
        #There seem to be a problem with geometryOrOriginTwo. To calcualte the correct origin of the generated stl files following approach was used.
        #https://forums.autodesk.com/t5/fusion-360-api-and-scripts/difference-of-geometryororiginone-and-geometryororiginonetwo/m-p/9837767
        #Thanks to Masaki Yamamoto!
        
        # Coordinate transformation by matrix
        # M: 4x4 transformation matrix
        # a: 3D vector
        def trans(M, a):
            ex = [M[0],M[4],M[8]]
            ey = [M[1],M[5],M[9]]
            ez = [M[2],M[6],M[10]]
            oo = [M[3],M[7],M[11]]
            b = [0, 0, 0]
            for i in range(3):
                b[i] = a[0]*ex[i]+a[1]*ey[i]+a[2]*ez[i]+oo[i]
            return(b)


        # Returns True if two arrays are element-wise equal within a tolerance
        def allclose(v1, v2, tol=1e-6):
            return( max([abs(a-b) for a,b in zip(v1, v2)]) < tol )

        try:
            if hasattr(joint.geometryOrOriginOne, "origin"): # Relative Joint pos
                xyz_from_one_to_joint = joint.geometryOrOriginOne.origin.asArray() 
            else:
                xyz_from_one_to_joint = joint.geometryOrOriginOne.geometry.origin.asArray()
            if hasattr(joint.geometryOrOriginTwo, "origin"): # Relative Joint pos
                xyz_from_two_to_joint = joint.geometryOrOriginTwo.origin.asArray()
            else:
                xyz_from_two_to_joint = joint.geometryOrOriginTwo.geometry.origin.asArray()
             
            xyz_of_one = joint.occurrenceOne.transform.translation.asArray() # Link origin
            xyz_of_two = joint.occurrenceTwo.transform.translation.asArray() # Link origin
            M_two = joint.occurrenceTwo.transform.asArray() # Matrix as a 16 element array.

        # Compose joint position
            case1 = allclose(xyz_from_two_to_joint, xyz_from_one_to_joint)
            case2 = allclose(xyz_from_two_to_joint, xyz_of_one)
            if case1 or case2:
                xyz_of_joint = xyz_from_two_to_joint
            else:
                xyz_of_joint = trans(M_two, xyz_from_two_to_joint)


            joint_dict['xyz'] = [round(i / 100.0, 6) for i in xyz_of_joint]  # converted to meter
        
        except:
            try:
                if type(joint.geometryOrOriginTwo)==adsk.fusion.JointOrigin:
                    data = joint.geometryOrOriginTwo.geometry.origin.asArray()
                else:
                    data = joint.geometryOrOriginTwo.origin.asArray()
                joint_dict['xyz'] = [round(i / 100.0, 6) for i in data]  # converted to meter
            except:
                msg = joint.name + " doesn't have joint origin. Please set it and run again."
                break
        
        
        joints_dict[joint.name] = joint_dict
    return joints_dict, msg

class Link:

    def __init__(self, name, xyz, center_of_mass, repo, mass, inertia_tensor):
        """
        Parameters
        ----------
        name: str
            name of the link
        xyz: [x, y, z]
            coordinate for the visual and collision
        center_of_mass: [x, y, z]
            coordinate for the center of mass
        link_xml: str
            generated xml describing about the link
        repo: str
            the name of the repository to save the xml file
        mass: float
            mass of the link
        inertia_tensor: [ixx, iyy, izz, ixy, iyz, ixz]
            tensor of the inertia
        """
        self.name = name
        # xyz for visual
        self.xyz = [-_ for _ in xyz]  # reverse the sign of xyz
        # xyz for center of mass
        self.center_of_mass = center_of_mass
        self.link_xml = None
        self.repo = repo
        self.mass = mass
        self.inertia_tensor = inertia_tensor

    def make_link_xml(self):
        """
        Generate the link_xml and hold it by self.link_xml
        """
        
        link = Element('link')
        link.attrib = {'name':self.name}
        
        #inertial
        inertial = SubElement(link, 'inertial')
        origin_i = SubElement(inertial, 'origin')
        origin_i.attrib = {'xyz':' '.join([str(_) for _ in self.center_of_mass]), 'rpy':'0 0 0'}       
        mass = SubElement(inertial, 'mass')
        mass.attrib = {'value':str(self.mass)}
        inertia = SubElement(inertial, 'inertia')
        inertia.attrib = \
            {'ixx':str(self.inertia_tensor[0]), 'iyy':str(self.inertia_tensor[1]),\
            'izz':str(self.inertia_tensor[2]), 'ixy':str(self.inertia_tensor[3]),\
            'iyz':str(self.inertia_tensor[4]), 'ixz':str(self.inertia_tensor[5])}        
        
        # visual
        visual = SubElement(link, 'visual')
        origin_v = SubElement(visual, 'origin')
        origin_v.attrib = {'xyz':' '.join([str(_) for _ in self.xyz]), 'rpy':'0 0 0'}
        geometry_v = SubElement(visual, 'geometry')
        mesh_v = SubElement(geometry_v, 'mesh')
        mesh_v.attrib = {'filename':'package://' + self.repo + self.name + '.stl','scale':'0.001 0.001 0.001'}
        material = SubElement(visual, 'material')
        material.attrib = {'name':'silver'}
        
        # collision
        collision = SubElement(link, 'collision')
        origin_c = SubElement(collision, 'origin')
        origin_c.attrib = {'xyz':' '.join([str(_) for _ in self.xyz]), 'rpy':'0 0 0'}
        geometry_c = SubElement(collision, 'geometry')
        mesh_c = SubElement(geometry_c, 'mesh')
        mesh_c.attrib = {'filename':'package://' + self.repo + self.name + '.stl','scale':'0.001 0.001 0.001'}

        # print("\n".join(utils.prettify(link).split("\n")[1:]))
        self.link_xml = "\n".join(prettify(link).split("\n")[1:])

def prettify(elem):
    """
    Return a pretty-printed XML string for the Element.
    Parameters
    ----------
    elem : xml.etree.ElementTree.Element
    
    
    Returns
    ----------
    pretified xml : str
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def origin2center_of_mass(inertia, center_of_mass, mass):
    """
    convert the moment of the inertia about the world coordinate into 
    that about center of mass coordinate


    Parameters
    ----------
    moment of inertia about the world coordinate:  [xx, yy, zz, xy, yz, xz]
    center_of_mass: [x, y, z]
    
    
    Returns
    ----------
    moment of inertia about center of mass : [xx, yy, zz, xy, yz, xz]
    """
    x = center_of_mass[0]
    y = center_of_mass[1]
    z = center_of_mass[2]
    translation_matrix = [y**2+z**2, x**2+z**2, x**2+y**2,
                         -x*y, -y*z, -x*z]
    return [ round(i - mass*t, 6) for i, t in zip(inertia, translation_matrix)]

def make_inertial_dict(root, msg):
    """      
    Parameters
    ----------
    root: adsk.fusion.Design.cast(product)
        Root component
    msg: str
        Tell the status
        
    Returns
    ----------
    inertial_dict: {name:{mass, inertia, center_of_mass}}
    
    msg: str
        Tell the status
    """
    # Get component properties.      
    allOccs = root.occurrences
    inertial_dict = {}
    
    for occs in allOccs:
        # Skip the root component.
        occs_dict = {}
        prop = occs.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
        
        occs_dict['name'] = re.sub('[ :()]', '_', occs.name)

        mass = prop.mass  # kg
        occs_dict['mass'] = mass
        center_of_mass = [_/100.0 for _ in prop.centerOfMass.asArray()] ## cm to m
        occs_dict['center_of_mass'] = center_of_mass

        # https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-ce341ee6-4490-11e5-b25b-f8b156d7cd97
        (_, xx, yy, zz, xy, yz, xz) = prop.getXYZMomentsOfInertia()
        moment_inertia_world = [_ / 10000.0 for _ in [xx, yy, zz, xy, yz, xz] ] ## kg / cm^2 -> kg/m^2
        occs_dict['inertia'] = origin2center_of_mass(moment_inertia_world, center_of_mass, mass)
        
        if occs.component.name == 'base_link':
            inertial_dict['base_link'] = occs_dict
        else:
            inertial_dict[re.sub('[ :()]', '_', occs.name)] = occs_dict

    return inertial_dict, msg



# extension code starts here
def start():
    """
    Creates the promoted "Export Project as URDF" command in the CLS-CAD tab.

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
    global experiment_parameters
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )

def do_events_for_duration(duration: float):
    """
    Allows the main Fusion 360 thread to process ui events for the specified duration.
    Prevents the interface lagging during the assembly process.

    :param duration: float: The duration for which to process ui events.
    :return:
    """
    start_time = timer()
    while timer() - start_time < duration:
        adsk.doEvents()

def command_execute(args: adsk.core.CommandEventArgs):
    """
    Executes immediately when user clicks the button in CLS-CAD tab as there are no
    command inputs. Prompts the user to confirm beginning the lengthy crawling process.
    Fetches the activeDocuments (priority, else active side browser position) projects
    root folder. Recursively traverses this initial set of folders.

    :param args: adsk.core.CommandEventArgs:
    :return:
    """
    global experiment_parameters
    futil.log(f"{CMD_NAME} Command Execute Event")

    load_project_taxonomy_to_config()
    app = adsk.core.Application.get()
    
    success_msg = 'Start Experiment? This might take a while'
    title = 'Run Full Experiment'
    msg = success_msg
    ui.messageBox(
        msg,
        title,
        adsk.core.MessageBoxButtonTypes.OKCancelButtonType
    )
    
    folder_dlg = ui.createFolderDialog()
    folder_dlg.title = "Fusion Choose Folder Dialog"

    dlg_result = folder_dlg.showDialog()
    if dlg_result == adsk.core.DialogResults.DialogOK:
        global export_path
        export_path = folder_dlg.folder
        if not os.path.exists(folder_dlg.folder):
            os.makedirs(folder_dlg.folder)
    else:
        return
    
    args.command.setDialogMinimumSize(1200, 800)
    args.command.setDialogInitialSize(1200, 800)

    (experiment_id, cancelled) = ui.inputBox(
            "Please enter experiment id",
            "Run New Experiment",
            "",
    )

    if cancelled:
        return

    experiment_parameters["experiment_id"] = experiment_id

    (iterations, cancelled) = ui.inputBox(
            "Please enter number of iterations",
            "Run New Experiment",
            str(experiment_parameters["iterations"]),
    )

    if cancelled:
        return

    experiment_parameters["iterations"] = int(iterations)

    (search_space_extrusions, cancelled) = ui.inputBox(
            "Please enter minimum and max count for extrusions (comma separated, e.g. 0,5)",
            "Run New Experiment",
            str(experiment_parameters["search_space_extrusions"]),
    )

    if cancelled:
        return

    experiment_parameters["search_space_extrusions"] = tuple(map(int, search_space_extrusions.split(",")))

    (search_space_motors, cancelled) = ui.inputBox(
            "Please enter minimum and max count for motors (comma separated, e.g. 0,7)",
            "Run New Experiment",
            str(experiment_parameters["search_space_motors"]),
    )

    if cancelled:
        return

    experiment_parameters["search_space_motors"] = tuple(map(int, search_space_motors.split(",")))

    (initial_state, cancelled) = ui.inputBox(
            "Please enter initial state",
            "Run New Experiment",
            str(experiment_parameters["initial_state"]),
    )

    if cancelled:
        return

    experiment_parameters["initial_state"] = int(initial_state)

    (initial_n_points, cancelled) = ui.inputBox(
            "Please enter number of initial points to sample in the search space before optimizing",
            "Run New Experiment",
            str(experiment_parameters["initial_n_points"]),
    )

    if cancelled:
        return

    experiment_parameters["initial_n_points"] = int(initial_n_points)
    futil.log(f"Experiment parameters: {experiment_parameters}")

    # call backend

    payload = json.dumps({
        "iterations": experiment_parameters["iterations"],
        "init_n_points": experiment_parameters["initial_n_points"],
        "initial_state": experiment_parameters["initial_state"],
        "experiment_id": experiment_parameters["experiment_id"],
        "search_space_extrusions": experiment_parameters["search_space_extrusions"],
        "search_space_motors": experiment_parameters["search_space_motors"],
    }).encode('utf-8')
    # POST the payload to the backend server

    req = urllib.request.Request("http://127.0.0.1:8000/bo/initialize")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Content-Length", len(payload))
    response = urllib.request.urlopen(req, payload)
    
    raw_response = response.read().decode()
    print(raw_response)

    global progress_dialog
    progress_dialog = ui.createProgressDialog()
    progress_dialog.show("Experiment in Progress", "Running Experiment...", 0, 1)
    progress_dialog.maximumValue = experiment_parameters["iterations"]
    # beginning of loop
    for i in range(experiment_parameters["iterations"]):
        progress_dialog.message = f"Iteration {i+1} of {experiment_parameters['iterations']}"
        # check if done (iterations)
        # ask bo for next vector
        print("Send request")
        cur_vec_req = urllib.request.Request(f"http://127.0.0.1:8000/bo/{experiment_id}/optimal-vector")
        cur_vec_req.add_header("Content-Type", "application/json; charset=utf-8")
        cur_vec_response = urllib.request.urlopen(cur_vec_req)
        cur_vec_response_data = json.loads(cur_vec_response.read().decode())
        print(cur_vec_response_data)
        futil.log(f"Request for optimal vector sent for experiment {experiment_id} returned: {cur_vec_response_data}")
        cur_motors = int(cur_vec_response_data['new_suggestion'][0])
        cur_extrusions = int(cur_vec_response_data['new_suggestion'][1])
        # synthesize with vector
        synth_with_vec_response = synthesize_with_vector([cur_motors, cur_extrusions])

        # if synth fails tell score 0
        if "FAIL" in synth_with_vec_response:
            print("Synthesis failed")
            # tell optimizer bad score
            request_dict = {
                "result": 0,
                "synthesis_vector": [cur_motors, cur_extrusions],
                "experiment_id": experiment_id,
            }
            payload = json.dumps(
                request_dict,
                indent=4,
            ).encode("utf-8")
            print("Send request")
            print(request_dict)
            req = urllib.request.Request("http://127.0.0.1:8000/bo/update-with-result")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("Content-Length", len(payload))
            response = urllib.request.urlopen(req, payload)
            print(response.read().decode())
        else:
            synth_with_vec_response_data = json.loads(synth_with_vec_response)
            assembly_id = synth_with_vec_response_data['_id']
            # assemble cheapest assembly
            request_cheapest_response = request_cheapest(assembly_id)

            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                    ui.messageBox('No active Fusion design', title)
                    return

            root = design.rootComponent  # root component 
            components = design.allComponents

            # set the names        
            robot_name = root.name.split()[0]
            package_name = robot_name

            save_dir = export_path + '/' + package_name
    
            try: os.makedirs(save_dir)
            except: pass  

            package_dir = os.path.abspath(os.path.dirname(__file__)) + '/package/'


            # run motion planning
            joints_dict, msg = make_joints_dict(root,msg)
            if msg != success_msg:
                ui.messageBox(
                    msg,
                    title,
                    adsk.core.MessageBoxButtonTypes.OKCancelButtonType
                )
                # Generate inertial_dict
            inertial_dict, msg = make_inertial_dict(root, msg)
            if msg != success_msg:
                ui.messageBox(
                    msg,
                    title,
                    adsk.core.MessageBoxButtonTypes.OKCancelButtonType
                )
                return 0
            elif not 'link_0_1' in inertial_dict:
                msg = 'There is no base_link. Please set base_link and run again.'
                ui.messageBox(
                    msg,
                    title,
                    adsk.core.MessageBoxButtonTypes.OKCancelButtonType
                )
                return 0
            
            links_xyz_dict = {}
            
            # --------------------
            # Generate STL FILES
            export_stl(design, save_dir, root, robot_name)

            payload = json.dumps({
                "joints_dict": joints_dict,
                "links_xyz_dict": links_xyz_dict,
                "inertial_dict": inertial_dict,
                "package_name": package_name,
                "robot_name": robot_name,
                "save_dir": save_dir,
                "export_path": export_path
            }).encode('utf-8')
            # POST the payload to the backend server

            # check for task list in backend first and only send request if no tasks are running
            req = urllib.request.Request("http://127.0.0.1:8000/bo/store-mp-files")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("Content-Length", len(payload))
            response = urllib.request.urlopen(req, payload)
            
            raw_response = response.read().decode()
            print(raw_response)
            response_data = json.loads(raw_response)
            task_id = response_data['task_id']

            status_req = urllib.request.Request(f"http://127.0.0.1:8000/bo/{task_id}/status")
            motion_planning_progress_dialog = ui.createProgressDialog()
            motion_planning_progress_dialog.show("Experiment in Progress", "Running Experiment...", 0, 1)
            # loop to check the status of the task
            success = False
            once = True
            if motion_planning_progress_dialog is not None:
                previous_max = motion_planning_progress_dialog.maximumValue
                previous_progress = motion_planning_progress_dialog.progressValue
                previous_msg = motion_planning_progress_dialog.message
            while not success:
                response = urllib.request.urlopen(status_req)
                response_data = json.loads(response.read().decode())
                if "total_time" in response_data:
                    success = True
                    print(f"Task completed in {response_data['total_time']} seconds.")
                    print(f"success_rate: {response_data['success_rate']}")
                    print(f"success_list: {response_data['success_list']}")
                elif 'error' in response_data:
                    success = False
                if not success:
                    if (motion_planning_progress_dialog is not None) and once:
                        once = False
                        motion_planning_progress_dialog.message = (
                            motion_planning_progress_dialog.message + "\n\nWaiting for Motion Planning..."
                        )
                        motion_planning_progress_dialog.maximumValue = 1000
                        motion_planning_progress_dialog.progressValue = 0
                    if motion_planning_progress_dialog is not None:
                        motion_planning_progress_dialog.progressValue += (
                            1 if motion_planning_progress_dialog.progressValue < 999 else -1
                        )
                    do_events_for_duration(0.01)  # Allow the main thread to process events
                    ui.activeSelections.clear()
                    adsk.doEvents()
            if motion_planning_progress_dialog is not None:
                motion_planning_progress_dialog.maximumValue = previous_max
                motion_planning_progress_dialog.progressValue = previous_progress
                motion_planning_progress_dialog.message = previous_msg

            motion_planning_progress_dialog.hide()

            # tell score to bo
            request_dict = {
                "result": response_data['success_rate'],
                "synthesis_vector": [cur_motors, cur_extrusions],
                "experiment_id": experiment_parameters["experiment_id"],
            }
            payload = json.dumps(
                request_dict,
                indent=4,
            ).encode("utf-8")
            print("Send request")
            print(request_dict)
            req = urllib.request.Request("http://127.0.0.1:8000/bo/update-with-result")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("Content-Length", len(payload))
            response = urllib.request.urlopen(req, payload)
            print(response.read().decode())
            progress_dialog.progressValue += 1
    # end of loop
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



