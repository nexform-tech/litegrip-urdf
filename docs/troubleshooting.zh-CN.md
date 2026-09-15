# 故障排查

`litegrip_urdf` 的已知故障模式及其解决办法。每条给出症状、原因与修复方式；
凡实际复现过的，附上可用于定位的确切命令输出。

[English](troubleshooting.md) · **简体中文**

---

## Conda 的 python3 导致构建失败

**症状。** `colcon build` 立即失败：

```text
ModuleNotFoundError: No module named 'catkin_pkg'
CMake Error at .../ament_package_xml.cmake:95 (message):
  execute_process(/home/<user>/miniconda3/bin/python3
  .../package_xml_2_cmake.py ...) returned error code 1
```

关键在于报错中的解释器路径 —— 是 Conda 前缀，而不是 `/usr/bin/python3`。

**原因。** Conda 环境位于 `PATH` 中，CMake 因而把 `Python3_EXECUTABLE` 解析为
未安装 ROS 2 Python 包的 Conda 解释器。这是环境问题，不是本包的缺陷 ——
任何 `ament_cmake` 包都会如此。

**修复。** 让 CMake 指向系统解释器：

```bash
colcon build --packages-select litegrip_urdf \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
```

或者在构建前退出 Conda 环境（`conda deactivate`），或在构建用的 shell 中将 Conda 的
`bin` 目录从 `PATH` 移除。**不要**通过 `pip install catkin_pkg` 装进 Conda 环境 ——
那会造成混用的解释器环境，后续失败会更难定位。

---

## `gui:=false` 会使手指 link 从 TF 中消失

**症状。** 使用 `ros2 launch litegrip_urdf display.launch.py gui:=false` 时：

- `tf2_echo base_footprint base_link` 正常，平移为 `[0, 0, 0]`。
- `tf2_echo base_footprint gripper_slider_link1` 一直等待，报
  `Invalid frame ID "gripper_slider_link1"`。

**原因。** `display.launch.py` 中只有 `joint_state_publisher_gui` 发布 `/joint_states`。
`gui:=false` 后没有任何节点发布关节状态，`robot_state_publisher` 拿不到两个 prismatic
关节的值，也就无法计算其变换。固定的 `base_footprint → base_link` 变换不依赖关节状态，
因而不受影响。`ros2 topic info /joint_states` 会显示 `Publisher count: 0`。

**修复。** 与 launch 同时启动无界面发布器：

```bash
ros2 run joint_state_publisher joint_state_publisher
```

此后三个 frame 均可解析。

---

## mock 硬件不会对越界指令做限幅

**症状。** 超出声明行程的指令会被静默接受：

```bash
ros2 topic pub --once /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.05, 0.05]}"   # stroke 为 0.042726；0.05 故意作为越界测试值
ros2 topic echo --once /joint_states
# position:
# - 0.05
# - 0.05
```

**原因。** `mock_components/GenericSystem` 把 position 指令原样回读为 state，
不会依据 command 接口上声明的 `min`/`max` 参数做校验。使用该硬件插件时，行程限制只是
描述性元数据，不是强制约束。任何未自行实现限位的硬件插件，预期行为也是如此。

**修复。** 在发布之前，于你自己的应用层完成限幅。
不要假设控制器或硬件会拒绝越界值。

---

## `/joint_states` 中 `effort` 为 `nan`

**症状。**

```text
effort:
- .nan
- .nan
```

**原因。** `<ros2_control>` 块只声明了 `position` 与 `velocity` 两个 state 接口，
mock 硬件没有 effort 值可发布。

**修复。** 无需处理 —— 这是预期行为。若下游消费方要求数值化的 effort，
要么新增 `effort` state 接口并由你的硬件插件提供，要么在消费方过滤 `NaN`。
这也不代表允许最大夹持力已经完成标定；`effort` 限值仍需经过力矩—夹持力测试后确定。

---

## 报 `'joints' parameter was empty` / 控制器无法配置

**症状。** 控制器管理器报告某个控制器无法配置，错误为 `'joints' parameter was empty`，
但 `config/litegrip_controllers.yaml` 中明明列出了关节。

**原因。** 有两种不同的错误都会导致该现象，请逐一排查：

**原因 1 —— 参数层级。** 控制器参数必须写在**独立的顶层节点段**中，以控制器名为键：

```yaml
# ✅ 正确
gripper_controller:
  ros__parameters:
    joints: [gripper_slide_joint_right, gripper_slide_joint_left]
```

而不是嵌套在 `controller_manager` 之下：

```yaml
# ❌ 错误 —— controller_manager 只从这里读取 `type`
controller_manager:
  ros__parameters:
    gripper_controller:
      joints: [...]      # 永远不会被转交给控制器节点
```

