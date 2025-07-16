import mimetypes
import os
import zipfile
import sys
import docker
from collections import defaultdict
from datetime import datetime
from timeit import default_timer as timer

from cls_cad_backend.database.commands import (
    get_all_projects_in_results,
    get_all_result_ids_for_project,
    get_result_for_id_in_project,
    get_taxonomy_for_project,
    upsert_part,
    upsert_result,
    upsert_taxonomy,
    init_database
)
from cls_cad_backend.repository_builder import RepositoryBuilder, wrapped_counted_types
from cls_cad_backend.responses import FastResponse
from cls_cad_backend.schemas import PartInf, SynthesisRequestInf, TaxonomyInf, StoreDataRequest
from cls_cad_backend.util.hrid import generate_id
from cls_cad_backend.util.json_operations import (
    invert_taxonomy,
    postprocess,
    suffix_and_merge_taxonomy,
)
from cls_cad_backend.util.mp_file_writers import *
from cls_cad_backend.util.BOStateMachine import SkoptOptimizer
from clsp import (
    Constructor,
    FiniteCombinatoryLogic,
    Subtypes,
    Type,
    enumerate_terms,
    interpret_term,
)
from clsp.types import Literal, Omega
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTasks
from starlette.staticfiles import StaticFiles


init_database()

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app = FastAPI(title="CLS-CAD-BACKEND (Cyberphysical System Synthesis Backend)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True),
    name="static",
)
cache = {}
# anzahl motoren -> Dynamixel 0-7
# axisrotaryjointintent -> 0-7 -> remove for now since its difficult to find valid configurations
# 40mm -> 0-5
search_space = [(0,7),(0,5)]
state_machine = SkoptOptimizer(search_space)

@app.post("/submit/part")
async def save_part(
    payload: PartInf,
) -> str:
    """
    Takes a part payload in JSON form and inserts it into the database as is. It is
    indexed by a unique ID, usually the Fusion 360 file identifier.

    :param payload: The payload containing project, folder and part ids, as well as type
        information.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    upsert_part(payload.model_dump(by_alias=True))
    print(payload.model_dump(by_alias=True))
    return "OK"


@app.post("/bo/{project_id}/{experiment_id}/initialize")
async def initialize_bo(
    project_id: str,
    experiment_id: str,
):
    """
    Initializes the state machine for a specific project and experiment id.

    :param project_id: The project id for which the state machine should be initialized.
    :param experiment_id: The experiment id for which the state machine should be
        initialized.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    return "OK"

