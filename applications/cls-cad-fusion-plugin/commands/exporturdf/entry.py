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

app = adsk.core.Application.get()
ui = app.userInterface
joint = None

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_export_project_urdf"
CMD_NAME = "Export Project as URDF"
CMD_DESCRIPTION = "Export project files as URDF for development."
IS_PROMOTED = True
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "CRAWL"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "resources", "")


local_handlers = []
progress_dialog: adsk.core.ProgressDialog = None
export_path = ""
# TODO: send files to backend
# TODO: also create moveit_configs

def setup_package_xml(save_dir, package_name, robot_name):
    """
    Creates a package.xml file in the specified directory with predefined content.
    
    :param save_dir: Path to the directory where package.xml should be saved.
    :param robot_name: Name of the robot for the package.
    """
    description = f"URDF {package_name} package"
    
    package_content = f"""<?xml version="1.0"?>
<package format="2">
    <name>{package_name}</name>
    <version>0.0.0</version>
    <description>{description}</description>

    <maintainer email="felix.wolff@tu-dortmund.de">Felix Wolff</maintainer>
    <license>Apache</license>

    <author email="felix.wolff@tu-dortmund.de">Felix Wolff</author>

    <buildtool_depend>catkin</buildtool_depend>
    <build_depend>rospy</build_depend>
    <build_export_depend>rospy</build_export_depend>
    <exec_depend>rospy</exec_depend>

    <export>
    </export>
</package>
"""
    
    # Define the file path
    package_file_path = os.path.join(save_dir, "package.xml")
    
    # Write the content to the file
    with open(package_file_path, "w") as f:
        f.write(package_content)


def setup_cmakelists(save_dir, package_name, robot_name):
    """
    Creates a CMakeLists.txt file in the specified directory with predefined content.
    
    :param save_dir: Path to the directory where CMakeLists.txt should be saved.
    """
    catkin_INCLUDE_DIRS = "${catkin_INCLUDE_DIRS}"
    cmake_content = f"""cmake_minimum_required(VERSION 2.8.3)
project({package_name})

find_package(catkin REQUIRED COMPONENTS
  rospy
)

catkin_package(
)

include_directories(
# include
  {catkin_INCLUDE_DIRS}
)
"""
    
    # Define the file path
    cmake_file_path = os.path.join(save_dir, "CMakeLists.txt")
    
    # Write the content to the file
    with open(cmake_file_path, "w") as f:
        f.write(cmake_content)

def copy_package(save_dir, package_dir):
    try: os.makedirs(save_dir + '/launch')
    except: pass 
    try: os.makedirs(save_dir + '/urdf')
    except: pass 
    shutil.copytree(package_dir, save_dir)

def update_cmakelists(save_dir, package_name):
    file_name = save_dir + '/CMakeLists.txt'

    for line in fileinput.input(file_name, inplace=True):
        if 'project(fusion2urdf)' in line:
            sys.stdout.write("project(" + package_name + ")\n")
        else:
            sys.stdout.write(line)

def update_package_xml(save_dir, package_name):
    file_name = save_dir + '/package.xml'

    for line in fileinput.input(file_name, inplace=True):
        if '<name>' in line:
            sys.stdout.write("  <name>" + package_name + "</name>\n")
        elif '<description>' in line:
            sys.stdout.write("<description>The " + package_name + " package</description>\n")
        else:
            sys.stdout.write(line)

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

def write_link_urdf(joints_dict, repo, links_xyz_dict, file_name, inertial_dict):
    """
    Write links information into urdf "repo/file_name"
    
    
    Parameters
    ----------
    joints_dict: dict
        information of the each joint
    repo: str
        the name of the repository to save the xml file
    links_xyz_dict: vacant dict
        xyz information of the each link
    file_name: str
        urdf full path
    inertial_dict:
        information of the each inertial
    
    Note
    ----------
    In this function, links_xyz_dict is set for write_joint_tran_urdf.
    The origin of the coordinate of center_of_mass is the coordinate of the link
    """
    with open(file_name, mode='a') as f:
        # for base_link -> not needed anomyore
        """
        center_of_mass = inertial_dict['link_0_1']['center_of_mass']
        link = Link(name='link_0_1', xyz=[0,0,0], 
            center_of_mass=center_of_mass, repo=repo,
            mass=inertial_dict['link_0_1']['mass'],
            inertia_tensor=inertial_dict['link_0_1']['inertia'])
        links_xyz_dict[link.name] = link.xyz
        link.make_link_xml()
        f.write(link.link_xml)
        f.write('\n')
        """

        # others
        for joint in joints_dict:
            name = joints_dict[joint]['child']
            # check in which link part with name is located
            center_of_mass = \
                [ i-j for i, j in zip(inertial_dict[name]['center_of_mass'], joints_dict[joint]['xyz'])]
            link = Link(name=name, xyz=joints_dict[joint]['xyz'],\
                center_of_mass=center_of_mass,\
                repo=repo, mass=inertial_dict[name]['mass'],\
                inertia_tensor=inertial_dict[name]['inertia'])
            links_xyz_dict[link.name] = link.xyz            
            link.make_link_xml()
            f.write(link.link_xml)
            f.write('\n')


def write_joint_urdf(joints_dict, repo, links_xyz_dict, file_name):
    """
    Write joints and transmission information into urdf "repo/file_name"
    
    
    Parameters
    ----------
    joints_dict: dict
        information of the each joint
    repo: str
        the name of the repository to save the xml file
    links_xyz_dict: dict
        xyz information of the each link
    file_name: str
        urdf full path
    """
    
    with open(file_name, mode='a') as f:
        for j in joints_dict:
            parent = joints_dict[j]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[j]['child']
                joint_type = joints_dict[j]['type']
                upper_limit = joints_dict[j]['upper_limit']
                lower_limit = joints_dict[j]['lower_limit']
                try:
                    xyz = [round(p-c, 6) for p, c in \
                        zip(links_xyz_dict[parent], links_xyz_dict[child])]  # xyz = parent - child
                except KeyError as ke:
                    app = adsk.core.Application.get()
                    ui = app.userInterface
                    ui.messageBox("There seems to be an error with the connection between\n\n%s\nand\n%s\n\nCheck \
    whether the connections\nparent=component2=%s\nchild=component1=%s\nare correct or if you need \
    to swap component1<=>component2"
                    % (parent, child, parent, child), "Error!")
                    quit()
                    
                joint = Joint(name=j, joint_type = joint_type, xyz=xyz, \
                axis=joints_dict[j]['axis'], parent=parent, child=child, \
                upper_limit=upper_limit, lower_limit=lower_limit)
                joint.make_joint_xml()
                joint.make_transmission_xml()
                f.write(joint.joint_xml)
                f.write('\n')
                

def write_robot_endtag(file_name):
    """
    Write the </robot> tag at the end of the urdf
    
    
    Parameters
    ----------
    file_name: str
        urdf full path
    """
    with open(file_name, mode='a') as f:
        f.write('</robot>\n')

def write_gazebo_endtag(joints_dict, file_name):
    """
    Write about gazebo_plugin and the </robot> tag at the end of the urdf
    
    
    Parameters
    ----------
    file_name: str
        urdf full path
    """
    with open(file_name, mode='a') as f:
        f.write('<gazebo>\n')
        f.write('   <plugin filename="libgazebo_ros_control.so" name="control"/>\n')
        f.write('</gazebo>\n')

        f.write('\n')
        # first one has gravity true
        # for base_link
        f.write('<gazebo reference="link_0_1">\n')
        f.write('  <material>Gazebo/Silver</material>\n')
        f.write('  <mu1>0.2</mu1>\n')
        f.write('  <mu2>0.2</mu2>\n')
        f.write('  <selfCollide>true</selfCollide>\n')
        f.write('  <gravity>true</gravity>\n')
        f.write('</gazebo>\n')
        f.write('\n')

        # others
        for joint in joints_dict:
            name = joints_dict[joint]['child']
            if name == 'link_0_1':
                continue
            f.write('<gazebo reference="{}">\n'.format(name))
            f.write('  <material>Gazebo/Silver</material>\n')
            f.write('  <mu1>0.2</mu1>\n')
            f.write('  <mu2>0.2</mu2>\n')
            f.write('  <selfCollide>true</selfCollide>\n')
            f.write('</gazebo>\n')
            f.write('\n')

        f.write('</robot>\n')
        
