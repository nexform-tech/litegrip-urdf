"""启动 ros2_control 控制链路。

启动：
    ros2 launch litegrip_urdf ros2_control.launch.py
    # 接入真机时替换硬件插件：
    ros2 launch litegrip_urdf ros2_control.launch.py \
        hardware_plugin:=<厂商硬件接口插件名>

默认硬件插件为 mock_components/GenericSystem —— 它把下发的 position 指令
直接回读为 state，用于在没有真实硬件的情况下验证控制链路是否通畅。
此模式下夹爪不会真的动，但 controller_manager / spawner / 控制器
会完整走一遍真实流程。

启动的节点：
    robot_state_publisher       发布 TF
    controller_manager          加载并管理控制器
    spawner                     依次激活 joint_state_broadcaster、gripper_controller
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
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
                 ' hardware_plugin:=', LaunchConfiguration('hardware_plugin')]),
        value_type=str,
    )

    declared_arguments = [
        DeclareLaunchArgument(
            'hardware_plugin', default_value='mock_components/GenericSystem',
            description='ros2_control 硬件接口插件；接入真机时替换为厂商插件'),
        DeclareLaunchArgument(
            'stroke', default_value='0.0435',
            description='单指行程 (m)'),
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

    # ⚠ 不要在这里显式指定 name='controller_manager'。
    #   ros2_control_node 的默认节点名已经是 controller_manager，
    #   显式指定会让 launch_ros 追加 `-r __node:=controller_manager` 重映射；
    #   该重映射会被 controller_manager 继承给运行时创建的控制器节点，
    #   导致所有控制器节点都叫 /controller_manager，
    #   从而使 YAML 中按控制器名划分的参数段无法匹配，
    #   表现为 "'joints' parameter was empty" 且控制器无法配置。
    controller_manager_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        output='both',
        parameters=[
            {'robot_description': robot_description},
            controllers_yaml,
        ],
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

    # joint_state_broadcaster 激活后再启动夹爪控制器，
    # 避免 /joint_states 尚未发布时控制器报缺少状态。
    gripper_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[gripper_controller_spawner],
        )
    )

    return LaunchDescription(declared_arguments + [
        robot_state_publisher_node,
        controller_manager_node,
        joint_state_broadcaster_spawner,
        gripper_after_jsb,
    ])