@app.get("/bo/{project_id}/{experiment_id}/optimal-vector")
async def optimal_vector(
    project_id: str,
    experiment_id: str,
):
    """
    Retrieves the current optimal vector from the optimizer for a specific project and
    experiment id.

    :param project_id: The project id for which the optimal vector should be retrieved.
    :param experiment_id: The experiment id for which the optimal vector should be
        retrieved.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    return "OK"

@app.post("/bo/store-mp-files")
async def store_mp_files(
    payload: StoreDataRequest
):
    """
    Stores the motion planning files.

    :param files: The files to be stored.
    :param form: Form data containing the relative file paths.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    joints_dict = payload.joints_dict
    links_xyz_dict = payload.links_xyz_dict
    inertial_dict = payload.inertial_dict
    package_name = payload.package_name
    robot_name = payload.robot_name
    save_dir = payload.save_dir
    export_path = payload.export_path

    joints_dict = {
        key.replace(" ", "_"): value
        for key, value in joints_dict.items()
    }

    write_urdf(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
    write_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
    write_materials_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
    write_transmissions_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
    write_gazebo_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
    write_display_launch(package_name, robot_name, save_dir)
    write_gazebo_launch(package_name, robot_name, save_dir)
    write_control_launch(package_name, robot_name, save_dir, joints_dict)
    write_yaml(package_name, robot_name, save_dir, joints_dict)


    # create package files
    setup_cmakelists(save_dir, package_name, robot_name)
    setup_package_xml(save_dir, package_name, robot_name)

    # Generate STl files        
    # copy_occs(root)
    # export_stl(design, save_dir, root, robot_name)

    # create moveit_configs
    write_cartesian_limits_yaml(export_path)
    write_chomp_planning_yaml(export_path)
    write_fake_controllers_yaml(package_name, robot_name, export_path, joints_dict)
    write_gazebo_controllers_yaml(export_path)
    write_joint_limits_yaml(package_name, robot_name, export_path, joints_dict)
    write_kinematics_yaml(export_path)
    write_srdf(package_name, robot_name, export_path, joints_dict, links_xyz_dict)
    write_ompl_planning_yaml(export_path)
    write_ros_controllers_yaml(package_name, robot_name, export_path, joints_dict)
    write_sensors_3d_yaml(export_path)
    write_simple_moveit_controllers_yaml(package_name, robot_name, export_path, joints_dict)
    # stomp planning yaml IGNORE STOMP PLANNING PIPELINE FOR NOW

    # write launch files
    write_chomp_planning_pipeline_launch_xml(export_path)
    write_default_warehouse_db_launch(export_path)
    write_demo_gazebo_launch(export_path)
    write_demo_launch(export_path)
    write_fake_moveit_controller_manager_launch_xml(export_path)
    write_moveit_gazebo_launch(export_path, robot_name)
    write_joystick_control_launch(export_path)
    write_movegroup_launch(export_path, robot_name)
    write_moveit_rviz_launch(export_path)
    write_moveit_rviz(export_path)
    write_myrobot_moveit_sensor_manager_launch_xml(export_path, robot_name)
    write_ompl_planning_pipeline_launch_xml(export_path)
    write_ompl_chomp_planning_pipeline_launch_xml(export_path)
    write_pilz_industrial_motion_planning_pipeline_launch_xml(export_path)
    write_planning_context_launch(export_path, robot_name)
    write_planning_pipeline_launch_xml(export_path)
    write_ros_control_moveit_controller_manager_launch_xml(export_path)
    write_ros_controllers_launch(export_path)
    write_run_benchmark_ompl_launch(export_path)
    write_sensor_manager_launch_xml(export_path, robot_name)
    write_setup_assistant_launch(export_path)
    write_simple_moveit_controller_manager_launch_xml(export_path)
    write_stomp_planning_pipeline_launch_xml(export_path)
    write_trajectory_execution_launch_xml(export_path)
    write_warehouse_settings_launch_xml(export_path)
    write_warehouse_launch(export_path)
    write_moveit_config_cmake(export_path)
    write_moveit_config_package_xml(export_path, robot_name)
    # EVERYTHING BELOW IS COMMENTED OUT FOR NOW
    """# mount the files inside tmp directory to the ros container using sys calls
    client = docker.from_env()
    docker_image_name = "my_ros_noetic_image:latest"
    local_src_path = export_path
    container_src_path = "/ros_ws/src"
    try:
        client.images.get("my_ros_noetic_image:latest")
    except docker.errors.ImageNotFound:
        print("Docker image not found, building...")
        docker_image_name = "my_ros_noetic_image:latest"
        build_context = os.path.abspath("./applications/cls-cad-ros-container")
        client.images.build(
            path=build_context,
            tag=docker_image_name,
            rm=True,
            dockerfile='Dockerfile'
        )
    docker_run_options = {
        'name': 'motion_planning_container',
        'mounts': [
            {
                'type': 'bind',
                'source': local_src_path + "/moveit_configs",
                'target': container_src_path + "/moveit_configs",
                
            },
            {
                'type': 'bind',
                'source': local_src_path + f"/{robot_name}",
                'target': container_src_path + f"/{robot_name}",
            }
        ],
        'detach': True,
        'command': 'bash -i',
        'tty': True,}
    # docker build -t my_ros_noetic_image:latest ../../cls-cad-ros-container
    # docker run -it --rm --name motion_planning_container my_ros_noetic_image:latest 
    # -v /Users/felix.wolff/Desktop/ma-dump/export-new/moveit_configs:/ros_ws/src/moveit_configs
    # -v /Users/felix.wolff/Desktop/ma-dump/export-new/my_robot:/ros_ws/src/my_robot
    # docker cp /Users/felix.wolff/Desktop/ma-dump/export-new/moveit_configs motion_planning_container:/ros_ws/src/
    try:
        container = client.containers.run(
            "my_ros_noetic_image:latest",
            **docker_run_options
        )
    except docker.errors.ContainerError as e:
        print(f"Container error: {e}")
        return {"error": str(e)}
    bash_command = 'bash'
    source_prefix = "source /opt/ros/noetic/setup.bash && source /ros_ws/devel/setup.bash"
    catkin_make_command = "catkin_make"
    roslaunch_command = "roslaunch moveit_configs demo.launch"
    cd_to_motion_planning_command = "cd src/motion_planning && python3 add_box.py && python3 move_group_2.py"
    add_box_command = 'python3 add_box.py'
    move_group_command = 'python3 move_group_2.py'
    cat_result_command = 'cd src/motion_planning && cat total_time.txt'

    try:
        #bash_command_result = container.exec_run(bash_command,detach=True, tty=True)
        #print(f"Bash command result: {bash_command_result.output.decode('utf-8')}")
        catkin_make_result = container.exec_run(f"bash -c '{source_prefix} && {catkin_make_command}'", tty=True)
        print(f"Catkin make result: {catkin_make_result.output.decode('utf-8')}")
        roslaunch_result = container.exec_run(f"bash -c '{source_prefix} && {roslaunch_command}'", stream=True)
        # check for "You can start planning now!" in next(roslaunch_result.output.decode('utf-8'))
        while True:
            try:
                line = next(roslaunch_result.output)
                if "You can start planning now!" in line.decode('utf-8'):
                    print("ROS launch successful, starting motion planning commands...")
                    break
            except StopIteration:
                break
        cd_to_motion_planning_command_result = container.exec_run(f"bash -c '{source_prefix} && {cd_to_motion_planning_command}'", stream=True)
        # check for StopIteration in next(cd_to_motion_planning_command_result.output.decode('utf-8'))
        while True:
            try:
                line = next(cd_to_motion_planning_command_result.output)
                print(line.decode('utf-8'))
            except StopIteration:
                break
    
        cat_result = container.exec_run(f"bash -c '{source_prefix} && {cat_result_command}'", tty=True)
        result = cat_result.output.decode('utf-8').strip()
        print(f"Cat result: {result}")
    except docker.errors.ContainerError as e:
        print(f"Error executing command in container: {e}")
        return {"error": str(e)}
    container.stop()
    container.remove()"""
    # EVERYTHING ABOVE IS COMMENTED OUT FOR NOW


    # TODO: REMOVE THIS SIMULATION PART
    result = "313.09,[1,0,1,1,0,0,1,0]"  # Simulated result for testing purposes
    
    
    """print(docker_build(docker_image_name, dockerfile_dir='../../cls-cad-ros-container'))
    print(docker_run(docker_image_name, local_src_path, container_src_path))
    print(exec_commands(docker_image_name, 'roslaunch moveit_configs demo.launch'))
    print(exec_commands(docker_image_name, 'cd /src/motion_planning'))
    print(exec_commands(docker_image_name, 'python3 add_box.py'))
    print(exec_commands(docker_image_name, 'python3 move_group_2.py'))
    result = exec_and_capture(docker_image_name, 'cat total_time.txt')"""
    total_time, success_list = result.split(',', 1)
    total_time = float(total_time)
    success_list = [int(b) for b in success_list.strip('[]').split(',')]
    
    """# BO RELEVANT CODE
    # asks for new parameters
    state_machine.suggest()
    # tells optimizer about result
    state_machine.observe(params=(6,5),result=sum(success_list) / len(success_list))
    state_machine.save_state(f"state_{project_id}_{experiment_id}.pkl")
    state_machine.reset()
    state_machine.load_state(f"state_{project_id}_{experiment_id}.pkl")
    # END BO RELEVANT CODE"""
    
    return {"total_time": total_time, "success_list": success_list}

@app.post("/bo/perform-motion-planning")
async def motion_planning(
    project_id: str,
    experiment_id: str,
    request_id: str,
):
    """
    Starts the motion planning process for a specific project, experiment and request.
    :param project_id: The project id for which the motion planning should be started.
    :param experiment_id: The experiment id for which the motion planning should be
        started.
    :param request_id: The request id for which the motion planning should be started.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    return "OK"

@app.get("/bo/results/{project_id}/{experiment_id}/{request_id}/motion-planning")
async def motion_planning_results(
    project_id: str,
    experiment_id: str,
    request_id: str,
):
    """
    Retrieves the motion planning results for a specific project, experiment and request.

    :param project_id: The project id for which the motion planning results should be
        retrieved.
    :param experiment_id: The experiment id for which the motion planning results should
        be retrieved.
    :param request_id: The request id for which the motion planning results should be
        retrieved.
    :return: Returns motion planning stats when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    data = {}
    return data

@app.post("/bo/{project_id}/{experiment_id}/update-with-result")
async def update_with_result(
    project_id: str,
    experiment_id: str
):
    """
    Updates bo state machine from a specific experiment with the latest result.
    
    :param project_id: The project id for which the state machine should be updated.
    :param experiment_id: The experiment id for which the state machine should be updated.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    return "OK"

@app.post("/submit/taxonomy")
async def save_taxonomy(
    payload: TaxonomyInf,
) -> str:
    """
    Takes a taxonomy payload in JSON form and inserts it into the database as is. It is
    indexed by a unique ID, usually the Fusion 360 project identifier.

    :param payload: The payload containing the taxonomy, split into three distinct
        taxonomies.
    :return: Returns "OK" when successful, else returns a 422 response code if payload
        didn't pass validation.
    """
    upsert_taxonomy(payload.model_dump(by_alias=True))
    return "OK"


@app.post("/request/assembly")
async def synthesize_assembly(
    payload: SynthesisRequestInf, background_tasks: BackgroundTasks
):
    """
    Takes a payload describing a synthesis request as JSON. Builds a repository and a
    query and then executes clsp. Results (if present) get enumerated (up to 100) and
    then post-processed into assembly instructions for the Fusion 360 Add-In to execute.
    A background task inserts the results bundled in a single JSON Object into the
    database.

    :param payload: The payload containing target types and constraints for the
        synthesis request.
    :param background_tasks: The background tasks to asynchronously insert into the
        database.
    :return: A JSON containing a result id and metadata, or FAIL if there are no
        results.
    """
    # state machine should transition to motion planning state after this is done
    # and IF flag is set
    take_time = timer()
    literals = {}
    part_count_type = Omega()
    if payload.partCounts:
        for partCount in payload.partCounts:
            literals[partCount.partCountName] = list(range(partCount.partNumber + 1))
        part_count_type = wrapped_counted_types(
            [Literal(c.partNumber, c.partCountName) for c in payload.partCounts]
        )

    query = Type.intersect([Constructor(x, part_count_type) for x in payload.target])
    taxonomy = Subtypes(
        suffix_and_merge_taxonomy(get_taxonomy_for_project(payload.forgeProjectId))
    )

    repo = RepositoryBuilder.add_all_to_repository(
        payload.forgeProjectId,
        taxonomy=taxonomy,
        part_counts=[
            (p.partType, p.partNumber, p.partCountName) for p in payload.partCounts
        ]
        if payload.partCounts
        else None,
    )

    gamma = FiniteCombinatoryLogic(
        repo,
        subtypes=taxonomy,
        literals=literals,
    )

    result = gamma.inhabit(query)

    terms = []
    terms.extend(enumerate_terms(query, result, max_count=100))
    interpreted_terms = [postprocess(interpret_term(term)) for term in terms]

    if not interpreted_terms:
        return "FAIL"

    request_id = generate_id()
    background_tasks.add_task(
        upsert_result,
        {
            "_id": request_id,
            "forgeProjectId": payload.forgeProjectId,
            "name": payload.name,
            "timestamp": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(interpreted_terms),
            "interpretedTerms": interpreted_terms,
            "payload": payload.model_dump(),
        },
    )
    print(f"Took: {timer() - take_time}")
    return {
        "_id": request_id,
        "forgeProjectId": payload.forgeProjectId,
        "name": payload.name,
        "timestamp": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(interpreted_terms),
    }


@app.get("/data/taxonomy/{project_id}", response_class=FastResponse)
async def get_taxonomy(project_id: str):
    """
    Retrieves the taxonomy and inverts subtype and supertype (Add-In uses Keys as
    Supertypes, CLS uses Keys as Subtype, for multiple inheritance).

    :param project_id: The project id for which a taxonomy should be retrieved.
    :return: The inverted taxonomy for the project id if present. If not present, an
        empty default taxonomy.
    """
    return invert_taxonomy(get_taxonomy_for_project(project_id))


@app.get("/results", response_class=FastResponse)
async def list_result_ids():
    """
    Lists all project ids for which synthesis results are found in the database.

    :return: The list of project ids. An empty list if no results exist.
    """
    return get_all_projects_in_results()


@app.get("/results/{project_id}", response_class=FastResponse)
async def list_project_ids(project_id: str):
    """
    Lists all result metadata for a specific project id.

    :param project_id: The project id for which to list metadata.
    :return: A list of JSON objects describing the individual results. Each object has
        an "id" key.
    """
    return [dict(x, id=x["_id"]) for x in get_all_result_ids_for_project(project_id)]


async def cache_request(request_id, project_id: str):
    """
    Caches a specific synthesis result. Since these can be several Mb of JSON data, this
    avoids unnecessary database accesses.

    :param project_id: The id of the project of the result to be cached.
    :param request_id: The id of the result to be cached.
    :return: The JSON data of the result.
    """
    if f"{request_id}_{project_id}" not in cache:
        cache[f"{request_id}_{project_id}"] = get_result_for_id_in_project(
            request_id, project_id
        )["interpretedTerms"]
    results = cache[f"{request_id}_{project_id}"]
    return results


@app.get("/results/{project_id}/{request_id}/maxcounts", response_class=FastResponse)
async def maximum_counts_for_id(
    project_id: str,
    request_id: str,
):
    """
    Computes the maximum amount of a part across all assemblies contained in a synthesis
    result. This is used to create a template file that contains enough parts to
    assemble any assembly from the results.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :return: A JSON object containing all the maximum counts. "Invalid" if the request
        or project ids were invalid.
    """
    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
    part_counts: defaultdict[int] = defaultdict(int)
    for result in results:
        for document_id, data in result["quantities"].items():
            part_counts[document_id] = (
                data["count"]
                if data["count"] > part_counts[document_id]
                else part_counts[document_id]
            )
    return FastResponse(part_counts)

@app.get("/results/{project_id}/{request_id}/cheapest", response_class=FastResponse)
async def cheapest_assembly_for_id(
    project_id: str,
    request_id: str,
):
    """
    Computes the cheapest assembly from a synthesis result.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :return: A JSON object containing the cheapest assembly. "Invalid" if the request
        or project ids were invalid.
    """
    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
    lowest_cost = None
    lowest_cost_index = 0
    for result_index, result in enumerate(results):
        if lowest_cost is None:
            lowest_cost = result["cost"]
            lowest_cost_index = result_index
        if result["cost"] < lowest_cost:
            lowest_cost = result["cost"]
            lowest_cost_index = result_index
    return FastResponse(results[lowest_cost_index])


@app.get("/results/{project_id}/{request_id}", response_class=FastResponse)
async def results_for_id(
    project_id: str,
    request_id: str,
    skip: int = 0,
    limit: int = sys.maxsize,
):
    """
    Returns the assemblies contained in a synthesis result.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :param skip: How many assemblies to skip from the start.
    :param limit: How many assemblies to return.
    :return: A list of assemblies of size up to limit. "Invalid" if the request or
        project ids were invalid.
    """
    if limit == 0:
        return []

    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
    if (limit < 0 or limit > len(results)) and skip == 0:
        return FastResponse(results)

    return FastResponse(
        [
            results[result_id]
            for result_id in range(
                skip if skip < len(results) else len(results) - 1,
                skip + limit if (skip + limit) <= len(results) else len(results),
            )
        ]
    )


@app.get("/results/{project_id}/{request_id}/{result_id}", response_class=FastResponse)
async def results_for_result_id(project_id: str, request_id: str, result_id: int):
    """
    Returns a single assembly from a synthesis result.

    :param project_id: The project id of the project the result is from.
    :param request_id: The id of the result.
    :param result_id: The index of the assembly in the result.
    :return: The assembly, or "" if the index did not exist. "Invalid" if the request or
        project ids were invalid.
    """
    try:
        results = await cache_request(request_id, project_id)
    except TypeError:
        return "Invalid"
    if result_id < len(results) or len(results) == -1:
        return FastResponse(results[result_id])
    else:
        return ""


# Finally, mount webpage for root.
app.mount(
    "/",
    StaticFiles(
        directory=os.path.join(os.path.dirname(__file__), "static/welcomePage"),
        html=True,
    ),
    name="landing",
)