# entry point urdf
def write_urdf(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):
    # TODO: check why limit tag is missing
    # TODO: xyz in joint tags should not be zero everytime
    # TODO: double check axis calculation
    file_dir = os.path.join(save_dir, 'urdf')
    file_path = os.path.join(file_dir, robot_name + '.urdf')
    try: os.makedirs(file_dir)
    except: pass 

    repo = package_name + '/meshes/'  # the repository of binary stl files
    with open(file_path, mode='w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write('<robot name="{}" xmlns:xacro="http://www.ros.org/wiki/xacro">\n'.format(robot_name))
        f.write('\n')
        f.write('<material name="silver">\n')
        f.write('  <color rgba="0.700 0.700 0.700 1.000"/>\n')
        f.write('</material>\n')
        f.write('\n')

    write_link_urdf(joints_dict, repo, links_xyz_dict, file_path, inertial_dict)
    write_joint_urdf(joints_dict, repo, links_xyz_dict, file_path)
    write_transmissions_urdf(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)  
    write_gazebo_endtag(joints_dict, file_path)

def write_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):

    try: os.makedirs(save_dir + '/urdf')
    except: pass 


    file_name = save_dir + '/urdf/' + robot_name + '.xacro'  # the name of urdf file
    repo = package_name + '/meshes/'  # the repository of binary stl files
    with open(file_name, mode='w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write('<robot name="{}" xmlns:xacro="http://www.ros.org/wiki/xacro">\n'.format(robot_name))
        f.write('\n')
        f.write('<xacro:include filename="$(find {})/urdf/materials.xacro" />'.format(package_name))
        f.write('\n')
        f.write('<xacro:include filename="$(find {})/urdf/{}.trans" />'.format(package_name, robot_name))
        f.write('\n')
        f.write('<xacro:include filename="$(find {})/urdf/{}.gazebo" />'.format(package_name, robot_name))
        f.write('\n')

    write_link_urdf(joints_dict, repo, links_xyz_dict, file_name, inertial_dict)
    write_joint_urdf(joints_dict, repo, links_xyz_dict, file_name)
    write_robot_endtag(file_name)

# entry point materials xacro
def write_materials_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):
    try: os.makedirs(save_dir + '/urdf')
    except: pass  

    file_name = save_dir + '/urdf/materials.xacro'  # the name of urdf file
    with open(file_name, mode='w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write('<robot name="{}" xmlns:xacro="http://www.ros.org/wiki/xacro" >\n'.format(robot_name))
        f.write('\n')
        f.write('<material name="silver">\n')
        f.write('  <color rgba="0.700 0.700 0.700 1.000"/>\n')
        f.write('</material>\n')
        f.write('\n')
        f.write('</robot>\n')

# entry point transmissions xacro
def write_transmissions_urdf(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):
    """
    Write joints and transmission information into urdf "repo/file_name"
    
    
    Parameters
    ----------
    joints_dict: dict
        information of the each joint
    repo: str
        the name of the repository to save the xml file
    links_xyz_dict: dict
        xyz information of the each link
    file_name: str
        urdf full path
    """
    
    file_name = save_dir + '/urdf/{}.urdf'.format(robot_name)  # the name of urdf file
    with open(file_name, mode='a') as f:

        for j in joints_dict:
            parent = joints_dict[j]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[j]['child']
                joint_type = joints_dict[j]['type']
                upper_limit = joints_dict[j]['upper_limit']
                lower_limit = joints_dict[j]['lower_limit']
                try:
                    xyz = [round(p-c, 6) for p, c in \
                        zip(links_xyz_dict[parent], links_xyz_dict[child])]  # xyz = parent - child
                except KeyError as ke:
                    app = adsk.core.Application.get()
                    ui = app.userInterface
                    ui.messageBox("There seems to be an error with the connection between\n\n%s\nand\n%s\n\nCheck \
    whether the connections\nparent=component2=%s\nchild=component1=%s\nare correct or if you need \
    to swap component1<=>component2"
                    % (parent, child, parent, child), "Error!")
                    quit()
                    
                joint = Joint(name=j, joint_type = joint_type, xyz=xyz, \
                axis=joints_dict[j]['axis'], parent=parent, child=child, \
                upper_limit=upper_limit, lower_limit=lower_limit)
                if joint_type != 'fixed':
                    joint.make_transmission_xml()
                    f.write(joint.tran_xml)
                    f.write('\n')

# entry point transmissions xacro
def write_transmissions_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):
    """
    Write joints and transmission information into urdf "repo/file_name"
    
    
    Parameters
    ----------
    joints_dict: dict
        information of the each joint
    repo: str
        the name of the repository to save the xml file
    links_xyz_dict: dict
        xyz information of the each link
    file_name: str
        urdf full path
    """
    
    file_name = save_dir + '/urdf/{}.trans'.format(robot_name)  # the name of urdf file
    with open(file_name, mode='w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write('<robot name="{}" xmlns:xacro="http://www.ros.org/wiki/xacro" >\n'.format(robot_name))
        f.write('\n')

        for j in joints_dict:
            parent = joints_dict[j]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[j]['child']
                joint_type = joints_dict[j]['type']
                upper_limit = joints_dict[j]['upper_limit']
                lower_limit = joints_dict[j]['lower_limit']
                try:
                    xyz = [round(p-c, 6) for p, c in \
                        zip(links_xyz_dict[parent], links_xyz_dict[child])]  # xyz = parent - child
                except KeyError as ke:
                    app = adsk.core.Application.get()
                    ui = app.userInterface
                    ui.messageBox("There seems to be an error with the connection between\n\n%s\nand\n%s\n\nCheck \
    whether the connections\nparent=component2=%s\nchild=component1=%s\nare correct or if you need \
    to swap component1<=>component2"
                    % (parent, child, parent, child), "Error!")
                    quit()
                    
                joint = Joint(name=j, joint_type = joint_type, xyz=xyz, \
                axis=joints_dict[j]['axis'], parent=parent, child=child, \
                upper_limit=upper_limit, lower_limit=lower_limit)
                if joint_type != 'fixed':
                    joint.make_transmission_xml()
                    f.write(joint.tran_xml)
                    f.write('\n')

        f.write('</robot>\n')

# entry point gazebo xacro
def write_gazebo_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir):
    try: os.makedirs(save_dir + '/urdf')
    except: pass  

    file_name = save_dir + '/urdf/' + robot_name + '.gazebo'  # the name of urdf file
    repo = robot_name + '/meshes/'  # the repository of binary stl files
    #repo = package_name + '/' + robot_name + '/bin_stl/'  # the repository of binary stl files
    with open(file_name, mode='w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write('<robot name="{}" xmlns:xacro="http://www.ros.org/wiki/xacro" >\n'.format(robot_name))
        f.write('\n')
        f.write('<xacro:property name="body_color" value="Gazebo/Silver" />\n')
        f.write('\n')

        gazebo = Element('gazebo')
        plugin = SubElement(gazebo, 'plugin')
        plugin.attrib = {'name':'control', 'filename':'libgazebo_ros_control.so'}
        gazebo_xml = "\n".join(prettify(gazebo).split("\n")[1:])
        f.write(gazebo_xml)

        # for base_link
        f.write('<gazebo reference="link_0_1">\n')
        f.write('  <material>${body_color}</material>\n')
        f.write('  <mu1>0.2</mu1>\n')
        f.write('  <mu2>0.2</mu2>\n')
        f.write('  <selfCollide>true</selfCollide>\n')
        f.write('  <gravity>true</gravity>\n')
        f.write('</gazebo>\n')
        f.write('\n')

        # others
        for joint in joints_dict:
            name = joints_dict[joint]['child']
            if name == 'link_0_1':
                continue
            f.write('<gazebo reference="{}">\n'.format(name))
            f.write('  <material>${body_color}</material>\n')
            f.write('  <mu1>0.2</mu1>\n')
            f.write('  <mu2>0.2</mu2>\n')
            f.write('  <selfCollide>true</selfCollide>\n')
            f.write('</gazebo>\n')
            f.write('\n')

        f.write('</robot>\n')

# entry display launch -> unused probably
def write_display_launch(package_name, robot_name, save_dir):
    """
    write display launch file "save_dir/launch/display.launch"


    Parameter
    ---------
    robot_name: str
    name of the robot
    save_dir: str
    path of the repository to save
    """   
    try: os.makedirs(save_dir + '/launch')
    except: pass     

    launch = Element('launch')     

    arg1 = SubElement(launch, 'arg')
    arg1.attrib = {'name':'model', 'default':'$(find {})/urdf/{}.xacro'.format(package_name, robot_name)}

    arg2 = SubElement(launch, 'arg')
    arg2.attrib = {'name':'gui', 'default':'true'}

    arg3 = SubElement(launch, 'arg')
    arg3.attrib = {'name':'rvizconfig', 'default':'$(find {})/launch/urdf.rviz'.format(package_name)}

    param1 = SubElement(launch, 'param')
    param1.attrib = {'name':'robot_description', 'command':'$(find xacro)/xacro $(arg model)'}

    param2 = SubElement(launch, 'param')
    param2.attrib = {'name':'use_gui', 'value':'$(arg gui)'}

    node1 = SubElement(launch, 'node')
    node1.attrib = {'name':'joint_state_publisher_gui', 'pkg':'joint_state_publisher_gui', 'type':'joint_state_publisher_gui'}

    node2 = SubElement(launch, 'node')
    node2.attrib = {'name':'robot_state_publisher', 'pkg':'robot_state_publisher', 'type':'robot_state_publisher'}

    node3 = SubElement(launch, 'node')
    node3.attrib = {'name':'rviz', 'pkg':'rviz', 'args':'-d $(arg rvizconfig)', 'type':'rviz', 'required':'true'}

    launch_xml = "\n".join(prettify(launch).split("\n")[1:])        

    file_name = save_dir + '/launch/display.launch'    
    with open(file_name, mode='w') as f:
        f.write(launch_xml)

# entry gazebo launch -> unused probably
def write_gazebo_launch(package_name, robot_name, save_dir):
    """
    write gazebo launch file "save_dir/launch/gazebo.launch"
    
    
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    """
    
    try: os.makedirs(save_dir + '/launch')
    except: pass     
    
    launch = Element('launch')
    param = SubElement(launch, 'param')
    param.attrib = {'name':'robot_description', 'command':'$(find xacro)/xacro $(find {})/urdf/{}.xacro'.format(package_name, robot_name)}

    node = SubElement(launch, 'node')
    node.attrib = {'name':'spawn_urdf', 'pkg':'gazebo_ros', 'type':'spawn_model',\
                    'args':'-param robot_description -urdf -model {}'.format(robot_name)}

    include_ =  SubElement(launch, 'include')
    include_.attrib = {'file':'$(find gazebo_ros)/launch/empty_world.launch'}        
    
    number_of_args = 5
    args = [None for i in range(number_of_args)]
    args_name_value_pairs = [['paused', 'true'], ['use_sim_time', 'true'],
                             ['gui', 'true'], ['headless', 'false'], 
                             ['debug', 'false']]
                             
    for i, arg in enumerate(args):
        arg = SubElement(include_, 'arg')
        arg.attrib = {'name' : args_name_value_pairs[i][0] , 
        'value' : args_name_value_pairs[i][1]}


    
    launch_xml = "\n".join(prettify(launch).split("\n")[1:])        
    
    file_name = save_dir + '/launch/' + 'gazebo.launch'    
    with open(file_name, mode='w') as f:
        f.write(launch_xml)

# entry controller launch
def write_control_launch(package_name, robot_name, save_dir, joints_dict):
    """
    write control launch file "save_dir/launch/controller.launch"
    
    
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    
    try: os.makedirs(save_dir + '/launch')
    except: pass     
    
    #launch = Element('launch')

    controller_name = robot_name + '_controller'
    #rosparam = SubElement(launch, 'rosparam')
    #rosparam.attrib = {'file':'$(find {})/launch/controller.yaml'.format(package_name),
    #                   'command':'load'}
                       
    controller_args_str = ""
    for j in joints_dict:
        joint_type = joints_dict[j]['type']
        if joint_type != 'fixed':
            controller_args_str += j + '_position_controller '
    controller_args_str += 'joint_state_controller '

    node_controller = Element('node')
    node_controller.attrib = {'name':'controller_spawner', 'pkg':'controller_manager', 'type':'spawner',\
                    'respawn':'false', 'output':'screen', 'ns':robot_name,\
                    'args':'{}'.format(controller_args_str)}
    
    node_publisher = Element('node')
    node_publisher.attrib = {'name':'robot_state_publisher', 'pkg':'robot_state_publisher',\
                    'type':'robot_state_publisher', 'respawn':'false', 'output':'screen'}
    remap = SubElement(node_publisher, 'remap')
    remap.attrib = {'from':'/joint_states',\
                    'to':'/' + robot_name + '/joint_states'}
    
    #launch_xml  = "\n".join(utils.prettify(launch).split("\n")[1:])   
    launch_xml  = "\n".join(prettify(node_controller).split("\n")[1:])   
    launch_xml += "\n".join(prettify(node_publisher).split("\n")[1:])   

    file_name = save_dir + '/launch/controller.launch'    
    with open(file_name, mode='w') as f:
        f.write('<launch>\n')
        f.write('\n')
        #for some reason ROS is very picky about the attribute ordering, so we'll bitbang this element
        f.write('<rosparam file="$(find {})/launch/controller.yaml" command="load"/>'.format(package_name))
        f.write('\n')
        f.write(launch_xml)
        f.write('\n')
        f.write('</launch>')
        

def write_cartesian_limits_yaml(save_dir):
    """
    write yaml file "save_dir/launch/cartesian_limits.yaml"
    
    
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass 

    file_name = save_dir + '/moveit_configs/config/cartesian_limits.yaml'
    with open(file_name, 'w') as f:
        f.write('cartesian_limits:\n')
        f.write('  max_trans_vel: 1\n')
        f.write('  max_trans_acc: 2.25\n')
        f.write('  max_trans_dev: -5\n')
        f.write('  max_rot_vel: 1.57\n')

def write_chomp_planning_yaml(save_dir):
    """
    write yaml file "save_dir/moveit_configs/config/chomp_planning.yaml"
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass 

    file_name = save_dir + '/moveit_configs/config/chomp_planning.yaml'
    with open(file_name, 'w') as f:
        f.write('planning_time_limit: 10.0\n')
        f.write('max_iterations: 200\n')
        f.write('max_iterations_after_collision_free: 5\n')
        f.write('smoothness_cost_weight: 0.1\n')
        f.write('obstacle_cost_weight: 1.0\n')
        f.write('learning_rate: 0.01\n')
        f.write('smoothness_cost_velocity: 0.0\n')
        f.write('smoothness_cost_acceleration: 1.0\n')
        f.write('smoothness_cost_jerk: 0.0\n')
        f.write('ridge_factor: 0.0\n')
        f.write('use_pseudo_inverse: false\n')
        f.write('pseudo_inverse_ridge_factor: 1e-4\n')
        f.write('joint_update_limit: 0.1\n')
        f.write('collision_clearance: 0.2\n')
        f.write('collision_threshold: 0.07\n')
        f.write('use_stochastic_descent: true\n')
        f.write('enable_failure_recovery: false\n')
        f.write('max_recovery_attempts: 5\n')

def write_fake_controllers_yaml(package_name, robot_name, save_dir, joints_dict):
    """
    write yaml file "save_dir/moveit_configs/config/fake_controllers.yaml"
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass 

    file_name = save_dir + '/moveit_configs/config/fake_controllers.yaml'
    with open(file_name, 'w') as f:
        f.write('controller_list:\n')
        # my_arm
        f.write("   - name: fake_my_arm_controller\n")
        f.write("     type: $(arg fake_execution_type)\n")
        f.write("     joints:\n")
        for joint in dict(list(joints_dict.items())[:-1]):
            parent = joints_dict[joint]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[joint]['child']
            f.write("       - " + joint + "\n")

        # my_effector
        f.write("   - name: fake_my_effector_controller\n")
        f.write("     type: $(arg fake_execution_type)\n")
        f.write("     joints:\n")
        for joint in dict([list(joints_dict.items())[-1]]):
            parent = joints_dict[joint]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[joint]['child']
            f.write("       - " + joint + "\n")
        # my_robot_top_group_controller
        f.write("   - name: fake_my_robot_top_group_controller\n")
        f.write("     type: $(arg fake_execution_type)\n")
        f.write("     joints:\n")
        for joint in joints_dict:
            parent = joints_dict[joint]['parent']
            if(parent == "base_link"):
                continue
            else:
                child = joints_dict[joint]['child']
            f.write("       - " + joint + "\n")
        f.write("initial:\n")
        f.write("   - group: my_effector\n")
        f.write("     pose: open\n")

def write_gazebo_controllers_yaml(save_dir):
    """
    write yaml file "save_dir/moveit_configs/config/gazebo_controllers.yaml"
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass 

    file_name = save_dir + '/moveit_configs/config/gazebo_controllers.yaml'
    with open(file_name, 'w') as f:
        f.write("joint_state_controller:\n")
        f.write("  type: joint_state_controller/JointStateController\n")
        f.write("  publish_rate: 50\n")

def write_joint_limits_yaml(package_name, robot_name, save_dir, joints_dict):
    """
    write yaml file "save_dir/moveit_configs/config/joint_limits.yaml"
    
    
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass
    file_name = save_dir + '/moveit_configs/config/joint_limits.yaml'
    with open(file_name, 'w') as f:
        f.write('# joint_limits.yaml allows the dynamics properties specified in the URDF to be overwritten or augmented as needed\n\n')
        f.write('# For beginners, we downscale velocity and acceleration limits.\n')
        f.write('# You can always specify higher scaling factors (<= 1.0) in your motion requests.\n')
        f.write('# Increase the values below to 1.0 to always move at maximum speed.\n\n')
        f.write('default_velocity_scaling_factor: 0.1\n')
        f.write('default_acceleration_scaling_factor: 0.1\n')
        
        f.write('\n# Specific joint properties can be changed with the keys [max_position, min_position, max_velocity, max_acceleration]\n')
        f.write('# Joint limits can be turned off with [has_velocity_limits, has_acceleration_limits]\n')
        f.write('joint_limits:\n')
        
        for joint in dict(list(joints_dict.items())[:-1]):  # last joint is gripper, so skip it
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write('  ' + joint + ':\n')
                f.write('    has_velocity_limits: false\n')
                f.write('    max_velocity: 0\n')
                f.write('    has_acceleration_limits: false\n')
                f.write('    max_acceleration: 0\n')
        for joint in dict([list(joints_dict.items())[-1]]):
            f.write('  ' + joint + ':\n')
            f.write('    has_velocity_limits: false\n')
            f.write('    max_velocity: 0\n')
            f.write('    has_acceleration_limits: false\n')
            f.write('    max_acceleration: 0\n')
            f.write('    max_position: 2.8\n')
            f.write('    min_position: 0.98\n')  # TODO: gripper joint limits, can be changed later

        

def write_kinematics_yaml(save_dir):
    """
    write yaml file "save_dir/moveit_configs/config/kinematics.yaml"
    
    
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass
    
    file_name = save_dir + '/moveit_configs/config/kinematics.yaml'
    with open(file_name, 'w') as f:
        f.write('my_arm:\n')
        f.write('  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin\n')
        f.write('  kinematics_solver_attempts: 100\n')
        f.write('  kinematics_solver_search_resolution: 0.005\n')
        f.write('  kinematics_solver_timeout: 0.1\n')
        f.write('  position_only_ik: True\n')
        
        f.write('\nmy_robot_top_group:\n')
        f.write('  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin\n')
        f.write('  kinematics_solver_attempts: 100\n')
        f.write('  kinematics_solver_search_resolution: 0.005\n')
        f.write('  kinematics_solver_timeout: 0.1\n')
        f.write('  position_only_ik: True\n')

        f.write('\nmy_effector:\n')
        f.write('  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin\n')
        f.write('  kinematics_solver_attempts: 100\n')
        f.write('  kinematics_solver_search_resolution: 0.005\n')
        f.write('  kinematics_solver_timeout: 0.1\n')
        f.write('  position_only_ik: True\n')

def write_srdf(package_name, robot_name, save_dir, joints_dict, links_xyz_dict):
    """
    write srdf file "save_dir/moveit_configs/config/{}.srdf"
    Parameter
    ---------
    package_name: str
        name of the package
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    links_xyz_dict: dict
        xyz information of the links
    """
    
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass

    file_name = save_dir + '/moveit_configs/config/' + robot_name + '.srdf'
    
    with open(file_name, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!--This does not replace URDF, and is not an extension of URDF.\n')
        f.write('    This is a format for representing semantic information about the robot structure.\n')
        f.write('    A URDF file must exist for this robot as well, where the joints and the links that are referenced are defined\n')
        f.write('-->\n')
        f.write('<robot name="{}">\n'.format(robot_name))
        f.write('    <!--GROUPS: Representation of a set of joints and links. This can be useful for specifying DOF to plan for, defining arms, end effectors, etc-->\n')
        f.write('    <!--LINKS: When a link is specified, the parent joint of that link (if it exists) is automatically included-->\n')
        f.write('    <!--JOINTS: When a joint is specified, the child link of that joint (which will always exist) is automatically included-->\n')
        f.write('    <!--CHAINS: When a chain is specified, all the links along the chain (including endpoints) are included in the group. Additionally, all the joints that are parents to included links are also included. This means that joints along the chain and the parent joint of the base link are included in the group-->\n')
        f.write('    <!--SUBGROUPS: Groups can also be formed by referencing to already defined group names-->\n')
        f.write('    <group name="my_arm">\n')
        # dict([list(joints_dict.items())[-1]])
        # dict(list(joints_dict.items())[:-1])
        for link in dict(list(links_xyz_dict.items())[:-1]):  # last link is gripper, so skip it
            f.write('        <link name="{}"/>\n'.format(link))
        f.write('        <joint name="world_joint"/>\n')
        for joint in dict(list(joints_dict.items())[1:-1]):  # last joint is gripper, so skip it # WILL CAUSE ISSUES IF ONLY ONE JOINT IS LEFT BY THIS
            f.write('        <joint name="{}"/>\n'.format(joint))
        f.write('    </group>\n')
        
        f.write('    <group name="my_effector">\n')
        f.write('        <link name="{}"/>\n'.format(list(links_xyz_dict.items())[-1][0]))
        f.write('        <joint name="{}"/>\n'.format(list(joints_dict.items())[-1][0]))
        f.write('    </group>\n')
        
        f.write('    <group name="my_robot_top_group">\n')
        for link in dict(list(links_xyz_dict.items())):
            f.write('        <link name="{}"/>\n'.format(link))
        f.write('        <joint name="world_joint"/>\n')
        for joint in dict(list(joints_dict.items())[1:]):
            f.write('        <joint name="{}"/>\n'.format(joint))
        f.write('        <group name="my_arm"/>\n')
        f.write('        <group name="my_effector"/>\n')
        f.write('    </group>\n')
        
        f.write('    <!--GROUP STATES: Purpose: Define a named state for a particular group, in terms of joint values. This is useful to define states like \'folded arms\'-->\n')
        f.write('    <group_state name="open" group="my_effector">\n')
        f.write('        <joint name="{}" value="1.8"/>\n'.format(list(joints_dict.items())[-1][0]))
        f.write('    </group_state>\n')
        
        f.write('    <group_state name="closed" group="my_effector">\n')
        f.write('        <joint name="{}" value="0.9666"/>\n'.format(list(joints_dict.items())[-1][0]))
        f.write('    </group_state>\n')

        f.write('    END_EFFECTOR: Purpose: Represent information about an end effector.-->\n')
        f.write('    <end_effector name="my_end_effector" parent_link="{}" group="my_effector" parent_group="my_arm"/>\n'.format(list(links_xyz_dict.items())[-2][0]))
        
        f.write('    <!--VIRTUAL JOINT: Purpose: this element defines a virtual joint between a robot link and an external frame of reference (considered fixed with respect to the robot)-->\n')
        f.write('    <virtual_joint name="world_joint" type="fixed" parent_frame="world" child_link="{}"/>\n'.format(list(links_xyz_dict.items())[0][0]))
        f.write('    DISABLE COLLISIONS: By default it is assumed that any link of the robot could potentially come into collision with any other link in the robot. This tag disables collision checking between a specified pair of links.-->\n')
        for i in range(len(links_xyz_dict) - 1):
            f.write('    <disable_collisions link1="{}" link2="{}" reason="Adjacent"/>\n'.format(list(links_xyz_dict.items())[i][0], list(links_xyz_dict.items())[i+1][0]))
        f.write('</robot>\n')

def write_ompl_planning_yaml(save_dir):
    """
    write yaml file "save_dir/moveit_configs/config/ompl_planning.yaml"
    
    
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass
    file_name = save_dir + '/moveit_configs/config/ompl_planning.yaml'
    with open(file_name, 'w') as f:
        f.write('planner_configs:\n')
        f.write('  RRTstar:\n')
        f.write('    type: geometric::RRTstar\n')
        f.write('    range: 0.0  # Max motion added to tree. ==> maxDistance_ default: 0.0, if 0.0, set on setup()\n')
        f.write('    goal_bias: 0.05  # When close to goal select goal, with this probability? default: 0.05\n')
        f.write('    delay_collision_checking: 1  # Stop collision checking as soon as C-free parent found. default 1\n')
        f.write('    optimization_objective: PathLengthOptimizationObjective\n')
        f.write('    min_valid_path_fraction: 0.05\n')
    
        f.write('my_arm:\n')
        f.write('  planner_configs:\n')
        f.write('    - RRTstar\n')
        
        f.write('my_effector:\n')
        f.write('  planner_configs:\n')
        f.write('    - RRTstar\n')
        
        f.write('my_robot_top_group:\n')
        f.write('  planner_configs:\n')
        f.write('    - RRTstar\n')

def write_ros_controllers_yaml(package_name, robot_name, save_dir, joints_dict):
    """
    write yaml file "save_dir/moveit_configs/config/ros_controllers.yaml"
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass

    file_name = save_dir + '/moveit_configs/config/ros_controllers.yaml'
    
    with open(file_name, 'w') as f:
        # my arm
        f.write("my_arm_controller:\n")
        f.write("  type: effort_controllers/JointTrajectoryController\n")
        f.write("  joints:\n")
        for joint in dict(list(joints_dict.items())[1:-1]):  # last joint is gripper, so skip it
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    - {}\n".format(joint))
        f.write("  gains:\n")
        for joint in dict(list(joints_dict.items())[1:-1]):  # last joint is gripper, so skip it
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    {}:\n".format(joint))
                f.write("      p: 100\n")
                f.write("      d: 1\n")
                f.write("      i: 1\n")
                f.write("      i_clamp: 1\n")
        
        # my effector
        f.write("\nmy_effector_controller:\n")
        f.write("  type: effort_controllers/JointTrajectoryController\n")
        f.write("  joints:\n")
        for joint in dict([list(joints_dict.items())[-1]]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    - {}\n".format(joint))
        f.write("  gains:\n")
        for joint in dict([list(joints_dict.items())[-1]]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    {}:\n".format(joint))
                f.write("      p: 100\n")
                f.write("      d: 1\n")
                f.write("      i: 1\n")
                f.write("      i_clamp: 1\n")

        # my robot top group
        f.write("\nmy_robot_top_group_controller:\n")
        f.write("  type: effort_controllers/JointTrajectoryController\n")
        f.write("  joints:\n")
        for joint in dict(list(joints_dict.items())[1:]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    - {}\n".format(joint))
        f.write("  gains:\n")
        for joint in dict(list(joints_dict.items())[1:]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write("    {}:\n".format(joint))
                f.write("      p: 100\n")
                f.write("      d: 1\n")
                f.write("      i: 1\n")
                f.write("      i_clamp: 1\n")

def write_sensors_3d_yaml(save_dir):
    """
    write yaml file "save_dir/moveit_configs/config/sensors_3d.yaml"
    
    
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass

    file_name = save_dir + '/moveit_configs/config/sensors_3d.yaml'
    with open(file_name, 'w') as f:
        f.write('sensors:\n')
        f.write('  []\n')

def write_simple_moveit_controllers_yaml(package_name, robot_name, save_dir, joints_dict):
    """
    write yaml file "save_dir/moveit_configs/config/simple_moveit_controllers.yaml"
    
    
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    try: os.makedirs(save_dir + '/moveit_configs/config')
    except: pass

    file_name = save_dir + '/moveit_configs/config/simple_moveit_controllers.yaml'
    
    with open(file_name, 'w') as f:
        f.write('controller_list:\n')
        
        # my arm controller
        f.write('  - name: my_arm_controller\n')
        f.write('    action_ns: follow_joint_trajectory\n')
        f.write('    type: FollowJointTrajectory\n')
        f.write('    default: True\n')
        f.write('    joints:\n')
        for joint in dict(list(joints_dict.items())[1:-1]):  # last joint is gripper, so skip it
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write('      - {}\n'.format(joint))
        
        # my effector controller
        f.write('  - name: my_effector_controller\n')
        f.write('    action_ns: follow_joint_trajectory\n')
        f.write('    type: FollowJointTrajectory\n')
        f.write('    default: True\n')
        f.write('    joints:\n')
        for joint in dict([list(joints_dict.items())[-1]]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write('      - {}\n'.format(joint))
        
        # my robot top group controller
        f.write('  - name: my_robot_top_group_controller\n')
        f.write('    action_ns: follow_joint_trajectory\n')
        f.write('    type: FollowJointTrajectory\n')
        f.write('    default: True\n')
        f.write('    joints:\n')
        for joint in dict(list(joints_dict.items())[1:]):
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write('      - {}\n'.format(joint))

def write_chomp_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/chomp_planning_pipeline.launch.xml'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <arg name="start_state_max_bounds_error" default="0.1" />\n')
        f.write('  <arg name="jiggle_fraction" default="0.05" />\n')
        f.write('  <!-- The request adapters (plugins) used when planning. ORDER MATTERS! -->\n')
        f.write('  <arg name="planning_adapters"\n')
        f.write('       default="default_planner_request_adapters/LimitMaxCartesianLinkSpeed\n')
        f.write('                default_planner_request_adapters/AddTimeParameterization\n')
        f.write('                default_planner_request_adapters/ResolveConstraintFrames\n')
        f.write('                default_planner_request_adapters/FixWorkspaceBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateCollision\n')
        f.write('                default_planner_request_adapters/FixStartStatePathConstraints"\n')
        f.write('                />\n')
        
        f.write('  <param name="planning_plugin" value="chomp_interface/CHOMPPlanner" />\n')
        f.write('  <param name="request_adapters" value="$(arg planning_adapters)" />\n')
        f.write('  <param name="start_state_max_bounds_error" value="$(arg start_state_max_bounds_error)" />\n')
        f.write('  <param name="jiggle_fraction" value="$(arg jiggle_fraction)" />\n')
        
        f.write('  <rosparam command="load" file="$(find moveit_configs)/config/chomp_planning.yaml" />\n')
        f.write('</launch>\n')

def write_default_warehouse_db_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/default_warehouse_db.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <arg name="reset" default="false"/>\n')
        f.write('  <!-- If not specified, we\'ll use a default database location -->\n')
        f.write('  <arg name="moveit_warehouse_database_path" default="$(find moveit_configs)/default_warehouse_mongo_db" />\n')
        f.write('\n')
        f.write('  <!-- Launch the warehouse with the configured database location -->\n')
        f.write('  <include file="$(dirname)/warehouse.launch">\n')
        f.write('    <arg name="moveit_warehouse_database_path" value="$(arg moveit_warehouse_database_path)" />\n')
        f.write('  </include>\n')
        f.write('\n')
        f.write('  <!-- If we want to reset the database, run this node -->\n')
        f.write('  <node if="$(arg reset)" name="$(anon moveit_default_db_reset)" type="moveit_init_demo_warehouse" pkg="moveit_ros_warehouse" respawn="false" output="screen" />\n')
        f.write('</launch>\n')

def write_demo_gazebo_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/demo_gazebo.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- MoveIt options -->\n')
        f.write('  <arg name="pipeline" default="ompl" doc="Planning pipeline to use with MoveIt"/>\n')
        f.write('\n')
        f.write('  <!-- Gazebo options -->\n')
        f.write('  <arg name="gazebo_gui" default="true" doc="Start Gazebo GUI"/>\n')
        f.write('  <arg name="paused" default="false" doc="Start Gazebo paused"/>\n')
        f.write('  <arg name="world_name" default="worlds/empty.world" doc="Gazebo world file"/>\n')
        f.write('  <arg name="world_pose" default="-x 0 -y 0 -z 0 -R 0 -P 0 -Y 0" doc="Pose to spawn the robot at"/>\n')
        f.write('\n')
        f.write('  <!-- Launch Gazebo and spawn the robot -->\n')
        f.write('  <include file="$(dirname)/gazebo.launch" pass_all_args="true"/>\n')
        f.write('\n')
        f.write('  <!-- Launch MoveIt -->\n')
        f.write('  <include file="$(dirname)/demo.launch" pass_all_args="true">\n')
        f.write('    <!-- robot_description is loaded by gazebo.launch, to enable Gazebo features -->\n')
        f.write('    <arg name="load_robot_description" value="false" />\n')
        f.write('    <arg name="moveit_controller_manager" value="ros_control" />\n')
        f.write('  </include>\n')
        f.write('</launch>\n')

def write_demo_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/demo.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- specify the planning pipeline -->\n')
        f.write('  <arg name="pipeline" default="ompl" />\n')
        f.write('\n')
        f.write('  <!-- By default, we do not start a database (it can be large) -->\n')
        f.write('  <arg name="db" default="false" />\n')
        f.write('  <!-- Allow user to specify database location -->\n')
        f.write('  <arg name="db_path" default="$(find moveit_configs)/default_warehouse_mongo_db" />\n')
        f.write('\n')
        f.write('  <!-- By default, we are not in debug mode -->\n')
        f.write('  <arg name="debug" default="false" />\n')
        f.write('\n')
        f.write('  <!-- By default, we will load or override the robot_description -->\n')
        f.write('  <arg name="load_robot_description" default="true"/>\n')
        f.write('\n')
        f.write('  <!-- Choose controller manager: fake, simple, or ros_control -->\n')
        f.write('  <arg name="moveit_controller_manager" default="fake" />\n')
        f.write('  <!-- Set execution mode for fake execution controllers -->\n')
        f.write('  <arg name="fake_execution_type" default="interpolate" />\n')
        f.write('\n')
        f.write('  <!-- By default, hide joint_state_publisher\'s GUI in \'fake\' controller_manager mode -->\n')
        f.write('  <arg name="use_gui" default="true" />\n')
        f.write('  <arg name="use_rviz" default="true" />\n')
        f.write('\n')
        f.write('  <!-- If needed, broadcast static tf for robot root -->\n')
        f.write('  <node pkg="tf2_ros" type="static_transform_publisher" name="virtual_joint_broadcaster_0" args="0 0 0 0 0 0 world link_0_1" />\n')
        f.write('\n')
        f.write('  <group if="$(eval arg(\'moveit_controller_manager\') == \'fake\')">\n')
        f.write('    <!-- We do not have a real robot connected, so publish fake joint states via a joint_state_publisher\n')
        f.write('         MoveIt\'s fake controller\'s joint states are considered via the \'source_list\' parameter -->\n')
        f.write('    <node name="joint_state_publisher" pkg="joint_state_publisher" type="joint_state_publisher" unless="$(arg use_gui)">\n')
        f.write('      <rosparam param="source_list">[move_group/fake_controller_joint_states]</rosparam>\n')
        f.write('    </node>\n')
        f.write('    <!-- If desired, a GUI version is available allowing to move the simulated robot around manually\n')
        f.write('         This corresponds to moving around the real robot without the use of MoveIt. -->\n')
        f.write('    <node name="joint_state_publisher" pkg="joint_state_publisher_gui" type="joint_state_publisher_gui" if="$(arg use_gui)">\n')
        f.write('      <rosparam param="source_list">[move_group/fake_controller_joint_states]</rosparam>\n')
        f.write('    </node>\n')
        f.write('\n')
        f.write('    <!-- Given the published joint states, publish tf for the robot links -->\n')
        f.write('    <node name="robot_state_publisher" pkg="robot_state_publisher" type="robot_state_publisher" respawn="true" output="screen" />\n')
        f.write('  </group>\n')
        f.write('\n')
        f.write('  <!-- Run the main MoveIt executable without trajectory execution (we do not have controllers configured by default) -->\n')
        f.write('  <include file="$(dirname)/move_group.launch">\n')
        f.write('    <arg name="allow_trajectory_execution" value="true"/>\n')
        f.write('    <arg name="moveit_controller_manager" value="$(arg moveit_controller_manager)" />\n')
        f.write('    <arg name="fake_execution_type" value="$(arg fake_execution_type)"/>\n')
        f.write('    <arg name="info" value="true"/>\n')
        f.write('    <arg name="debug" value="$(arg debug)"/>\n')
        f.write('    <arg name="pipeline" value="$(arg pipeline)"/>\n')
        f.write('    <arg name="load_robot_description" value="$(arg load_robot_description)"/>\n')
        f.write('  </include>\n')
        f.write('\n')
        f.write('  <!-- Run Rviz and load the default config to see the state of the move_group node -->\n')
        f.write('  <include file="$(dirname)/moveit_rviz.launch" if="$(arg use_rviz)">\n')
        f.write('    <arg name="rviz_config" value="$(dirname)/moveit.rviz"/>\n')
        f.write('    <arg name="debug" value="$(arg debug)"/>\n')
        f.write('  </include>\n')
        f.write('\n')
        f.write('  <!-- If database loading was enabled, start mongodb as well -->\n')
        f.write('  <include file="$(dirname)/default_warehouse_db.launch" if="$(arg db)">\n')
        f.write('    <arg name="moveit_warehouse_database_path" value="$(arg db_path)"/>\n')
        f.write('  </include>\n')
        f.write('</launch>\n')

def write_fake_moveit_controller_manager_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/fake_moveit_controller_manager.launch.xml'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- execute the trajectory in \'interpolate\' mode or jump to goal position in \'last point\' mode -->\n')
        f.write('  <arg name="fake_execution_type" default="interpolate" />\n')
        f.write('\n')
        f.write('  <!-- Set the param that trajectory_execution_manager needs to find the controller plugin -->\n')
        f.write('  <param name="moveit_controller_manager" value="moveit_fake_controller_manager/MoveItFakeControllerManager"/>\n')
        f.write('\n')
        f.write('  <!-- The rest of the params are specific to this plugin -->\n')
        f.write('  <rosparam subst_value="true" file="$(find moveit_configs)/config/fake_controllers.yaml"/>\n')
        f.write('</launch>\n')

def write_moveit_gazebo_launch(save_dir, robot_name):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/gazebo.launch'
    
    with open(file_name, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<launch>\n')
        f.write('  <!-- Gazebo options -->\n')
        f.write('  <arg name="gazebo_gui" default="true" doc="Start Gazebo GUI"/>\n')
        f.write('  <arg name="paused" default="false" doc="Start Gazebo paused"/>\n')
        f.write('  <arg name="world_name" default="worlds/empty.world" doc="Gazebo world file"/>\n')
        f.write('  <arg name="world_pose" default="-x 0 -y 0 -z 0 -R 0 -P 0 -Y 0" doc="Pose to spawn the robot at"/>\n')
        f.write('  <arg name="initial_joint_positions" default="-J Revolute_6 1.8" doc="Initial joint configuration of the robot"/>\n')
        f.write('\n')
        f.write('  <!-- Start Gazebo paused to allow the controllers to pickup the initial pose -->\n')
        f.write('  <include file="$(find gazebo_ros)/launch/empty_world.launch" pass_all_args="true">\n')
        f.write('    <arg name="paused" value="true"/>\n')
        f.write('  </include>\n')
        f.write('\n')
        f.write('  <!-- Set the robot urdf on the parameter server -->\n')
        f.write(f'  <param name="robot_description" textfile="$(find {robot_name})/urdf/{robot_name}.urdf" />\n')
        f.write('\n')
        f.write('  <!-- Unpause the simulation after loading the robot model -->\n')
        f.write('  <arg name="unpause" value="$(eval \'\' if arg(\'paused\') else \'-unpause\')" />\n')
        f.write('\n')
        f.write('  <!-- Spawn the robot in Gazebo -->\n')
        f.write('  <node name="spawn_gazebo_model" pkg="gazebo_ros" type="spawn_model" args="-urdf -param robot_description -model robot $(arg unpause) $(arg world_pose) $(arg initial_joint_positions)" respawn="false" output="screen" />\n')
        f.write('\n')
        f.write('  <!-- Load the controller parameters onto the parameter server -->\n')
        f.write('  <rosparam file="$(find moveit_configs)/config/gazebo_controllers.yaml" />\n')
        f.write('  <include file="$(dirname)/ros_controllers.launch"/>\n')
        f.write('\n')
        f.write('  <!-- Spawn the Gazebo ROS controllers -->\n')
        f.write('  <node name="gazebo_controller_spawner" pkg="controller_manager" type="spawner" respawn="false" output="screen" args="joint_state_controller" />\n')
        f.write('\n')
        f.write('  <!-- Given the published joint states, publish tf for the robot links -->\n')
        f.write('  <node name="robot_state_publisher" pkg="robot_state_publisher" type="robot_state_publisher" respawn="true" output="screen" />\n')
        f.write('</launch>\n')

def write_joystick_control_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/joystick_control.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- See moveit_ros/visualization/doc/joystick.rst for documentation -->\n')
        f.write('  <arg name="dev" default="/dev/input/js0" />\n')
        f.write('\n')
        f.write('  <!-- Launch joy node -->\n')
        f.write('  <node pkg="joy" type="joy_node" name="joy">\n')
        f.write('    <param name="dev" value="$(arg dev)" /> <!-- Customize this to match the location your joystick is plugged in on-->\n')
        f.write('    <param name="deadzone" value="0.2" />\n')
        f.write('    <param name="autorepeat_rate" value="40" />\n')
        f.write('    <param name="coalesce_interval" value="0.025" />\n')
        f.write('  </node>\n')
        f.write('\n')
        f.write('  <!-- Launch python interface -->\n')
        f.write('  <node pkg="moveit_ros_visualization" type="moveit_joy.py" output="screen" name="moveit_joy"/>\n')
        f.write('</launch>\n')

def write_movegroup_launch(save_dir, robot_name):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/move_group.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- GDB Debug Option -->\n')
        f.write('  <arg name="debug" default="false" />\n')
        f.write('  <arg unless="$(arg debug)" name="launch_prefix" value="" />\n')
        f.write('  <arg if="$(arg debug)" name="launch_prefix" value="gdb -x $(dirname)/gdb_settings.gdb --ex run --args" />\n')
        f.write('\n')
        
        f.write('  <!-- Verbose Mode Option -->\n')
        f.write('  <arg name="info" default="$(arg debug)" />\n')
        f.write('  <arg unless="$(arg info)" name="command_args" value="" />\n')
        f.write('  <arg if="$(arg info)" name="command_args" value="--debug" />\n')
        f.write('\n')
        
        f.write('  <!-- move_group settings -->\n')
        f.write('  <arg name="pipeline" default="ompl" />\n')
        f.write('  <arg name="allow_trajectory_execution" default="true"/>\n')
        f.write('  <arg name="moveit_controller_manager" default="simple" />\n')
        f.write('  <arg name="fake_execution_type" default="interpolate"/>\n')
        f.write('  <arg name="max_safe_path_cost" default="1"/>\n')
        f.write('  <arg name="publish_monitored_planning_scene" default="true"/>\n')
        
        f.write('  <arg name="capabilities" default="" />\n')
        f.write('  <arg name="disable_capabilities" default="" />\n')
        f.write('  <!-- load these non-default MoveGroup capabilities (space separated) -->\n')
        f.write('  <!--\n')
        f.write('  <arg name="capabilities" value="\n')
        f.write('                a_package/AwsomeMotionPlanningCapability\n')
        f.write('                another_package/GraspPlanningPipeline\n')
        f.write('                " />\n')
        f.write('  -->\n')
        
        f.write('  <!-- inhibit these default MoveGroup capabilities (space separated) -->\n')
        f.write('  <!--\n')
        f.write('  <arg name="disable_capabilities" value="\n')
        f.write('                move_group/MoveGroupKinematicsService\n')
        f.write('                move_group/ClearOctomapService\n')
        f.write('                " />\n')
        f.write('  -->\n')
        
        f.write('  <arg name="load_robot_description" default="false" />\n')
        f.write('  <!-- load URDF, SRDF and joint_limits configuration -->\n')
        f.write('  <include file="$(dirname)/planning_context.launch">\n')
        f.write('    <arg name="load_robot_description" value="$(arg load_robot_description)" />\n')
        f.write('  </include>\n')
        f.write('\n')
        
        f.write('  <!-- Planning Pipelines -->\n')
        f.write('  <group ns="move_group/planning_pipelines">\n')
        
        # OMPL
        f.write('    <include file="$(dirname)/planning_pipeline.launch.xml">\n')
        f.write('      <arg name="pipeline" value="ompl" />\n')
        f.write('    </include>\n')
        
        # CHOMP        f.write('    <include file="$(dirname)/planning_pipeline.launch.xml">\n')
        f.write('      <arg name="pipeline" value="chomp" />\n')
        f.write('    </include>\n')
        
        # Pilz Industrial Motion
        f.write('    <include file="$(dirname)/planning_pipeline.launch.xml">\n')
        f.write('      <arg name="pipeline" value="pilz_industrial_motion_planner" />\n')
        f.write('    </include>\n')
        
        # Support custom planning pipeline
        f.write('    <include if="$(eval arg(\'pipeline\') not in [\'ompl\', \'chomp\', \'pilz_industrial_motion_planner\'])"\n')
        f.write('             file="$(dirname)/planning_pipeline.launch.xml">\n')
        f.write('      <arg name="pipeline" value="$(arg pipeline)" />\n')
        f.write('    </include>\n')
        
        f.write('  </group>\n')
        f.write('\n')
        
        f.write('  <!-- Trajectory Execution Functionality -->\n')
        f.write('  <include ns="move_group" file="$(dirname)/trajectory_execution.launch.xml" if="$(arg allow_trajectory_execution)">\n')
        f.write('    <arg name="moveit_manage_controllers" value="true" />\n')
        f.write('    <arg name="moveit_controller_manager" value="$(arg moveit_controller_manager)" />\n')
        f.write('    <arg name="fake_execution_type" value="$(arg fake_execution_type)" />\n')
        f.write('  </include>\n')
        f.write('\n')
        
        f.write('  <!-- Sensors Functionality -->\n')
        f.write('  <include ns="move_group" file="$(dirname)/sensor_manager.launch.xml" if="$(arg allow_trajectory_execution)">\n')
        f.write(f'    <arg name="moveit_sensor_manager" value="{robot_name}" />\n')
        f.write('  </include>\n')
        f.write('\n')
        
        f.write('  <!-- Start the actual move_group node/action server -->\n')
        f.write('  <node name="move_group" launch-prefix="$(arg launch_prefix)" pkg="moveit_ros_move_group" type="move_group" respawn="false" output="screen" args="$(arg command_args)">\n')
        f.write('    <!-- Set the display variable, in case OpenGL code is used internally -->\n')
        f.write('    <env name="DISPLAY" value="$(optenv DISPLAY :0)" />\n')
        
        f.write('    <param name="allow_trajectory_execution" value="$(arg allow_trajectory_execution)"/>\n')
        f.write('    <param name="sense_for_plan/max_safe_path_cost" value="$(arg max_safe_path_cost)"/>\n')
        f.write('    <param name="default_planning_pipeline" value="$(arg pipeline)" />\n')
        f.write('    <param name="capabilities" value="$(arg capabilities)" />\n')
        f.write('    <param name="disable_capabilities" value="$(arg disable_capabilities)" />\n')
        
        f.write('    <!-- do not copy dynamics information from /joint_states to internal robot monitoring\n')
        f.write('         default to false, because almost nothing in move_group relies on this information -->\n')
        f.write('    <param name="monitor_dynamics" value="false" />\n')
        
        f.write('    <!-- Publish the planning scene of the physical robot so that rviz plugin can know actual robot -->\n')
        f.write('    <param name="planning_scene_monitor/publish_planning_scene" value="$(arg publish_monitored_planning_scene)" />\n')
        f.write('    <param name="planning_scene_monitor/publish_geometry_updates" value="$(arg publish_monitored_planning_scene)" />\n')
        f.write('    <param name="planning_scene_monitor/publish_state_updates" value="$(arg publish_monitored_planning_scene)" />\n')
        f.write('    <param name="planning_scene_monitor/publish_transforms_updates" value="$(arg publish_monitored_planning_scene)" />\n')
        f.write('  </node>\n')
        
        f.write('</launch>\n')

def write_moveit_rviz_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/moveit_rviz.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <arg name="debug" default="false" />\n')
        f.write('  <arg unless="$(arg debug)" name="launch_prefix" value="" />\n')
        f.write('  <arg if="$(arg debug)" name="launch_prefix" value="gdb --ex run --args" />\n')
        f.write('\n')
        
        f.write('  <arg name="rviz_config" default="$(find moveit_configs)/config/moveit.rviz" />\n')
        f.write('  <arg if="$(eval arg(\'rviz_config\') == \'\')" name="command_args" value="" />\n')
        f.write('  <arg unless="$(eval arg(\'rviz_config\') == \'\')" name="command_args" value="-d $(arg rviz_config)" />\n')
        f.write('\n')
        
        f.write('  <node name="$(anon rviz)" launch-prefix="$(arg launch_prefix)" pkg="rviz" type="rviz" respawn="false"\n')
        f.write('        args="$(arg command_args)" output="screen">\n')
        f.write('  </node>\n')
        
        f.write('</launch>\n')

def write_moveit_rviz(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/config', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/config/moveit.rviz'
    
    with open(file_name, 'w') as f:
        f.write('# This is a default RViz configuration file for MoveIt!\n')
        f.write('# It is automatically generated by the MoveIt configuration generator.\n')
        f.write('# You can customize it to your needs.\n')
        f.write('\n')
        f.write('Panels:\n')
        f.write('  - Class: rviz/Displays\n')
        f.write('    Help Height: 84\n')
        f.write('    Name: Displays\n')
        f.write('    Property Tree Widget:\n')
        f.write('      Expanded:\n')
        f.write('        - /MotionPlanning1\n')
        f.write('      Splitter Ratio: 0.5\n')
        f.write('    Tree Height: 226\n')
        f.write('  - Class: rviz/Help\n')
        f.write('    Name: Help\n')
        f.write('  - Class: rviz/Views\n')
        f.write('    Expanded:\n')
        f.write('      - /Current View1\n')
        f.write('    Name: Views\n')
        f.write('    Splitter Ratio: 0.5\n')
        f.write('Visualization Manager:\n')
        f.write('  Class: ""\n')
        f.write('  Displays:\n')
        f.write('    - Alpha: 0.5\n')
        f.write('      Cell Size: 1\n')
        f.write('      Class: rviz/Grid\n')
        f.write('      Color: 160; 160; 164\n')
        f.write('      Enabled: true\n')
        f.write('      Line Style:\n')
        f.write('        Line Width: 0.03\n')
        f.write('        Value: Lines\n')
        f.write('      Name: Grid\n')
        f.write('      Normal Cell Count: 0\n')
        f.write('      Offset:\n')
        f.write('        X: 0\n')
        f.write('        Y: 0\n')
        f.write('        Z: 0\n')
        f.write('      Plane: XY\n')
        f.write('      Plane Cell Count: 10\n')
        f.write('      Reference Frame: <Fixed Frame>\n')
        f.write('      Value: true\n')
        f.write('    - Class: moveit_rviz_plugin/MotionPlanning\n')
        f.write('      Enabled: true\n')
        f.write('      Name: MotionPlanning\n')
        f.write('      Planned Path:\n')
        f.write('        Links: ~\n')
        f.write('        Loop Animation: true\n')
        f.write('        Robot Alpha: 0.5\n')
        f.write('        Show Robot Collision: false\n')
        f.write('        Show Robot Visual: true\n')
        f.write('        Show Trail: false\n')
        f.write('        State Display Time: 0.05 s\n')
        f.write('        Trajectory Topic: move_group/display_planned_path\n')
        f.write('      Planning Metrics:\n')
        f.write('        Payload: 1\n')
        f.write('        Show Joint Torques: false\n')
        f.write('        Show Manipulability: false\n')
        f.write('        Show Manipulability Index: false\n')
        f.write('        Show Weight Limit: false\n')
        f.write('      Planning Request:\n')
        f.write('        Colliding Link Color: 255; 0; 0\n')
        f.write('        Goal State Alpha: 1\n')
        f.write('        Goal State Color: 250; 128; 0\n')
        f.write('        Interactive Marker Size: 0\n')
        f.write('        Joint Violation Color: 255; 0; 255\n')
        f.write('        Query Goal State: true\n')
        f.write('        Query Start State: false\n')
        f.write('        Show Workspace: false\n')
        f.write('        Start State Alpha: 1\n')
        f.write('        Start State Color: 0; 255; 0\n')
        f.write('      Planning Scene Topic: move_group/monitored_planning_scene\n')
        f.write('      Robot Description: robot_description\n')
        f.write('      Scene Geometry:\n')
        f.write('        Scene Alpha: 1\n')
        f.write('        Show Scene Geometry: true\n')
        f.write('        Voxel Coloring: Z-Axis\n')
        f.write('        Voxel Rendering: Occupied Voxels\n')
        f.write('      Scene Robot:\n')
        f.write('        Attached Body Color: 150; 50; 150\n')
        f.write('        Links: ~\n')
        f.write('        Robot Alpha: 0.5\n')
        f.write('        Show Scene Robot: true\n')
        f.write('      Value: true\n')
        f.write('  Enabled: true\n')
        f.write('  Global Options:\n')
        f.write('    Background Color: 48; 48; 48\n')
        f.write('    Fixed Frame: link_0_1\n')
        f.write('  Name: root\n')
        f.write('  Tools:\n')
        f.write('    - Class: rviz/Interact\n')
        f.write('      Hide Inactive Objects: true\n')
        f.write('    - Class: rviz/MoveCamera\n')
        f.write('    - Class: rviz/Select\n')
        f.write('  Value: true\n')
        f.write('  Views:\n')
        f.write('    Current:\n')
        f.write('      Class: rviz/Orbit\n')
        f.write('      Distance: 2.0\n')
        f.write('      Enable Stereo Rendering:\n')
        f.write('        Stereo Eye Separation: 0.06\n')
        f.write('        Stereo Focal Distance: 1\n')
        f.write('        Swap Stereo Eyes: false\n')
        f.write('        Value: false\n')
        f.write('      Field of View: 0.75\n')
        f.write('      Focal Point:\n')
        f.write('        X: -0.1\n')
        f.write('        Y: 0.25\n')
        f.write('        Z: 0.30\n')
        f.write('      Focal Shape Fixed Size: true\n')
        f.write('      Focal Shape Size: 0.05\n')
        f.write('      Invert Z Axis: false\n')
        f.write('      Name: Current View\n')
        f.write('      Near Clip Distance: 0.01\n')
        f.write('      Pitch: 0.5\n')
        f.write('      Target Frame: link_0_1\n')
        f.write('      Yaw: -0.6232355833053589\n')
        f.write('    Saved: ~\n')
        f.write('Window Geometry:\n')
        f.write('  Displays:\n')
        f.write('    collapsed: false\n')
        f.write('  Height: 848\n')
        f.write('  Help:\n')
        f.write('    collapsed: false\n')
        f.write('  Hide Left Dock: false\n')
        f.write('  Hide Right Dock: false\n')
        f.write('  MotionPlanning:\n')
        f.write('    collapsed: false\n')
        f.write('  MotionPlanning - Trajectory Slider:\n')
        f.write('    collapsed: false\n')
        f.write('  QMainWindow State: 000000ff00000000fd0000000100000000000001f0000002f6fc0200000007fb000000100044006900730070006c006100790073010000003d00000173000000c900fffffffb0000000800480065006c00700000000342000000bb0000006e00fffffffb0000000a00560069006500770073000000010c000000a4000000a400fffffffb0000000c00430061006d00650072006100000002ff000001610000000000000000fb0000001e004d006f00740069006f006e00200050006c0061006e006e0069006e00670100000374000001890000000000000000fb00000044004d006f00740069006f006e0050006c0061006e006e0069006e00670020002d0020005400720061006a006500630074006f0072007900200053006c00690064006500720000000000ffffffff0000001600000016fb0000001c004d006f00740069006f006e0050006c0061006e006e0069006e006701000001b60000017d0000017d00ffffff00000315000002f600000001000000020000000100000002fc0000000100000002000000010000000a0054006f006f006c00730100000000ffffffff00000000000000\n')
        f.write('  Views:\n')
        f.write('    collapsed: false\n')
        f.write('  Width: 1291\n')
        f.write('  X: 454\n')
        f.write('  Y: 25\n')

def write_myrobot_moveit_sensor_manager_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/myrobot_moveit_sensor_manager.launch.xml'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n\n')
        f.write('</launch>\n')

def write_ompl_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/ompl_planning_pipeline.launch.xml'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- The request adapters (plugins) used when planning with OMPL. ORDER MATTERS! -->\n')
        f.write('  <arg name="planning_adapters"\n')
        f.write('       default="default_planner_request_adapters/LimitMaxCartesianLinkSpeed\n')
        f.write('                default_planner_request_adapters/AddTimeParameterization\n')
        f.write('                default_planner_request_adapters/ResolveConstraintFrames\n')
        f.write('                default_planner_request_adapters/FixWorkspaceBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateCollision\n')
        f.write('                default_planner_request_adapters/FixStartStatePathConstraints" />\n')
        f.write('\n')
        f.write('  <arg name="start_state_max_bounds_error" default="0.1" />\n')
        f.write('  <arg name="jiggle_fraction" default="0.05" />\n')
        f.write('\n')
        f.write('  <param name="planning_plugin" value="ompl_interface/OMPLPlanner" />\n')
        f.write('  <param name="request_adapters" value="$(arg planning_adapters)" />\n')
        f.write('  <param name="start_state_max_bounds_error" value="$(arg start_state_max_bounds_error)" />\n')
        f.write('  <param name="jiggle_fraction" value="$(arg jiggle_fraction)" />\n')
        f.write('\n')
        f.write('  <rosparam command="load" file="$(find moveit_configs)/config/ompl_planning.yaml"/>\n')
        f.write('</launch>\n')

def write_ompl_chomp_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/ompl_chomp_planning_pipeline.launch.xml'
   
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- load OMPL planning pipeline, but add the CHOMP planning adapter. -->\n')
        f.write('  <include file="$(find moveit_configs)/launch/ompl_planning_pipeline.launch.xml">\n')
        f.write('    <arg name="planning_adapters"\n')
        f.write('         default="default_planner_request_adapters/LimitMaxCartesianLinkSpeed\n')
        f.write('                  default_planner_request_adapters/AddTimeParameterization\n')
        f.write('                  default_planner_request_adapters/FixWorkspaceBounds\n')
        f.write('                  default_planner_request_adapters/FixStartStateBounds\n')
        f.write('                  default_planner_request_adapters/FixStartStateCollision\n')
        f.write('                  default_planner_request_adapters/FixStartStatePathConstraints\n')
        f.write('                  chomp/OptimizerAdapter"\n')
        f.write('    />\n')
        f.write('  </include>\n')
        f.write('\n')
        f.write('  <!-- load chomp config -->\n')
        f.write('  <rosparam command="load" file="$(find moveit_configs)/config/chomp_planning.yaml" />\n')
        f.write('\n')
        f.write('  <!-- override trajectory_initialization_method: Use OMPL-generated trajectory -->\n')
        f.write('  <param name="trajectory_initialization_method" value="fillTrajectory"/>\n')
        f.write('</launch>\n')

def write_pilz_industrial_motion_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/pilz_industrial_motion_planning_pipeline.launch.xml'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- The request adapters (plugins) used when planning. ORDER MATTERS! -->\n')
        f.write('  <arg name="planning_adapters" default="" />\n')
        f.write('\n')
        f.write('  <param name="planning_plugin" value="pilz_industrial_motion_planner::CommandPlanner" />\n')
        f.write('  <param name="request_adapters" value="$(arg planning_adapters)" />\n')
        f.write('\n')
        f.write('  <!-- Define default planner (for all groups) -->\n')
        f.write('  <param name="default_planner_config" value="PTP" />\n')
        f.write('\n')
        f.write('  <!-- MoveGroup capabilities to load for this pipeline, append sequence capability -->\n')
        f.write('  <param name="capabilities" value="pilz_industrial_motion_planner/MoveGroupSequenceAction\n')
        f.write('                                    pilz_industrial_motion_planner/MoveGroupSequenceService" />\n')
        f.write('</launch>\n')

def write_planning_context_launch(save_dir, robot_name):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/planning_context.launch'
    
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- By default we do not overwrite the URDF. Change the following to true to change the default behavior -->\n')
        f.write('  <arg name="load_robot_description" default="false"/>\n')
        f.write('\n')
        f.write('  <!-- The name of the parameter under which the URDF is loaded -->\n')
        f.write('  <arg name="robot_description" default="robot_description"/>\n')
        f.write('\n')
        f.write('  <!-- Load universal robot description format (URDF) -->\n')
        f.write(f'  <param if="$(arg load_robot_description)" name="$(arg robot_description)" textfile="$(find {robot_name})/urdf/{robot_name}.urdf"/>\n')
        f.write('\n')
        f.write('  <!-- The semantic description that corresponds to the URDF -->\n')
        f.write(f'  <param name="$(arg robot_description)_semantic" textfile="$(find moveit_configs)/config/{robot_name}.srdf" />\n')
        f.write('\n')
        f.write('  <!-- Load updated joint limits (override information from URDF) -->\n')
        f.write('  <group ns="$(arg robot_description)_planning">\n')
        f.write('    <rosparam command="load" file="$(find moveit_configs)/config/joint_limits.yaml"/>\n')
        f.write('    <rosparam command="load" file="$(find moveit_configs)/config/cartesian_limits.yaml"/>\n')
        f.write('  </group>\n')
        f.write('\n')
        f.write('  <!-- Load default settings for kinematics; these settings are overridden by settings in a node\'s namespace -->\n')
        f.write('  <group ns="$(arg robot_description)_kinematics">\n')
        f.write('    <rosparam command="load" file="$(find moveit_configs)/config/kinematics.yaml"/>\n')
        f.write('  </group>\n')
        f.write('</launch>\n')

def write_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/planning_pipeline.launch.xml'
    """<launch>

  <!-- This file makes it easy to include different planning pipelines;
       It is assumed that all planning pipelines are named XXX_planning_pipeline.launch  -->

  <arg name="pipeline" default="ompl" />

  <include ns="$(arg pipeline)" file="$(dirname)/$(arg pipeline)_planning_pipeline.launch.xml" />

</launch>
"""
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- This file makes it easy to include different planning pipelines; -->\n')
        f.write('  <arg name="pipeline" default="ompl" />\n')
        f.write('\n')
        f.write('  <include ns="$(arg pipeline)" file="$(dirname)/$(arg pipeline)_planning_pipeline.launch.xml" />\n')
        f.write('</launch>\n')

def write_ros_control_moveit_controller_manager_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/ros_control_moveit_controller_manager.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- Define MoveIt controller manager plugin -->\n')
        f.write('  <param name="moveit_controller_manager" value="moveit_ros_control_interface::MoveItControllerManager" />\n')
        f.write('</launch>\n')

def write_ros_controllers_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/ros_controllers.launch'
    with open(file_name, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<launch>\n\n')
        f.write('  <!-- Load joint controller configurations from YAML file to parameter server -->\n')
        f.write('  <rosparam file="$(find moveit_configs)/config/ros_controllers.yaml" command="load"/>\n\n')
        f.write('  <!-- Load the controllers -->\n')
        f.write('  <node name="controller_spawner" pkg="controller_manager" type="spawner" respawn="false"\n')
        f.write('    output="screen" args="my_arm_controller my_effector_controller my_robot_top_group_controller "/>\n\n')
        f.write('</launch>\n')

def write_run_benchmark_ompl_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/run_benchmark_ompl.launch'
    with open(file_name, 'w') as f:
        f.write('<launch>\n\n')
        f.write('  <!-- This argument must specify the list of .cfg files to process for benchmarking -->\n')
        f.write('  <arg name="cfg" />\n\n')
        f.write('  <!-- Load URDF -->\n')
        f.write('  <include file="$(dirname)/planning_context.launch">\n')
        f.write('    <arg name="load_robot_description" value="true"/>\n')
        f.write('  </include>\n\n')
        f.write('  <!-- Start the database -->\n')
        f.write('  <include file="$(dirname)/warehouse.launch">\n')
        f.write('    <arg name="moveit_warehouse_database_path" value="moveit_ompl_benchmark_warehouse"/>\n')
        f.write('  </include>\n\n')
        f.write('  <!-- Start Benchmark Executable -->\n')
        f.write('  <node name="$(anon moveit_benchmark)" pkg="moveit_ros_benchmarks" type="moveit_run_benchmark" args="$(arg cfg) --benchmark-planners" respawn="false" output="screen">\n')
        f.write('    <rosparam command="load" file="$(find moveit_configs)/config/ompl_planning.yaml"/>\n')
        f.write('  </node>\n\n')
        f.write('</launch>\n')

def write_sensor_manager_launch_xml(save_dir, robot_name):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/sensor_manager.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n\n')
        f.write('  <!-- This file makes it easy to include the settings for sensor managers -->\n\n')
        f.write('  <!-- Params for 3D sensors config -->\n')
        f.write('  <rosparam command="load" file="$(find moveit_configs)/config/sensors_3d.yaml" />\n\n')
        f.write('  <!-- Params for the octomap monitor -->\n')
        f.write('  <!--  <param name="octomap_frame" type="string" value="some frame in which the robot moves" /> -->\n')
        f.write('  <param name="octomap_resolution" type="double" value="0.025" />\n')
        f.write('  <param name="max_range" type="double" value="5.0" />\n\n')
        f.write('  <!-- Load the robot specific sensor manager; this sets the moveit_sensor_manager ROS parameter -->\n')
        f.write(f'  <arg name="moveit_sensor_manager" default="{robot_name}" />\n')
        f.write('  <include file="$(dirname)/$(arg moveit_sensor_manager)_moveit_sensor_manager.launch.xml" />\n\n')
        f.write('</launch>\n')

def write_setup_assistant_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/setup_assistant.launch'
    with open(file_name, 'w') as f:
        f.write('<!-- Re-launch the MoveIt Setup Assistant with this configuration package already loaded -->\n')
        f.write('<launch>\n\n')
        f.write('  <!-- Debug Info -->\n')
        f.write('  <arg name="debug" default="false" />\n')
        f.write('  <arg unless="$(arg debug)" name="launch_prefix" value="" />\n')
        f.write('  <arg     if="$(arg debug)" name="launch_prefix" value="gdb --ex run --args" />\n\n')
        f.write('  <!-- Run -->\n')
        f.write('  <node pkg="moveit_setup_assistant" type="moveit_setup_assistant" name="moveit_setup_assistant"\n')
        f.write('        args="--config_pkg=moveit_configs"\n')
        f.write('        launch-prefix="$(arg launch_prefix)"\n')
        f.write('        required="true"\n')
        f.write('        output="screen" />\n\n')
        f.write('</launch>\n')

def write_simple_moveit_controller_manager_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/simple_moveit_controller_manager.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- Define the MoveIt controller manager plugin to use for trajectory execution -->\n')
        f.write('  <param name="moveit_controller_manager" value="moveit_simple_controller_manager/MoveItSimpleControllerManager" />\n\n')
        f.write('  <!-- Load controller list to the parameter server -->\n')
        f.write('  <rosparam file="$(find moveit_configs)/config/simple_moveit_controllers.yaml" />\n')
        f.write('  <rosparam file="$(find moveit_configs)/config/ros_controllers.yaml" />\n')
        f.write('</launch>\n')

def write_stomp_planning_pipeline_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/stomp_planning_pipeline.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- Stomp Plugin for MoveIt -->\n')
        f.write('  <arg name="planning_plugin" value="stomp_moveit/StompPlannerManager" />\n\n')
        f.write('  <arg name="start_state_max_bounds_error" value="0.1" />\n')
        f.write('  <arg name="jiggle_fraction" value="0.05" />\n')
        f.write('  <!-- The request adapters (plugins) used when planning. ORDER MATTERS! -->\n')
        f.write('  <arg name="planning_adapters"\n')
        f.write('       default="default_planner_request_adapters/LimitMaxCartesianLinkSpeed\n')
        f.write('                default_planner_request_adapters/AddTimeParameterization\n')
        f.write('                default_planner_request_adapters/FixWorkspaceBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateBounds\n')
        f.write('                default_planner_request_adapters/FixStartStateCollision\n')
        f.write('                default_planner_request_adapters/FixStartStatePathConstraints" />\n\n')
        f.write('  <param name="planning_plugin" value="$(arg planning_plugin)" />\n')
        f.write('  <param name="request_adapters" value="$(arg planning_adapters)" />\n')
        f.write('  <param name="start_state_max_bounds_error" value="$(arg start_state_max_bounds_error)" />\n')
        f.write('  <param name="jiggle_fraction" value="$(arg jiggle_fraction)" />\n\n')
        f.write('  <rosparam command="load" file="$(find moveit_configs)/config/stomp_planning.yaml"/>\n')
        f.write('</launch>\n')

def write_trajectory_execution_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/trajectory_execution.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- This file summarizes all settings required for trajectory execution  -->\n\n')
        f.write('  <!-- Define moveit controller manager plugin: fake, simple, or ros_control -->\n')
        f.write('  <arg name="moveit_controller_manager" />\n')
        f.write('  <arg name="fake_execution_type" default="interpolate" />\n\n')
        f.write('  <!-- Flag indicating whether MoveIt is allowed to load/unload  or switch controllers -->\n')
        f.write('  <arg name="moveit_manage_controllers" default="true"/>\n')
        f.write('  <param name="moveit_manage_controllers" value="$(arg moveit_manage_controllers)"/>\n\n')
        f.write('  <!-- When determining the expected duration of a trajectory, this multiplicative factor is applied to get the allowed duration of execution -->\n')
        f.write('  <param name="trajectory_execution/allowed_execution_duration_scaling" value="1.2"/> <!-- default 1.2 -->\n')
        f.write('  <!-- Allow more than the expected execution time before triggering a trajectory cancel (applied after scaling) -->\n')
        f.write('  <param name="trajectory_execution/allowed_goal_duration_margin" value="0.5"/> <!-- default 0.5 -->\n')
        f.write('  <!-- Allowed joint-value tolerance for validation that trajectory\'s first point matches current robot state -->\n')
        f.write('  <param name="trajectory_execution/allowed_start_tolerance" value="0.01"/> <!-- default 0.01 -->\n\n')
        f.write('  <!-- We use pass_all_args=true here to pass fake_execution_type, which is required by fake controllers, but not by real-robot controllers.\n')
        f.write('       As real-robot controller_manager.launch files shouldn\'t be required to define this argument, we use the trick of passing all args. -->\n')
        f.write('  <include file="$(dirname)/$(arg moveit_controller_manager)_moveit_controller_manager.launch.xml" pass_all_args="true" />\n\n')
        f.write('</launch>\n')

def write_warehouse_settings_launch_xml(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/warehouse_settings.launch.xml'
    with open(file_name, 'w') as f:
        f.write('<launch>\n')
        f.write('  <!-- Set the parameters for the warehouse and run the mongodb server. -->\n\n')
        f.write('  <!-- The default DB port for moveit (not default MongoDB port to avoid potential conflicts) -->\n')
        f.write('  <arg name="moveit_warehouse_port" default="33829" />\n\n')
        f.write('  <!-- The default DB host for moveit -->\n')
        f.write('  <arg name="moveit_warehouse_host" default="localhost" />\n\n')
        f.write('  <!-- Set parameters for the warehouse -->\n')
        f.write('  <param name="warehouse_port" value="$(arg moveit_warehouse_port)"/>\n')
        f.write('  <param name="warehouse_host" value="$(arg moveit_warehouse_host)"/>\n')
        f.write('  <param name="warehouse_exec" value="mongod" />\n')
        f.write('  <param name="warehouse_plugin" value="warehouse_ros_mongo::MongoDatabaseConnection" />\n\n')
        f.write('</launch>\n')

def write_warehouse_launch(save_dir):
    try: os.makedirs(save_dir + '/moveit_configs/launch', exist_ok=True)
    except: pass
    file_name = save_dir + '/moveit_configs/launch/warehouse.launch'
    with open(file_name, 'w') as f:
        f.write('<launch>\n\n')
        f.write('  <!-- The path to the database must be specified -->\n')
        f.write('  <arg name="moveit_warehouse_database_path" />\n\n')
        f.write('  <!-- Load warehouse parameters -->\n')
        f.write('  <include file="$(dirname)/warehouse_settings.launch.xml" />\n\n')
        f.write('  <!-- Run the DB server -->\n')
        f.write('  <node name="$(anon mongo_wrapper_ros)" cwd="ROS_HOME" type="mongo_wrapper_ros.py" pkg="warehouse_ros_mongo">\n')
        f.write('    <param name="overwrite" value="false"/>\n')
        f.write('    <param name="database_path" value="$(arg moveit_warehouse_database_path)" />\n')
        f.write('  </node>\n\n')
        f.write('</launch>\n')

def write_moveit_config_cmake(save_dir):
    """
    write CMakeLists.txt file "save_dir/moveit_configs/CMakeLists.txt"
    
    
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    """
    try: os.makedirs(save_dir + '/moveit_configs', exist_ok=True)
    except: pass
    
    file_name = save_dir + '/moveit_configs/CMakeLists.txt'
    
    with open(file_name, 'w') as f:
        f.write('cmake_minimum_required(VERSION 3.5)\n')
        f.write('project(moveit_configs)\n\n')
        f.write('find_package(catkin REQUIRED)\n\n')
        f.write('catkin_package()\n\n')
        f.write('install(DIRECTORY launch DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}\n')
        f.write('  PATTERN "setup_assistant.launch" EXCLUDE)\n')
        f.write('install(DIRECTORY config DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})\n')

def write_moveit_config_package_xml(save_dir, robot_name):
    """
    write package.xml file "save_dir/moveit_configs/package.xml"
    Parameter
    ---------
    save_dir: str
        path of the repository to save
    robot_name: str
        name of the robot
    """
    try: os.makedirs(save_dir + '/moveit_configs', exist_ok=True)
    except: pass
    
    file_name = save_dir + '/moveit_configs/package.xml'
    
    with open(file_name, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<package>\n\n')
        f.write('  <name>moveit_configs</name>\n')
        f.write('  <version>0.3.0</version>\n')
        f.write('  <description>An automatically generated package with all the configuration and launch files for using the {} with the MoveIt Motion Planning Framework</description>\n'.format(robot_name))
        f.write('  <author email="felix.wolff@tu-dortmund.de">Felix Wolff</author>\n')
        f.write('  <maintainer email="felix.wolff@tu-dortmund.de">Felix Wolff</maintainer>\n\n')
        f.write('  <license>BSD</license>\n\n')
        f.write('  <url type="website">http://moveit.ros.org/</url>\n')
        f.write('  <url type="bugtracker">https://github.com/moveit/moveit/issues</url>\n')
        f.write('  <url type="repository">https://github.com/moveit/moveit</url>\n\n')
        f.write('  <buildtool_depend>catkin</buildtool_depend>\n\n')
        f.write('  <run_depend>moveit_ros_move_group</run_depend>\n')
        f.write('  <run_depend>moveit_fake_controller_manager</run_depend>\n')
        f.write('  <run_depend>moveit_kinematics</run_depend>\n')
        f.write('  <run_depend>moveit_planners</run_depend>\n')
        f.write('  <run_depend>moveit_ros_visualization</run_depend>\n')
        f.write('  <run_depend>moveit_setup_assistant</run_depend>\n')
        f.write('  <run_depend>moveit_simple_controller_manager</run_depend>\n')
        f.write('  <run_depend>joint_state_publisher</run_depend>\n')
        f.write('  <run_depend>joint_state_publisher_gui</run_depend>\n')
        f.write('  <run_depend>robot_state_publisher</run_depend>\n')
        f.write('  <run_depend>rviz</run_depend>\n')
        f.write('  <run_depend>tf2_ros</run_depend>\n')
        f.write('  <run_depend>xacro</run_depend>\n')
        # The next 2 packages are required for the gazebo simulation.
        # We don't include them by default to prevent installing gazebo and all its dependencies.
        # f.write('  <run_depend>joint_trajectory_controller</run_depend>\n')
        # f.write('  <run_depend>gazebo_ros_control</run_depend>\n')
        # This package is referenced in the warehouse launch files, but does not build out of the box at the moment. Commented the dependency until this works.
        # f.write('  <run_depend>warehouse_ros_mongo</run_depend>\n')
        f.write(f'  <run_depend>{robot_name}</run_depend>\n\n')
        f.write('</package>\n')

def post_files_to_backend(save_dir, robot_name):
    """ Post the files in the save_dir to the backend server.
    
    Parameters
    ----------
    save_dir: str
        path of folder containing the files to be posted.
    """
    
    zipped_files = shutil.make_archive(save_dir + f'/{robot_name}_files', 'zip', save_dir)
    with open(zipped_files, 'rb') as f:
        files = {'file': (f'{robot_name}_files', f, 'application/zip')}
        req = urllib.request.Request('http://127.0.1:8000/bo/store-mp-files', files)
        response = urllib.request.urlopen(req)
    return response

    
def remove_temporary_files(save_dir):
    """ Remove the temporary files created during the export process.
    
    Parameters
    ----------
    save_dir: str
        path of folder containing the files to be removed.
    """
    try:
        shutil.rmtree(save_dir)
    except Exception as e:
        print(f"Error removing temporary files: {e}")

def write_yaml(package_name, robot_name, save_dir, joints_dict):
    """
    write yaml file "save_dir/launch/controller.yaml"
    
    
    Parameter
    ---------
    robot_name: str
        name of the robot
    save_dir: str
        path of the repository to save
    joints_dict: dict
        information of the joints
    """
    try: os.makedirs(save_dir + '/launch')
    except: pass 

    controller_name = robot_name + '_controller'
    file_name = save_dir + '/launch/controller.yaml'
    with open(file_name, 'w') as f:
        f.write(controller_name + ':\n')
        # joint_state_controller
        f.write('  # Publish all joint states -----------------------------------\n')
        f.write('  joint_state_controller:\n')
        f.write('    type: joint_state_controller/JointStateController\n')  
        f.write('    publish_rate: 50\n\n')
        # position_controllers
        f.write('  # Position Controllers --------------------------------------\n')
        for joint in joints_dict:
            joint_type = joints_dict[joint]['type']
            if joint_type != 'fixed':
                f.write('  ' + joint + '_position_controller:\n')
                f.write('    type: effort_controllers/JointPositionController\n')
                f.write('    joint: '+ joint + '\n')
                f.write('    pid: {p: 100.0, i: 0.01, d: 10.0}\n')

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
    futil.log(f"{CMD_NAME} Command Created Event")

    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )
    

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

    load_project_taxonomy_to_config()
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
            ui.messageBox('No active Fusion design', title)
            return
    
    # TODO inject urdf exporter here
    success_msg = 'Started export to urdf'
    title = 'Fusion to urdf export'
    msg = success_msg
    ui.messageBox(
        msg,
        title,
        adsk.core.MessageBoxButtonTypes.OKCancelButtonType
    )

    root = design.rootComponent  # root component 
    components = design.allComponents

     # set the names        
    robot_name = root.name.split()[0]
    package_name = robot_name
    
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
    
    save_dir = export_path + '/' + package_name
    
    try: os.makedirs(save_dir)
    except: pass  

    package_dir = os.path.abspath(os.path.dirname(__file__)) + '/package/'
    
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
    # Generate URDF
    export_stl(design, save_dir, root, robot_name)

    # TODO MOVE ALL OF THIS TO THE BACKEND AND ONLY POST THE FOLLOWING DATA
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
    req = urllib.request.Request("http://127.0.0.1:8000/bo/store-mp-files")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Content-Length", len(payload))
    response = urllib.request.urlopen(req, payload)
    print(response.read().decode())
        

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



