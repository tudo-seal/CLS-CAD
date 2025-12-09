import sys
import copy
import rospy
import moveit_msgs.msg
import geometry_msgs.msg

from std_msgs.msg import String
from moveit_commander.conversions import pose_to_list

import time
from geometry_msgs.msg import PoseStamped
import moveit_commander

# === ADDED: Helper to check if trajectory has points ===
def plan_has_points(plan):
    try:
        return len(plan.joint_trajectory.points) > 0
    except AttributeError:
        return False

# === Your main code starts here ===
moveit_commander.roscpp_initialize(sys.argv)
rospy.init_node("move_group_interface", anonymous=True, log_level=rospy.DEBUG)

robot = moveit_commander.RobotCommander()
scene = moveit_commander.PlanningSceneInterface()
group_name = "my_robot_top_group"
move_group = moveit_commander.MoveGroupCommander(group_name)

planning_frame = move_group.get_planning_frame()
eef_link = move_group.get_end_effector_link()
group_names = robot.get_group_names()

print(f"\n============ Planning frame: {planning_frame}")
print(f"============ End effector link: {eef_link}")
print(f"============ Available Planning Groups: {group_names}")

# === Robot state at startup ===
print("============ Initial robot state:")
print(robot.get_current_state())
print("============ Current robot pose:")
print(move_group.get_current_pose().pose)

# === Active joints info ===
print("============ Active joints:", move_group.get_active_joints())
print("============ All robot joints:", move_group.get_joints())

# === Planner and pipeline setup ===
move_group.set_planning_time(10.0)
move_group.set_num_planning_attempts(1000)
move_group.set_max_velocity_scaling_factor(0.5)
move_group.set_max_acceleration_scaling_factor(0.5)

rospy.sleep(2.0)
move_group.set_start_state_to_current_state()

# === Step 1: Pre-grasp pose ===
pre_grasp_pose = geometry_msgs.msg.Pose()
pre_grasp_pose.position.x = 0.051961
pre_grasp_pose.position.y = -0.12341
pre_grasp_pose.position.z = 0.27082
xyz = [pre_grasp_pose.position.x, pre_grasp_pose.position.y, pre_grasp_pose.position.z]
pre_grasp_pose.orientation.w = 1.0

move_group.set_position_target(xyz,end_effector_link=eef_link)
plan_result = move_group.plan()

if isinstance(plan_result, tuple):
    success, plan, planning_time, error_code = plan_result
    print(f"\n--- Pre-grasp Planning ---")
    print(f"Success: {success}, Planning time: {planning_time}, Error code: {error_code.val}")
    print(f"Trajectory has {len(plan.joint_trajectory.points)} points" if plan_has_points(plan) else "No trajectory points!")
else:
    print("Older MoveIt version plan structure.")

if success and plan_has_points(plan):
    move_group.execute(plan, wait=True)
else:
    print("Planning failed — skipping execution.")

move_group.stop()
move_group.clear_pose_targets()
rospy.sleep(1.0)

# === Attach object to end-effector ===
touch_links = robot.get_link_names(group="my_effector")
scene.attach_box(eef_link, "box", touch_links=touch_links)

# === Step 2: Place pose ===
place_pose = geometry_msgs.msg.Pose()
place_pose.position.x = 0.35
place_pose.position.y = 0.0
place_pose.position.z = 0.08
place_pose.orientation.w = 1.0

move_group.set_start_state_to_current_state()
move_group.set_pose_target(place_pose)
plan_result = move_group.plan()

if isinstance(plan_result, tuple):
    success, plan, planning_time, error_code = plan_result
    print(f"\n--- Place Planning ---")
    print(f"Success: {success}, Planning time: {planning_time}, Error code: {error_code.val}")
    print(f"Trajectory has {len(plan.joint_trajectory.points)} points" if plan_has_points(plan) else "No trajectory points!")
else:
    print("Older MoveIt version plan structure.")

if success and plan_has_points(plan):
    move_group.execute(plan, wait=True)
else:
    print("Planning failed — skipping execution.")

move_group.stop()
move_group.clear_pose_targets()
rospy.sleep(1.0)
scene.remove_attached_object(eef_link, name="box")

# === Step 3: Return to start pose ===
start_pose = move_group.get_current_pose().pose
move_group.set_pose_target(start_pose)
plan_result = move_group.plan()

if isinstance(plan_result, tuple):
    success, plan, planning_time, error_code = plan_result
    print(f"\n--- Return to Start Pose Planning ---")
    print(f"Success: {success}, Planning time: {planning_time}, Error code: {error_code.val}")
    print(f"Trajectory has {len(plan.joint_trajectory.points)} points" if plan_has_points(plan) else "No trajectory points!")
else:
    print("Older MoveIt version plan structure.")

if success and plan_has_points(plan):
    move_group.execute(plan, wait=True)
else:
    print("Planning failed — skipping execution.")

move_group.stop()