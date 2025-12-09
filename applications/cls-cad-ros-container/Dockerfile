FROM ros:noetic-ros-core

# Set noninteractive frontend for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install common dependencies
RUN apt-get update && apt-get install -y \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    ros-noetic-tf2-ros \
    ros-noetic-robot-state-publisher \
    ros-noetic-joint-state-publisher \
    ros-noetic-joint-state-publisher-gui \
    ros-noetic-rviz \
    ros-noetic-moveit \
    ros-noetic-rospy \
    && rm -rf /var/lib/apt/lists/*

# Initialize rosdep
RUN rosdep init && rosdep update

# Create a workspace
RUN mkdir -p /ros_ws/src
WORKDIR /ros_ws

# Copy over the python scripts for motion planning
COPY ./src /ros_ws/src

# Build workspace
RUN . /opt/ros/noetic/setup.sh && \
    catkin_make

# Source environment by default
RUN echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
RUN echo "source /ros_ws/devel/setup.bash" >> ~/.bashrc

SHELL ["/bin/bash", "-c"]

CMD ["bash", "-i"]