**原因 2 —— 被控制器继承的 `__node` 重映射。** 不要在 launch 中给 `ros2_control_node`
显式传入 `name='controller_manager'`。这样做会让 `launch_ros` 追加
`-r __node:=controller_manager`，而 `controller_manager` 会把该重映射传播给它运行时
创建的控制器节点。于是所有控制器都自称 `/controller_manager`，原因 1 中的顶层 YAML
段便再也匹配不上任何节点。当前的 `ros2_control.launch.py` 是刻意省略 `name=` 参数的
—— 见 `controller_manager_node` 定义处的注释。

---

## KDL 报 `root link has an inertia` 告警

**症状。** MoveIt 或某个基于 KDL 的工具告警称根节点带惯性，
且 `base_link` 的惯性似乎被忽略。

**原因。** KDL 要求根节点无惯性。原始 SolidWorks 导出中 `base_link` 既是根节点又带惯性，
其惯性因此被静默丢弃。

**修复。** 已处理：模型定义了无惯性的 `base_footprint` 根节点，并以 fixed 关节连接
`base_link`。若在当前模型上仍看到该告警，说明你加载的是另一个 URDF ——
最可能是未展开的原始导出文件副本。

**切勿**再额外发布 `base_footprint` 与 `base_link` 之间的静态变换：URDF 中已定义二者关系，
重复定义会让同一对 frame 在 TF 树中出现两个父节点。

---

## `gazebo.launch.py` 启动失败

**症状。** launch 因 `package 'gazebo_ros' not found` 中止，或 Gazebo 已启动但模型始终
未生成。

**原因。** Gazebo Classic 是可选依赖，默认未安装。
**验证本包的环境中并未安装 Gazebo，因此 `gazebo.launch.py` 从未执行过，必须视为未经验证。**
因此，虽然本机已经完成机械行程和角度标定，更新后的 `0.042726 m` 行程限位在
Gazebo 中的 mesh、TF 和控制器行为仍不能视为已验证。

**修复。** 安装仿真依赖：

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
```

然后运行，并按此顺序确认：(1) 模型出现在 Gazebo 中，(2)
`ros2 control list_controllers` 显示 `joint_state_broadcaster` 为 `active`，(3)
`gripper_controller` 变为 `active`，(4) 下发位置指令后手指在仿真中确实运动。

---

## 原始导出文件无法解析

**症状。** 将原始 SolidWorks 导出中的文件载入任何 URDF 工具均失败。

**原因。** 导出中的两份中间 URDF 都无法解析。经 `check_urdf` 确认：

| 文件 | 报错 |
| --- | --- |
| `夹爪urdf改前.urdf` | `joint 'gripper_slide_joint' is not unique.` |
| `夹爪urdf2 (1).urdf` | `upper value (0.043.5) is not a valid float` |

**修复。** 使用本包中的 `urdf/litegrip_urdf.urdf.xacro`。两份中间文件都不能作为参照 ——
尤其**不要从中拷贝 `0.067` 的行程限位**。当前本机实测单指行程为 `0.042726 m`，
总机械行程为 `85.452 mm`；`0.0435 m` 仅是由 mesh 包围盒推导出的理论行程，不能替代
本机实测标定值。正确推导见
[design-notes.zh-CN.md](design-notes.zh-CN.md#行程限位的推导)。

---

## RViz 中什么都看不到

**症状。** RViz 打开了但看不到夹爪，或显示缺少变换。

**原因。** 随包提供的配置使用 `base_footprint` 作为固定坐标系，
因此整棵树依赖 `/tf` 与 `/robot_description` 正常发布。

**修复。** 确认这两项：

```bash
ros2 topic echo --once /robot_description    # 应返回 URDF 文本
ros2 run tf2_ros tf2_echo base_footprint base_link
```

若 `/robot_description` 为空，说明 `robot_state_publisher` 未启动或展开 xacro 失败 ——
请检查其终端输出。若 `/robot_description` 正常但变换缺失，见
[`gui:=false` 会使手指 link 从 TF 中消失](#guifalse-会使手指-link-从-tf-中消失)。

本机当前标定记录为：`zero_position_rad = 0.041390`、
`max_position_rad = -1.272793`、`travel_range_rad = 1.314183`、
`rad_to_mm = 65.0229 mm/rad`；`calibrate_guided` 3 次输出稳定，张开端复测 5 次
得到的机械行程为 `85.43–85.47 mm`。位置卡尺数据已经采集，但 `20 mm` 位置出现
`18.80 mm` 的异常读数，最大原始绝对误差为 `1.20 mm`，因此位置绝对误差仍需复测
后才能最终验收。50 次循环（`2 mm ↔ 83 mm`）已完成，第 1 次到第 50 次的闭合端、
张开端开口漂移分别为 `+0.01 mm`、`+0.02 mm`，闭合角度和张开角度漂移均为
`+0.000009 rad`。上述实测数据不等同于 `calibrate_guided` 源代码逻辑和运行时
Gazebo/TF 验证已经完成；这两项仍需单独验证。