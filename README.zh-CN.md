# litegrip_urdf

**LiteGrip 平行夹爪**的 ROS 2 描述包 —— URDF/xacro 模型、RViz 可视化、Gazebo 仿真
与 ros2_control 硬件接口定义。

[English](README.md) · **简体中文**

| 项目 | 内容 |
| --- | --- |
| **ROS 2 发行版** | Humble Hawksbill |
| **目标平台** | Ubuntu 22.04 (x86_64) |
| **包版本** | 1.0.0 |
| **模型来源** | SolidWorks URDF Exporter 1.6.0（几何与惯性参数未作改动） |

---

## 状态

下表如实列出哪些部分已被实际执行与验证、哪些没有 ——
在依赖本包的任何部分之前，请先阅读此表。

| 能力 | 状态 | 依据 |
| --- | --- | --- |
| URDF/xacro 可解析 | ✅ 已验证 | `check_urdf` 报出根节点 `base_footprint` → `base_link` → 2 个手指 link |
| `colcon build` | ✅ 已验证 | 在 ROS 2 Humble 上构建通过；见[已知环境问题](docs/troubleshooting.zh-CN.md#conda-的-python3-导致构建失败) |
| `display.launch.py` | ✅ 已验证 | 可启动，`stroke:=` 覆盖值能传入 URDF |
| `ros2_control.launch.py` | ✅ 已验证 | 两个控制器均达到 `active`；位置指令回路已确认 |
| 关节几何（行程 ↔ 开口） | ⚠️ **待重新验证** | TF 复核是在 mesh 理论行程 `0.0435` 两端做的；现默认限位已改为实测值 `0.042726`，两端位形需重新复核 |
| `gazebo.launch.py` | ⚠️ **未验证** | 验证环境中未安装 Gazebo，从未执行 |
| 参数 `effort`、`velocity` | ⚠️ **占位值** | SolidWorks 导出默认值，非实测。见[需要标定](#需要标定) |
| 参数 `joint_damping`、`joint_friction` | ⚠️ **占位值** | 为抑制仿真振荡而选取的保守初值 |

验证环境：ROS 2 Humble / Ubuntu 22.04 / `x86_64`，验证日期 2026-09-15。
在你自己的平台上依赖上述任何 ✅ 项之前，请重新验证。

---

## 概述

LiteGrip 是两指平行夹爪，由两个独立的 prismatic 关节驱动，每指一个。
两指沿 `base_link` 的 X 轴做对称运动。

本包是纯描述包，不含任何编译产物 —— `CMakeLists.txt` 仅将 `urdf/`、`launch/`、
`config/`、`meshes/` 安装到 `share/litegrip_urdf/`。

```text
litegrip_urdf/
├── package.xml
├── CMakeLists.txt
├── CHANGELOG.md
├── .markdownlint.json
├── .gitignore
├── urdf/
│   └── litegrip_urdf.urdf.xacro          机器人描述 —— 唯一的模型源文件
├── launch/
│   ├── display.launch.py                 RViz 可视化
│   ├── ros2_control.launch.py            ros2_control 控制链路
│   └── gazebo.launch.py                  Gazebo Classic 仿真（⚠ 未验证）
├── config/
│   ├── litegrip_controllers.yaml         ros2_control 控制器配置
│   ├── joint_names_litegrip_urdf.yaml    关节名清单，供 MoveIt Setup Assistant 导入
│   └── litegrip_urdf.rviz                RViz 配置
├── meshes/
│   ├── base_link.STL                     约 925 KB
│   ├── gripper_slider_link1.STL          （右指）
│   └── gripper_slider_link2.STL          （左指）
└── docs/
    ├── calibration-guide.zh-CN.md        标定流程（逐步）
    ├── calibration-guide.md              英文版
    ├── design-notes.zh-CN.md             设计决策、几何推导、修订记录
    ├── design-notes.md                   英文版
    ├── troubleshooting.zh-CN.md          已知坑点及其解决办法
    └── troubleshooting.md                英文版
```

**物理属性。** 总质量 0.5772 kg —— `base_link` 0.5063 kg，每指 0.03545 kg。
惯性张量原样沿用 SolidWorks 导出结果。

---

## 环境要求

- Ubuntu 22.04 上的 ROS 2 Humble Hawksbill
- Python 3.10（系统解释器 —— 见 [Conda 相关说明](docs/troubleshooting.zh-CN.md#conda-的-python3-导致构建失败)）

---

## 安装

安装依赖：

```bash
# 描述与可视化
sudo apt install ros-humble-robot-state-publisher ros-humble-joint-state-publisher \
                 ros-humble-joint-state-publisher-gui ros-humble-rviz2 ros-humble-xacro

# ros2_control（mock_components/GenericSystem 由 hardware_interface 提供）
sudo apt install ros-humble-ros2-control ros-humble-ros2-controllers \
                 ros-humble-controller-manager ros-humble-joint-state-broadcaster \
                 ros-humble-position-controllers

# 可选：Gazebo Classic 仿真
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
```

构建本包：

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
ln -s /path/to/litegrip_urdf .          # 或直接拷贝本目录
cd ~/ros2_ws
colcon build --packages-select litegrip_urdf
source install/setup.bash
```

> 若 `colcon build` 报 `ModuleNotFoundError: No module named 'catkin_pkg'`，
> 说明 Conda 解释器抢占了系统 Python。见
> [docs/troubleshooting.zh-CN.md](docs/troubleshooting.zh-CN.md#conda-的-python3-导致构建失败)
> —— 这是本包最常见的构建失败原因。

---

## 使用

### 1. RViz 可视化

```bash
ros2 launch litegrip_urdf display.launch.py
```

拖动 `joint_state_publisher_gui` 窗口的滑块即可驱动两指。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `gui` | `true` | 是否启动 `joint_state_publisher_gui` 关节滑块 |
| `rviz` | `true` | 是否启动 RViz2 |
| `rvizconfig` | `config/litegrip_urdf.rviz` | RViz 配置文件路径 |
| `stroke` | `0.042726` | 单指行程 (m)，实测值 |
| `effort` | `10.0` | 关节最大输出力 (N) |
| `velocity` | `0.2` | 关节最大速度 (m/s) |

示例：

```bash
ros2 launch litegrip_urdf display.launch.py gui:=false       # 不要关节滑块
ros2 launch litegrip_urdf display.launch.py stroke:=0.02     # 覆盖关节行程
```

> ⚠️ **`gui:=false` 会使手指 link 从 TF 中消失。** 本 launch 中唯一发布
> `/joint_states` 的节点就是 `joint_state_publisher_gui`；关掉它，prismatic 关节
> 就没有状态，`robot_state_publisher` 无法计算其变换，TF 中只剩
> `base_footprint → base_link` 这一条固定变换。若需要手指坐标系又不想开图形滑块窗口，
> 请另行启动无界面发布器：
>
> ```bash
> ros2 run joint_state_publisher joint_state_publisher
> ```

RViz 配置使用的固定坐标系为 `base_footprint`。

### 2. ros2_control 控制链路

```bash
ros2 launch litegrip_urdf ros2_control.launch.py
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `hardware_plugin` | `mock_components/GenericSystem` | ros2_control 硬件接口插件 |
| `stroke` | `0.042726` | 单指行程 (m)，实测值 |
| `effort` | `10.0` | 关节最大输出力 (N) |
| `velocity` | `0.2` | 关节最大速度 (m/s) |

默认硬件插件为 `mock_components/GenericSystem`，它把下发的 position 指令直接回读为
state。此模式下夹爪不会真的动，但 `controller_manager`、控制器加载、资源占用声明、
指令/状态接口链路都与接真机时完全一致 —— 因此这是在没有设备时验证集成方案的正确方式。

产生的节点图：

| 节点 | 作用 |
| --- | --- |
| `/robot_state_publisher` | 依据 `/joint_states` 发布 TF |
| `/controller_manager` | 加载并管理控制器 |
| `/joint_state_broadcaster` | 发布 `/joint_states` |
| `/gripper_controller` | `position_controllers/JointGroupPositionController` |

验证链路：

```bash
ros2 control list_controllers
# joint_state_broadcaster 与 gripper_controller 均应显示 [active]。

ros2 control list_hardware_interfaces
# 2 个 command 接口（已 claimed）+ 4 个 state 接口 = 共 6 个。

# 下发位置指令（顺序：右指, 左指）
ros2 topic pub --once /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.042726, 0.042726]}"

ros2 topic echo /joint_states
```

> ⚠️ **mock 硬件不会对越界指令做限幅。** 在上述配置下，`[0.05, 0.05]` 超出
> `stroke = 0.042726`，但既不会报错也不会被截断，会原样回读为 `0.05` —— 尽管接口上
> 声明了 `min`/`max` 参数。在该配置下，行程限制只是描述性元数据，而非强制性约束。
> 请在你自己的应用层做指令限幅。
>
> ℹ️ `/joint_states` 中 `effort` 为 `[nan, nan]`。mock 硬件未声明 effort 状态接口，
> 因此没有可发布的值。这是预期行为，不是错误。

### 3. Gazebo 仿真

> ⚠️ **本 launch 文件从未执行过。** 验证本包的环境中未安装 Gazebo。
> 首次运行请当作一次调试过程，重点确认模型是否正确生成、两个控制器是否成功激活。

```bash
ros2 launch litegrip_urdf gazebo.launch.py
```

该 launch 强制 `hardware_plugin:=gazebo_ros2_control/GazeboSystem`，启动 Gazebo、
生成模型，然后依次激活 `joint_state_broadcaster` 与 `gripper_controller`。

---

## 接口

### 关节

| 关节名 | 类型 | axis | 关节原点（`base_link` 系） | 限位 |
| --- | --- | --- | --- | --- |
| `gripper_slide_joint_right` | prismatic | `+X` | `(-0.067, 0.0010833, 0.034083)` | `[0, 0.042726]` m |
| `gripper_slide_joint_left` | prismatic | `-X` | `( 0.067, -0.0010833, 0.034083)` | `[0, 0.042726]` m |

### 连杆

| Link | 父节点 | 关节 | 质量 |
| --- | --- | --- | --- |
| `base_footprint` | — | 根节点，无惯性 | 0 |
| `base_link` | `base_footprint` | `base_footprint_joint`（fixed） | 0.5063 kg |
| `gripper_slider_link1` | `base_link` | `gripper_slide_joint_right` | 0.03545 kg |
| `gripper_slider_link2` | `base_link` | `gripper_slide_joint_left` | 0.03545 kg |

`base_footprint` 是与 `base_link` 位姿重合的无惯性 dummy 根节点，其存在是为了让
TF 树具有合法树根：KDL 不支持带惯性的 root link，否则会告警并静默忽略 `base_link`
的惯性。**将夹爪安装到机械臂时，请以 `base_footprint` 作为附着基准。**

### ros2_control 接口

| 关节 | command 接口 | state 接口 |
| --- | --- | --- |
| `gripper_slide_joint_right` | `position` | `position`、`velocity` |
| `gripper_slide_joint_left` | `position` | `position`、`velocity` |

**每份模型共 6 个接口。**（本文档早期版本写的是 4 个，正确数量为 2 command + 4 state。）

### 控制器

`position_controllers/JointGroupPositionController`，节点为 `/gripper_controller`。

指令数组的顺序即 `config/litegrip_controllers.yaml` 中的顺序：

| 下标 | 关节 |
| --- | --- |
| `[0]` | `gripper_slide_joint_right` |
| `[1]` | `gripper_slide_joint_left` |

---

## ⚠️ 关节符号约定 —— 编写控制器前必读

**两个关节的 `axis` 方向相反：right 为 `+X`，left 为 `-X`。
因此两关节取【同号值】才能使两指做对称运动。**

| 指令 | 结果 |
| --- | --- |
| `[0.0, 0.0]` | 完全张开 —— 模型内侧面位于 `x = ∓0.0435`，模型开口 **87 mm**；本机卡尺实测张开开口 **86.960 mm** |
| `[0.02, 0.02]` | 半闭合 |
| `[0.042726, 0.042726]` | 实测闭合标定位置 —— 本机卡尺实测闭合间隙 **1.508 mm** |

**按「一正一负」的直觉编写控制器，会让两指反向运动而非相向运动。**
该结论已通过实测确认：指令 `[0, 0]` 时两指原点位于 `x = ∓0.067`（模型内侧面在
`∓0.0435`）；而按 mesh 理论闭合值 `0.0435`，两指原点应位于 `x = ∓0.0235`
（内侧面在 `x = 0`，零间隙）。现默认限位 `0.042726` 略小于该理论值，停在实测闭合位置。

### 为何行程是 0.042726 而非 0.067

这里有两个不同的数，**不要混为一谈**。

**mesh 理论闭合行程 `0.0435`**，由 CAD 几何核算得出：

```text
gripper_slider_link1.STL 的 X 范围 = [-0.00095, +0.0235]   （包围盒实测）
关节原点 x                        = -0.067
=> 闭合行程 = 0.067 - 0.0235      =  0.0435
```

它是两指内侧面恰好贴合于 `x = 0`（零间隙）时的关节值，属于 CAD 几何属性，
不是实物属性。

**实测单指行程 `0.042726 m`**，即本包 `stroke` 的默认值。本机卡尺实测总机械行程
`85.452 mm`，即单指 `42.726 mm`，闭合间隙 `1.508 mm`。实物到不了理想零间隙闭合位，
故实测值更小 —— 是偏保守的一侧。

若取 `stroke = 0.067`，两指将完全重叠穿透。SolidWorks CSV 中右指标注
`Limit Upper = 0.067`、左指标注 `-0.067`，两者均无法直接使用。
完整推导见 [docs/design-notes.zh-CN.md](docs/design-notes.zh-CN.md#夹爪几何)。

> ⚠️ 把限位改成 `0.042726` 会同时改变模型两端的位形。下文记录的 mesh 与 TF 复核是在
> mesh 理论值 `0.0435` 上做的，因此模型新的两端位形仍需在运行时重新做 mesh/TF 复核，
> 才能称为几何验证完成。

---

## 配置

`urdf/litegrip_urdf.urdf.xacro` 通过 xacro 参数进行参数化：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `stroke` | `0.042726` | 单指行程 (m)，即关节 limit 的 `upper`，实测值 |
| `effort` | `10.0` | 关节最大输出力 (N) ⚠ 占位值 |
| `velocity` | `0.2` | 关节最大速度 (m/s) ⚠ 占位值 |
| `joint_damping` | `0.05` | 关节阻尼 ⚠ 占位值 |
| `joint_friction` | `0.02` | 关节摩擦 ⚠ 占位值 |
| `hardware_plugin` | `mock_components/GenericSystem` | ros2_control 硬件插件 |

**参数覆盖方式。** `stroke`、`effort`、`velocity` 已由 `display.launch.py` 与
`ros2_control.launch.py` 暴露为 launch 参数，可在命令行直接覆盖。
`joint_damping` 与 `joint_friction` **未被任何 launch 文件暴露** —— 要修改它们，
只能改 xacro 默认值，或直接调用 `xacro`。

单独展开为纯 URDF（供不支持 xacro 的工具使用）：

```bash
xacro $(ros2 pkg prefix litegrip_urdf)/share/litegrip_urdf/urdf/litegrip_urdf.urdf.xacro \
  -o /tmp/litegrip_urdf.urdf
```

### 需要标定

`effort = 10.0` N 与 `velocity = 0.2` m/s **是 SolidWorks 导出的默认值，不是实测值**。
在替换为标定值之前，任何基于 `<limit>` 的力矩或速度限幅都是不正确的。
`joint_damping` 与 `joint_friction` 同样只是为抑制仿真振荡而选的保守初值，
应按真实机构进行标定。

→ **[标定指南](docs/calibration-guide.zh-CN.md)** —— 从物理夹爪、Python SDK
一直到上述 xacro 参数的完整逐步标定流程。

---

## 接入真机

把 mock 插件替换为厂商的 ros2_control 硬件接口插件：

```bash
ros2 launch litegrip_urdf ros2_control.launch.py hardware_plugin:=<厂商插件名>
```

你的插件需要为两个关节提供：

- 一个 `position` **command** 接口
- `position` 与 `velocity` **state** 接口

本包不附带任何厂商插件。若你的硬件提供的是 `velocity` 或 `effort` 指令而非 `position`，
则 xacro 中的 `<ros2_control>` 块与 `config/litegrip_controllers.yaml` 中的控制器类型
都需要相应修改。

---

## 发布前检查清单

以下事项**尚未完成**，在发布本包前必须解决：

1. **维护者身份** —— `package.xml` 中仍为
   `<maintainer email="TODO@example.com">LiteGrip</maintainer>`。
   请替换为真实且法律上正确的实体名称与联系方式。
2. **许可证未定** —— 本包尚未选定许可证。`package.xml` 中的 `<license>TODO</license>`
   仅因 ROS 2 拒收不含 license 标签的包，不构成任何法律声明。
3. **URL** —— `package.xml` 中的 `<url>` 指向 `https://example.com/litegrip`。
4. **`effort` / `velocity` 标定** —— 见[需要标定](#需要标定)。
5. **`joint_damping` / `joint_friction` 标定** —— 见[需要标定](#需要标定)。
6. **Gazebo launch 验证** —— `gazebo.launch.py` 从未运行过。

## 已知限制

- **碰撞几何直接复用了高精度视觉 STL。** `base_link.STL` 约 925 KB。本夹爪仅 3 个
  link，碰撞检测开销可接受；若集成到对性能敏感的场景，建议将 `<collision>` 几何
  替换为简化几何体（box/cylinder）。
- **无抓取 Action 接口。** 默认的 `JointGroupPositionController` 通过话题接收关节数组。
  若需基于 Action 的接口，需改用 `position_controllers/GripperActionController`，
  但该控制器只接受**单个**关节，因此需要为另一指配置 `<mimic>` 关节 —— 而 `<mimic>`
  在 ros2_control 中不会自动生效。这正是默认选用多关节控制器的原因。
- **没有几何简化、没有碰撞余量、没有 `<safety_controller>` 限位、没有 transmission。**
  原始 SolidWorks 导出中也未定义这些内容。

## 文档

| 文档 | 内容 |
| --- | --- |
| [docs/calibration-guide.zh-CN.md](docs/calibration-guide.zh-CN.md) | 逐步标定流程，把每个占位值替换为实测值 —— 行程、角度范围、夹持力、速度、阻尼、摩擦 |
| [docs/design-notes.zh-CN.md](docs/design-notes.zh-CN.md) | 几何推导、关节约定、针对 SolidWorks 导出文件的修订记录、设计决策依据 |
| [docs/troubleshooting.zh-CN.md](docs/troubleshooting.zh-CN.md) | 已知故障模式及其解决办法，含 Conda 构建失败与 `controller_manager` 命名坑 |
| [CHANGELOG.md](CHANGELOG.md) | 版本历史（英文） |
