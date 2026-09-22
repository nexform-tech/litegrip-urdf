"""在 Gazebo Classic 中仿真 LiteGrip 夹爪。

⚠ 本文件尚未在本机验证 —— 构建环境未安装 Gazebo。
   使用前请确认已安装：
       sudo apt install ros-$ROS_DISTRO-gazebo-ros-pkgs \
                        ros-$ROS_DISTRO-gazebo-ros2-control
   首次运行请重点检查：模型是否正确生成、控制器是否成功激活。

说明：此 launch 不额外发布 base_link -> base_footprint 的静态变换。
URDF 中已定义 base_footprint 为无惯性根节点且与 base_link 位姿重合，
另加静态变换会造成 TF 树出现两个父节点而报错。
（原 catkin 包的 gazebo.launch 存在此问题。）

启动：
    ros2 launch litegrip_urdf gazebo.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('litegrip_urdf')
    xacro_file = os.path.join(pkg_share, 'urdf', 'litegrip_urdf.urdf.xacro')
    controllers_yaml = os.path.join(pkg_share, 'config', 'litegrip_controllers.yaml')

    robot_description = ParameterValue(
        Command(['xacro "', xacro_file, '"',
                 ' stroke:=', LaunchConfiguration('stroke'),
                 ' effort:=', LaunchConfiguration('effort'),
                 ' velocity:=', LaunchConfiguration('velocity'),
                 ' hardware_plugin:=gazebo_ros2_control/GazeboSystem']),
        value_type=str,
    )

    declared_arguments = [
        DeclareLaunchArgument('stroke', default_value='0.042726',
                              description='单指行程 (m)'),
        DeclareLaunchArgument('effort', default_value='10.0',
                              description='关节最大输出力 (N)'),
        DeclareLaunchArgument('velocity', default_value='0.2',
                              description='关节最大速度 (m/s)'),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'),
                         'launch', 'gazebo.launch.py')
        )
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                   '-entity', 'litegrip_urdf'],
        output='screen',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # 模型生成完毕后再激活控制器
    controllers_after_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )

    gripper_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[gripper_controller_spawner],
        )
    )

    return LaunchDescription(declared_arguments + [
        gazebo,
        robot_state_publisher_node,
        spawn_entity,
        controllers_after_spawn,
        gripper_after_jsb,
    ])
