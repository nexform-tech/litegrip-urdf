"""在 RViz2 中可视化 LiteGrip 夹爪。

启动：
    ros2 launch litegrip_urdf display.launch.py
    ros2 launch litegrip_urdf display.launch.py gui:=false          # 不要关节滑块
    ros2 launch litegrip_urdf display.launch.py stroke:=0.02        # 覆盖关节行程

启动的节点：
    robot_state_publisher     解析 URDF 并发布 TF
    joint_state_publisher_gui 关节滑块（可用 gui:=false 关闭）
    rviz2                     可视化
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('litegrip_urdf')
    xacro_file = os.path.join(pkg_share, 'urdf', 'litegrip_urdf.urdf.xacro')
    default_rviz_config = os.path.join(pkg_share, 'config', 'litegrip_urdf.rviz')

    # 路径用引号包裹，避免工作空间路径含空格时 shell 解析出错
    robot_description = ParameterValue(
        Command(['xacro "', xacro_file, '"',
                 ' stroke:=', LaunchConfiguration('stroke'),
                 ' effort:=', LaunchConfiguration('effort'),
                 ' velocity:=', LaunchConfiguration('velocity')]),
        value_type=str,
    )

    declared_arguments = [
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='是否启动 joint_state_publisher_gui 关节滑块窗口'),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='是否启动 RViz2'),
        DeclareLaunchArgument(
            'rvizconfig', default_value=default_rviz_config,
            description='RViz2 配置文件路径'),
        DeclareLaunchArgument(
            'stroke', default_value='0.0435',
            description='单指行程 (m)，即关节 limit 的 upper'),
        DeclareLaunchArgument(
            'effort', default_value='10.0',
            description='关节最大输出力 (N)'),
        DeclareLaunchArgument(
            'velocity', default_value='0.2',
            description='关节最大速度 (m/s)'),
    ]

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        condition=IfCondition(LaunchConfiguration('gui')),
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription(declared_arguments + [
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node,
    ])
