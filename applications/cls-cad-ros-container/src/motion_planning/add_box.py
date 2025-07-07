import sys
import rospy
import geometry_msgs.msg
from geometry_msgs.msg import PoseStamped
import moveit_commander



moveit_commander.roscpp_initialize(sys.argv)
rospy.init_node("move_group_interface", anonymous=True, log_level=rospy.DEBUG)

group_name = "my_robot_top_group"
move_group = moveit_commander.MoveGroupCommander(group_name)

scene = moveit_commander.PlanningSceneInterface()
planning_frame = move_group.get_planning_frame()

# Add BALL object
box_pose = PoseStamped()
box_pose.header.frame_id = planning_frame
box_pose.pose.position.x = 0.051961
box_pose.pose.position.y = -0.12341
box_pose.pose.position.z = 0.27082
box_pose.pose.orientation.w = 1.0

scene.add_box("box", box_pose, size=(0.02, 0.02, 0.01))