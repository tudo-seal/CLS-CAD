#!/usr/bin/python

import sys
import math
import rospy
import moveit_commander
import time

from geometry_msgs.msg import Pose
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive

from tf.transformations import quaternion_from_euler

FRAME_ID = 'link_0_1'
(X, Y, Z, W) = (0, 1, 2, 3)
OPEN = 2.8
CLOSE = 0.98
OBJECT_POSITIONS = {'target_1': [0.35, -0.0293, 0.261],
                    'target_2': [-0.0677, 0.24, 0.302]}
PICK_ORIENTATION_EULER = [-math.pi / 2, 0, 0]
PLACE_ORIENTATION_EULER = [-math.pi / 2, 0, math.pi / 2]
SCENE = moveit_commander.PlanningSceneInterface()
timer_data = {
    "start_time": None,
    "elapsed": 0.0
}

def start_timer():
    """Start the timer by recording the current time."""
    timer_data["start_time"] = time.time()

def stop_timer():
    """Stop the timer and add the elapsed time to the total."""
    if timer_data["start_time"] is not None:
        elapsed_time = time.time() - timer_data["start_time"]
        timer_data["elapsed"] += elapsed_time
        timer_data["start_time"] = None
        print(f"Stopped timer. Added {elapsed_time:.2f} seconds.")
    else:
        print("Timer was not running.")

def get_total_time():
    """Return the total accumulated time."""
    return timer_data["elapsed"]



def create_collision_object(id, dimensions, pose):
    object = CollisionObject()
    object.id = id
    object.header.frame_id = FRAME_ID

    solid = SolidPrimitive()
    solid.type = solid.BOX
    solid.dimensions = dimensions
    object.primitives = [solid]

    object_pose = Pose()
    object_pose.position.x = pose[X]
    object_pose.position.y = pose[Y]
    object_pose.position.z = pose[Z]

    object.primitive_poses = [object_pose]
    object.operation = object.ADD
    return object


def add_collision_objects():
    floor_limit = create_collision_object(id='floor_limit',
                                          dimensions=[10, 10, 0.2],
                                          pose=[0, 0, -0.1])
    table_1 = create_collision_object(id='table_1',
                                      dimensions=[0.3, 0.6, 0.25],
                                      pose=[0.35, 0.2, 0.125])
    above_table_1 = create_collision_object(id='above_table_1',
                                            dimensions=[0.3, 0.6, 0.1],
                                            pose=[0.35, 0.2, 0.425])
    table_2 = create_collision_object(id='table_2',
                                      dimensions=[0.3, 0.3, 0.3],
                                      pose=[0.05, 0.35, 0.15])
    above_table_2 = create_collision_object(id='above_table_2',
                                            dimensions=[0.3, 0.3, 0.1],
                                            pose=[0.05, 0.35, 0.425])
    target_box = create_collision_object(id='target_box',
                                       dimensions=[0.02, 0.02, 0.04],
                                       pose=[0.35, -0.0293, 0.271])

    SCENE.add_object(floor_limit)
    SCENE.add_object(table_1)
    SCENE.add_object(table_2)
    SCENE.add_object(above_table_1)
    SCENE.add_object(above_table_2)
    #SCENE.add_object(target_box)


def reach_named_position(arm, target):
    arm.set_named_target(target)
    plan_success, plan, planning_time, error_code = arm.plan()
    return arm.execute(plan, wait=True), plan_success


def reach_pose(arm, pose, tolerance=0.02):
    arm.set_position_target([pose.orientation.x,pose.orientation.y,pose.orientation.z])
    arm.set_goal_position_tolerance(tolerance)
    return arm.go(wait=True)

def reach_position(arm, position, tolerance=0.03):
    arm.set_position_target(position)
    arm.set_goal_position_tolerance(tolerance)
    return arm.go(wait=True)


def open_gripper(gripper):
    # Replace with your specific joint value for open
    joint_goal = gripper.get_current_joint_values()
    joint_goal[0] = OPEN
    return gripper.go(joint_goal, wait=True)

def close_gripper(gripper):
    joint_goal = gripper.get_current_joint_values()
    joint_goal[0] = CLOSE
    return gripper.go(joint_goal, wait=True)


def pick_object(name, arm, gripper):
    pose = Pose()
    pose.position.x = OBJECT_POSITIONS[name][X]
    pose.position.y = OBJECT_POSITIONS[name][Y] - 0.1
    pose.position.z = OBJECT_POSITIONS[name][Z]
    orientation = quaternion_from_euler(*PICK_ORIENTATION_EULER)
    pose.orientation.x = orientation[X]
    pose.orientation.y = orientation[Y]
    pose.orientation.z = orientation[Z]
    pose.orientation.w = orientation[W]
    reach_pose(arm, pose)
    open_gripper(gripper=gripper)
    pose.position.y += 0.1
    reach_pose(arm, pose)
    close_gripper(gripper=gripper)
    arm.attach_object(name)


def place_object(name, arm, gripper):
    pose = Pose()
    pose.position.x = OBJECT_POSITIONS[name][Y]
    pose.position.y = OBJECT_POSITIONS[name][X]
    pose.position.z = OBJECT_POSITIONS[name][Z]
    orientation = quaternion_from_euler(*PLACE_ORIENTATION_EULER)
    pose.orientation.x = orientation[X]
    pose.orientation.y = orientation[Y]
    pose.orientation.z = orientation[Z]
    pose.orientation.w = orientation[W]

    reach_pose(arm, pose)
    open_gripper(gripper=gripper)
    reach_pose(arm, pose)
    arm.detach_object(name)


def main():
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node('pick_place')
    rospy.sleep(2)

    arm = moveit_commander.MoveGroupCommander('my_robot_top_group',
                                              ns=rospy.get_namespace())
    robot = moveit_commander.RobotCommander('robot_description')

    scene = moveit_commander.PlanningSceneInterface()
    planning_frame = arm.get_planning_frame()
    
    arm.set_planning_time(10.0)
    arm.set_num_planning_attempts(100)
    gripper = moveit_commander.MoveGroupCommander('my_effector',
                                              ns=rospy.get_namespace())

    add_collision_objects()
    
    arm.set_start_state_to_current_state()
    success_list = []
    something, plan_success = reach_named_position(arm=arm, target='home')
    # success of first step is not needed
    start_timer()
    plan_success = reach_position(arm=arm, position=OBJECT_POSITIONS['target_1'])
    stop_timer()
    success_list.append(plan_success)
    print(f"Time to reach target_1: {get_total_time():.2f} seconds")
    #arm.attach_object('target_box')
    start_timer
    something, plan_success = reach_named_position(arm=arm, target='home')
    stop_timer()
    success_list.append(plan_success)
    print(f"Time to reach home: {get_total_time():.2f} seconds")
    start_timer()
    plan_success = reach_position(arm=arm, position=OBJECT_POSITIONS['target_2'])
    stop_timer()
    success_list.append(plan_success)
    print(f"Time to reach target_2: {get_total_time():.2f} seconds")
    #arm.detach_object('target_box')
    start_timer()
    something, plan_success = reach_named_position(arm=arm, target='home')
    stop_timer()
    success_list.append(plan_success)
    print(f"Time to reach home: {get_total_time():.2f} seconds")

    print("Total time: ", get_total_time())
    # save the total time to a file
    with open('total_time.txt', 'w') as f:
        f.write(f"{get_total_time():.2f},{[int(b) for b in success_list]}")

if __name__ == '__main__':
    main()