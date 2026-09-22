# litegrip_urdf

ROS 2 description package for the **LiteGrip parallel gripper** — URDF/xacro model,
RViz visualization, Gazebo simulation, and ros2_control hardware interface definitions.

**English** · [简体中文](README.zh-CN.md)

| Property | Value |
| --- | --- |
| **ROS 2 distribution** | Humble Hawksbill |
| **Target platform** | Ubuntu 22.04 (x86_64) |
| **Package version** | 1.0.0 |
| **Model source** | SolidWorks URDF Exporter 1.6.0 (geometry and inertia unchanged) |

---

## Status

The table below states exactly what has been executed and verified, and what has
not — read it before depending on any part of this package.

| Capability | Status | Evidence |
| --- | --- | --- |
| URDF/xacro parses | ✅ Verified | `check_urdf` reports root `base_footprint` → `base_link` → 2 finger links |
| `colcon build` | ✅ Verified | Builds on ROS 2 Humble; see [known environment issue](docs/troubleshooting.md#conda-python3-breaks-the-build) |
| `display.launch.py` | ✅ Verified | Launches, `stroke:=` override propagates into the URDF |
| `ros2_control.launch.py` | ✅ Verified | Both controllers reach `active`; position command round-trip confirmed |
| Joint geometry (stroke ↔ opening) | ⚠️ **Re-verification pending** | Finger origins and inner-face positions were confirmed via TF at the mesh-theoretical travel limit `0.0435`; the shipped limit is now the measured `0.042726`, so both endpoints need re-checking |
| `gazebo.launch.py` | ⚠️ **Not verified** | Gazebo is not installed in the verification environment; never executed |
| Parameters `effort`, `velocity` | ⚠️ **Placeholder** | SolidWorks export defaults, not measured. See [Calibration required](#calibration-required) |
| Parameters `joint_damping`, `joint_friction` | ⚠️ **Placeholder** | Conservative values chosen to damp simulation oscillation |

Verification was performed on ROS 2 Humble / Ubuntu 22.04 with `x86_64` on 2026-09-15.
Re-verify on your own platform before relying on any ✅ above.

---

## Overview

LiteGrip is a two-finger parallel gripper driven by two independent prismatic joints,
one per finger. The two fingers move symmetrically along the X axis of `base_link`.

This package is a pure description package. It contains no compiled code — `CMakeLists.txt`
only installs `urdf/`, `launch/`, `config/`, and `meshes/` into `share/litegrip_urdf/`.

```text
litegrip_urdf/
├── package.xml
├── CMakeLists.txt
├── CHANGELOG.md
├── .markdownlint.json
├── .gitignore
├── urdf/
│   └── litegrip_urdf.urdf.xacro          Robot description — the single source of truth
├── launch/
│   ├── display.launch.py                 RViz visualization
│   ├── ros2_control.launch.py            ros2_control pipeline
│   └── gazebo.launch.py                  Gazebo Classic simulation (⚠ unverified)
├── config/
│   ├── litegrip_controllers.yaml         ros2_control controller configuration
│   ├── joint_names_litegrip_urdf.yaml    Joint name list, for MoveIt Setup Assistant
│   └── litegrip_urdf.rviz                RViz configuration
├── meshes/
│   ├── base_link.STL                     ~925 KB
│   ├── gripper_slider_link1.STL          (right finger)
│   └── gripper_slider_link2.STL          (left finger)
└── docs/
    ├── calibration-guide.md              Step-by-step calibration procedure
    ├── calibration-guide.zh-CN.md        Chinese translation
    ├── design-notes.md                   Design decisions, geometry derivation, revision history
    ├── design-notes.zh-CN.md             Chinese translation
    ├── troubleshooting.md                Known pitfalls and their resolutions
    └── troubleshooting.zh-CN.md          Chinese translation
```

**Physical properties.** Total mass 0.5772 kg — `base_link` 0.5063 kg, each finger
0.03545 kg. Inertia tensors are carried over unmodified from the SolidWorks export.

---

## Requirements

- ROS 2 Humble Hawksbill on Ubuntu 22.04
- Python 3.10 (system interpreter — see [the Conda note](docs/troubleshooting.md#conda-python3-breaks-the-build))

---

## Installation

Install dependencies:

```bash
# Description and visualization
sudo apt install ros-humble-robot-state-publisher ros-humble-joint-state-publisher \
                 ros-humble-joint-state-publisher-gui ros-humble-rviz2 ros-humble-xacro

# ros2_control (provides mock_components/GenericSystem via hardware_interface)
sudo apt install ros-humble-ros2-control ros-humble-ros2-controllers \
                 ros-humble-controller-manager ros-humble-joint-state-broadcaster \
                 ros-humble-position-controllers

# Optional: Gazebo Classic simulation
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
```

Build the package:

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
ln -s /path/to/litegrip_urdf .          # or copy the directory
cd ~/ros2_ws
colcon build --packages-select litegrip_urdf
source install/setup.bash
```

> If `colcon build` fails with `ModuleNotFoundError: No module named 'catkin_pkg'`,
> a Conda interpreter is shadowing the system Python. See
> [docs/troubleshooting.md](docs/troubleshooting.md#conda-python3-breaks-the-build) —
> this is the most common build failure for this package.

---

## Usage

### 1. RViz visualization

```bash
ros2 launch litegrip_urdf display.launch.py
```

Drag the sliders in the `joint_state_publisher_gui` window to drive both fingers.

| Argument | Default | Description |
| --- | --- | --- |
| `gui` | `true` | Start `joint_state_publisher_gui` (joint sliders) |
| `rviz` | `true` | Start RViz2 |
| `rvizconfig` | `config/litegrip_urdf.rviz` | RViz configuration file path |
| `stroke` | `0.042726` | Per-finger travel (m) — measured value |
| `effort` | `10.0` | Joint maximum effort (N) |
| `velocity` | `0.2` | Joint maximum velocity (m/s) |

Examples:

```bash
ros2 launch litegrip_urdf display.launch.py gui:=false       # no slider window
ros2 launch litegrip_urdf display.launch.py stroke:=0.02     # override joint travel
```

> ⚠️ **`gui:=false` removes the finger links from TF.** `joint_state_publisher_gui`
> is the only node in this launch that publishes `/joint_states`, so with `gui:=false`
> the prismatic joints have no state and `robot_state_publisher` cannot compute their
> transforms. Only the fixed transform `base_footprint → base_link` remains. If you
> need the finger frames without the GUI, start the headless publisher too:
>
> ```bash
> ros2 run joint_state_publisher joint_state_publisher
> ```

The RViz configuration uses `base_footprint` as its fixed frame.

### 2. ros2_control pipeline

```bash
ros2 launch litegrip_urdf ros2_control.launch.py
```

| Argument | Default | Description |
| --- | --- | --- |
| `hardware_plugin` | `mock_components/GenericSystem` | ros2_control hardware interface plugin |
| `stroke` | `0.042726` | Per-finger travel (m) — measured value |
| `effort` | `10.0` | Joint maximum effort (N) |
| `velocity` | `0.2` | Joint maximum velocity (m/s) |

The default hardware plugin is `mock_components/GenericSystem`, which echoes each
position command straight back as state. The gripper does not physically move in this
mode, but `controller_manager`, controller loading, resource claiming, and the full
command/state interface pipeline behave exactly as they do with real hardware — which
makes it the right way to validate an integration before a device is available.

Resulting graph:

| Node | Role |
| --- | --- |
| `/robot_state_publisher` | Publishes TF from `/joint_states` |
| `/controller_manager` | Loads and manages controllers |
| `/joint_state_broadcaster` | Publishes `/joint_states` |
| `/gripper_controller` | `position_controllers/JointGroupPositionController` |

Verify the pipeline:

```bash
ros2 control list_controllers
# Both joint_state_broadcaster and gripper_controller must report [active].

ros2 control list_hardware_interfaces
# 2 command interfaces (claimed) + 4 state interfaces = 6 total.

# Command the gripper (order: right finger, left finger)
ros2 topic pub --once /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.042726, 0.042726]}"

ros2 topic echo /joint_states
```

> ⚠️ **The mock hardware does not clamp out-of-range commands.** In the configuration
> above, `[0.05, 0.05]` exceeds `stroke = 0.042726` and is echoed back as `0.05` without
> error or clamping, despite the `min`/`max` parameters declared on the command
> interface. The travel limits are descriptive metadata in this configuration, not an
> enforced constraint. Clamp commands in your own application layer.
>
> ℹ️ `/joint_states` reports `effort: [nan, nan]`. The mock hardware declares no effort
> state interface, so no value exists to publish. This is expected and not an error.

### 3. Gazebo simulation

> ⚠️ **This launch file has never been executed.** Gazebo is not installed in the
> environment where this package was verified. Treat the first run as a debugging
> session and confirm that the model spawns correctly and both controllers activate.

```bash
ros2 launch litegrip_urdf gazebo.launch.py
```

This launch forces `hardware_plugin:=gazebo_ros2_control/GazeboSystem` and starts Gazebo,
spawns the model, then activates `joint_state_broadcaster` followed by `gripper_controller`.

---

## Interfaces

### Joints

| Joint | Type | Axis | Origin in `base_link` | Limit |
| --- | --- | --- | --- | --- |
| `gripper_slide_joint_right` | prismatic | `+X` | `(-0.067, 0.0010833, 0.034083)` | `[0, 0.042726]` m |
| `gripper_slide_joint_left` | prismatic | `-X` | `( 0.067, -0.0010833, 0.034083)` | `[0, 0.042726]` m |

### Links

| Link | Parent | Joint | Mass |
| --- | --- | --- | --- |
| `base_footprint` | — | root, no inertia | 0 |
| `base_link` | `base_footprint` | `base_footprint_joint` (fixed) | 0.5063 kg |
| `gripper_slider_link1` | `base_link` | `gripper_slide_joint_right` | 0.03545 kg |
| `gripper_slider_link2` | `base_link` | `gripper_slide_joint_left` | 0.03545 kg |

`base_footprint` is an inertia-free dummy root coincident with `base_link`. It exists to
give the TF tree a valid root: KDL does not support a root link carrying inertia, and
would emit a `root link has an inertia` warning and silently ignore `base_link`'s inertia.
**Attach the gripper to a robot arm at `base_footprint`.**

### ros2_control interfaces

| Joint | Command interfaces | State interfaces |
| --- | --- | --- |
| `gripper_slide_joint_right` | `position` | `position`, `velocity` |
| `gripper_slide_joint_left` | `position` | `position`, `velocity` |

**6 interfaces in total per copy of the model.** (An earlier revision of this document
stated 4; the correct count is 2 command + 4 state.)

### Controller

`position_controllers/JointGroupPositionController` on `/gripper_controller`.

The command array order is the order in `config/litegrip_controllers.yaml`:

| Index | Joint |
| --- | --- |
| `[0]` | `gripper_slide_joint_right` |
| `[1]` | `gripper_slide_joint_left` |

---

## ⚠️ Joint sign convention — read before writing a controller

**The two joints have opposite `axis` directions: right is `+X`, left is `-X`.
Therefore both joints take the *same sign* to move the fingers symmetrically.**

| Command | Result |
| --- | --- |
| `[0.0, 0.0]` | Fully open — model inner faces at `x = ∓0.0435`, model opening **87 mm**; this gripper calipers at **86.960 mm** |
| `[0.02, 0.02]` | Partially closed |
| `[0.042726, 0.042726]` | Measured closed calibration position — this gripper calipers at a **1.508 mm** gap |

**Writing a controller on the intuition that the two values should have opposite signs
will drive the fingers in opposite directions instead of together.** This has been
confirmed by direct measurement: at `[0, 0]` the finger origins sit at `x = ∓0.067`
(model inner faces at `∓0.0435`), and at the mesh-theoretical closure `0.0435` they would
sit at `x = ∓0.0235` (inner faces at `x = 0`, zero gap). The shipped limit `0.042726`
stops just short of that, at the measured closed position.

### Why the travel limit is 0.042726 and not 0.067

Two different numbers are in play here. Do not conflate them.

**Mesh-theoretical closure `0.0435`** is derived from the CAD geometry:

```text
gripper_slider_link1.STL X range = [-0.00095, +0.0235]   (bounding box, measured)
joint origin x                   = -0.067
=> stroke = 0.067 - 0.0235       =  0.0435
```

That is the joint value at which the two inner faces would meet exactly at `x = 0`, i.e.
zero gap. It is a property of the CAD geometry, not of the physical unit.

**Measured per-finger travel `0.042726 m`** is the value this package ships as the
`stroke` default. Caliper measurement of this gripper gives a total mechanical stroke of
`85.452 mm`, i.e. `42.726 mm` per finger, and a closed clearance of `1.508 mm`. Because
the real gripper does not reach the ideal zero-gap closure, the measured value is smaller
— the conservative direction.

At `stroke = 0.067` the two fingers would fully overlap and interpenetrate. The
SolidWorks CSV declares `Limit Upper = 0.067` for the right finger and `-0.067` for the
left; both are unusable as exported. Full derivation in
[docs/design-notes.md](docs/design-notes.md#gripper-geometry).

> ⚠️ Changing the limit to `0.042726` changes both travel endpoints of the model. The
> mesh and TF checks recorded below were performed at the mesh-theoretical `0.0435`, so
> the model's new endpoints still need a runtime mesh/TF re-verification before they can
> be called geometrically verified.

---

## Configuration

`urdf/litegrip_urdf.urdf.xacro` is parameterized by xacro arguments:

| Argument | Default | Description |
| --- | --- | --- |
| `stroke` | `0.042726` | Per-finger travel (m) — the joint limit `upper`; measured value |
| `effort` | `10.0` | Maximum joint effort (N) ⚠ placeholder |
| `velocity` | `0.2` | Maximum joint velocity (m/s) ⚠ placeholder |
| `joint_damping` | `0.05` | Joint damping ⚠ placeholder |
| `joint_friction` | `0.02` | Joint friction ⚠ placeholder |
| `hardware_plugin` | `mock_components/GenericSystem` | ros2_control hardware plugin |

**Overriding arguments.** `stroke`, `effort`, and `velocity` are exposed as launch
arguments by both `display.launch.py` and `ros2_control.launch.py`, so they can be set on
the command line. `joint_damping` and `joint_friction` are **not** exposed by any launch
file — to change them you must either edit the xacro defaults or invoke `xacro` directly.

Expand to plain URDF for tools that do not support xacro:

```bash
xacro $(ros2 pkg prefix litegrip_urdf)/share/litegrip_urdf/urdf/litegrip_urdf.urdf.xacro \
  -o /tmp/litegrip_urdf.urdf
```

### Calibration required

`effort = 10.0` N and `velocity = 0.2` m/s are **SolidWorks export defaults, not measured
values**. Until they are replaced with calibrated figures, any torque or velocity limiting
derived from `<limit>` is incorrect. `joint_damping` and `joint_friction` are conservative
initial values chosen only to damp simulation oscillation and should likewise be
calibrated against the real mechanism.

→ **[Calibration Guide](docs/calibration-guide.md)** — the complete step-by-step procedure
for measuring these values, from the physical gripper through the Python SDK to the xacro
arguments above.

---

## Connecting real hardware

Substitute your vendor's ros2_control hardware interface plugin for the mock:

```bash
ros2 launch litegrip_urdf ros2_control.launch.py hardware_plugin:=<vendor_plugin_name>
```

Your plugin must provide, for both joints:

- a `position` **command** interface
- `position` and `velocity` **state** interfaces

This package ships no vendor plugin. If your hardware exposes `velocity` or `effort`
commands instead of `position`, the `<ros2_control>` block in the xacro and the controller
type in `config/litegrip_controllers.yaml` both need to change.

---

## Pre-release checklist

The following are **incomplete** and must be resolved before this package is published:

1. **Maintainer identity** — `package.xml` still carries `<maintainer email="TODO@example.com">LiteGrip</maintainer>`.
   Replace it with the real, legally correct entity and contact address.
2. **License undecided** — no license has been chosen for this package. `package.xml`
   carries `<license>TODO</license>` only because ROS 2 rejects a package without a
   license tag; it is not a legal statement.
3. **URLs** — `package.xml` `<url>` entries point at `https://example.com/litegrip`.
4. **`effort` / `velocity` calibration** — see [Calibration required](#calibration-required).
5. **`joint_damping` / `joint_friction` calibration** — see [Calibration required](#calibration-required).
6. **Gazebo launch validation** — `gazebo.launch.py` has never been run.

## Known limitations

- **Collision geometry reuses the high-precision visual STL.** `base_link.STL` is ~925 KB.
  With only 3 links the collision-checking cost is acceptable, but for
  performance-sensitive integration replace the `<collision>` geometry with simplified
  primitives (box/cylinder).
- **No gripper action interface.** The default `JointGroupPositionController` accepts
  a joint array over a topic. An Action-based interface would require
  `position_controllers/GripperActionController`, which accepts only a *single* joint and
  therefore needs a `<mimic>` joint for the second finger — and `<mimic>` does not take
  effect automatically in ros2_control. This is why the multi-joint controller is the
  default.
- **No `.stl` → simplification, no collision padding, no `<safety_controller>` limits,
  no transmissions.** The original SolidWorks export defined none of these.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/calibration-guide.md](docs/calibration-guide.md) | Step-by-step procedure to replace every placeholder value with a measured one — stroke, angle range, force, speed, damping, friction |
| [docs/design-notes.md](docs/design-notes.md) | Geometry derivation, joint conventions, revision history against the SolidWorks export, rationale for design decisions |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Known failure modes and their resolutions, including the Conda build failure and the `controller_manager` naming pitfall |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
