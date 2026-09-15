# Troubleshooting

Known failure modes for `litegrip_urdf` and how to resolve them. Each entry states the
symptom, the cause, and the fix — and, where it was reproduced, the exact command output
that identifies it.

**English** · [简体中文](troubleshooting.zh-CN.md)

---

## Conda `python3` breaks the build

**Symptom.** `colcon build` fails immediately:

```text
ModuleNotFoundError: No module named 'catkin_pkg'
CMake Error at .../ament_package_xml.cmake:95 (message):
  execute_process(/home/<user>/miniconda3/bin/python3
  .../package_xml_2_cmake.py ...) returned error code 1
```

The giveaway is the interpreter path in the error — a Conda prefix, not `/usr/bin/python3`.

**Cause.** A Conda environment is on `PATH`, so CMake resolves `Python3_EXECUTABLE` to a
Conda interpreter that has no ROS 2 Python packages installed. This is an environment
problem, not a defect in this package — it affects any `ament_cmake` package.

**Fix.** Point CMake at the system interpreter:

```bash
colcon build --packages-select litegrip_urdf \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
```

Alternatively, deactivate the Conda environment before building
(`conda deactivate`), or remove the Conda `bin` directory from `PATH` for the build shell.
Do not `pip install catkin_pkg` into the Conda environment — that produces a mixed
interpreter environment that fails in less obvious ways later.

---

## `gui:=false` removes the finger links from TF

**Symptom.** With `ros2 launch litegrip_urdf display.launch.py gui:=false`:

- `tf2_echo base_footprint base_link` succeeds — translation `[0, 0, 0]`.
- `tf2_echo base_footprint gripper_slider_link1` hangs, reporting
  `Invalid frame ID "gripper_slider_link1"`.

**Cause.** `joint_state_publisher_gui` is the only node in `display.launch.py` that
publishes `/joint_states`. With `gui:=false` nothing publishes joint states, so
`robot_state_publisher` has no value for the two prismatic joints and cannot compute their
transforms. The fixed `base_footprint → base_link` transform is unaffected because it does
not depend on joint state. `ros2 topic info /joint_states` reports `Publisher count: 0`.

**Fix.** Start the headless publisher alongside the launch:

```bash
ros2 run joint_state_publisher joint_state_publisher
```

All three frames then resolve.

---

## The mock hardware does not clamp out-of-range commands

**Symptom.** Commanding beyond the declared travel limit is accepted silently.

```bash
ros2 topic pub --once /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.05, 0.05]}"   # stroke is 0.0435
ros2 topic echo --once /joint_states
# position:
# - 0.05
# - 0.05
```

**Cause.** `mock_components/GenericSystem` echoes each position command back as state
without validating it against the `min`/`max` parameters declared on the command
interface. With this hardware plugin, the travel limits are descriptive metadata rather
than an enforced constraint. Expect the same from any hardware plugin that does not
implement its own limits.

**Fix.** Clamp commands in your own application layer before publishing them. Do not
assume the controller or the hardware will reject an out-of-range value.

---

## `effort` is `nan` in `/joint_states`

**Symptom.**

```text
effort:
- .nan
- .nan
```

**Cause.** The `<ros2_control>` block declares only `position` and `velocity` state
interfaces. The mock hardware has no effort value to publish.

**Fix.** None needed — this is expected. If a downstream consumer requires numeric effort,
either add an `effort` state interface and provide it from your hardware plugin, or
filter the `NaN` in the consumer.

---

## `'joints' parameter was empty` / controllers will not configure

**Symptom.** The controller manager reports that a controller could not be configured,
with `'joints' parameter was empty`, even though `config/litegrip_controllers.yaml`
clearly lists the joints.

**Cause.** Two distinct mistakes produce this — check both:

**Cause 1 — parameter nesting.** Controller parameters must live in their **own
top-level node section**, keyed by controller name:

```yaml
# ✅ Correct
gripper_controller:
  ros__parameters:
    joints: [gripper_slide_joint_right, gripper_slide_joint_left]
```

Not nested underneath `controller_manager`:

```yaml
# ❌ Wrong — controller_manager reads only `type` from here
controller_manager:
  ros__parameters:
    gripper_controller:
      joints: [...]      # never forwarded to the controller node
```

**Cause 2 — a `__node` remap inherited by controllers.** Do not pass an explicit
`name='controller_manager'` to the `ros2_control_node` action in a launch file. Doing so
makes `launch_ros` append `-r __node:=controller_manager`, and `controller_manager`
propagates that remap to the controller nodes it creates at runtime. Every controller then
announces itself as `/controller_manager`, so the top-level YAML sections in Cause 1 can
no longer match any node. The current `ros2_control.launch.py` omits the `name=` argument
deliberately — see the comment at the `controller_manager_node` definition.

---

## `root link has an inertia` warning from KDL

**Symptom.** MoveIt or a KDL-based tool warns that the root link has inertia, and
`base_link`'s inertia appears to be ignored.

**Cause.** KDL requires an inertia-free root link. In the original SolidWorks export,
`base_link` was the root *and* carried inertia, so its inertia was silently discarded.

**Fix.** Already applied: the model defines an inertia-free `base_footprint` root with a
fixed joint to `base_link`. If you see this warning with the current model, you are
loading a different URDF — most likely an unexpanded copy of the original export.

**Do not** additionally publish a static transform between `base_footprint` and
`base_link`; the URDF already relates them, and a second definition gives the TF tree two
parents for the same frames.

---

## `gazebo.launch.py` fails to start

**Symptom.** The launch aborts with `package 'gazebo_ros' not found`, or Gazebo starts but
the model never spawns.

**Cause.** Gazebo Classic is optional and is not installed by default. **It was not
installed in the environment where this package was verified, so `gazebo.launch.py` has
never been executed and must be treated as untested.**

**Fix.** Install the simulation dependencies:

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
```

Then run it, and verify in this order: (1) the model appears in Gazebo, (2)
`ros2 control list_controllers` shows `joint_state_broadcaster` as `active`, (3)
`gripper_controller` becomes `active`, (4) a commanded position produces actual finger
motion in the simulation.

---

## The original export files do not parse

**Symptom.** Loading a file from the original SolidWorks export into any URDF tool fails.

**Cause.** Both intermediate URDFs in the export are unparseable. Confirmed with
`check_urdf`:

| File | Error |
| --- | --- |
| `夹爪urdf改前.urdf` | `joint 'gripper_slide_joint' is not unique.` |
| `夹爪urdf2 (1).urdf` | `upper value (0.043.5) is not a valid float` |

**Fix.** Use `urdf/litegrip_urdf.urdf.xacro` from this package. Neither intermediate file
is usable as a reference — in particular, **do not copy the `0.067` travel limit from
them**; see [design-notes.md](design-notes.md#deriving-the-travel-limit) for the correct
derivation.

---

## Nothing appears in RViz

**Symptom.** RViz opens but the gripper is not visible, or the display reports a missing
transform.

**Cause.** The bundled configuration uses `base_footprint` as its fixed frame, so the
whole tree depends on `/tf` and `/robot_description` being published.

**Fix.** Confirm both:

```bash
ros2 topic echo --once /robot_description    # must return the URDF text
ros2 run tf2_ros tf2_echo base_footprint base_link
```

If `/robot_description` is empty, `robot_state_publisher` did not start or failed to
expand the xacro — check its console output. If the transform is missing while
`/robot_description` is present, see
[`gui:=false` removes the finger links from TF](#guifalse-removes-the-finger-links-from-tf).
