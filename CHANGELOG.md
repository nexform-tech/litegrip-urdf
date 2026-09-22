# Changelog

All notable changes to this package are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Change categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

> This changelog is maintained in English so that it stays readable to the widest
> audience across releases. The usage documentation is available in both
> [English](README.md) and [简体中文](README.zh-CN.md).

---

## [Unreleased]

### Added

- `docs/calibration-guide.md` and `docs/calibration-guide.zh-CN.md` — step-by-step
  procedure for measuring every placeholder value: mechanical stroke, angular range,
  `rad_to_mm`, position accuracy, grip force, speed, and the simulation-only damping and
  friction terms.
- `docs/design-notes.md` and `docs/design-notes.zh-CN.md` — geometry derivation,
  joint conventions, source lineage, and the complete revision record against the
  SolidWorks export.
- `docs/troubleshooting.md` and `docs/troubleshooting.zh-CN.md` — known failure modes
  and their resolutions.
- `.gitignore` — colcon build artifacts, Python caches, ROS runtime files, and editor
  and OS cruft.
- `.markdownlint.json` — lint configuration shared with the other repositories.
- `README.zh-CN.md` — Simplified Chinese translation of the README.
- `CHANGELOG.md` — this file.

### Changed

- Recorded the current physical calibration result: closed clearance `1.508 mm`, open
  opening `86.960 mm`, total mechanical stroke `85.452 mm`, per-finger URDF stroke
  `0.042726 m`, closed/open motor angles `0.041390` / `-1.272793 rad`, angular range
  `1.314183 rad`, and `rad_to_mm = 65.0229 mm/rad`.
- Recorded three stable `calibrate_guided` measurements and five endpoint rechecks. The
  rechecked mechanical stroke was `85.43–85.47 mm`, and the corresponding
  `rad_to_mm` values were `65.0053–65.0372 mm/rad`.
- Recorded the six-point caliper position test and the 50-cycle repeatability data. The
  position test remains pending final acceptance because the 20 mm group contains an
  `18.80 mm` reading, which produces a `1.20 mm` maximum absolute error. In the 50-cycle
  test over `2 mm ↔ 83 mm`, the closed/open opening drift was `+0.01` / `+0.02 mm`, and
  both endpoint angle drifts were `+0.000009 rad`.
- Updated the xacro and launch defaults from the old nominal `0.0435 m` to the measured
  `0.042726 m` per-finger stroke. Force, speed, damping, friction, hardware integration,
  the `calibrate_guided` source logic, and runtime Gazebo/TF validation remain uncalibrated
  or unverified.
- `README.md` is now written in English as the repository default; the previous Chinese
  content was revised and moved to `README.zh-CN.md`. Both versions cross-link.

### Fixed

- Documentation errors in the previous README:
  - The ros2_control interface count was stated as 4. Loading the model declares
    **2 command interfaces and 4 state interfaces — 6 in total**.
  - `joint_damping` and `joint_friction` were listed as overridable "in launch". No launch
    file in this package exposes them; they can only be changed in the xacro defaults or
    by invoking `xacro` directly.
  - The claim that `gui:=false` merely hides the slider window was incomplete — it removes
    the finger links from TF entirely, because `joint_state_publisher_gui` is the only
    publisher of `/joint_states` in `display.launch.py`.
  - The revision record attributed the `0.067` travel limit to a single source file. The
    export contains two distinct intermediate URDFs, each failing for a different reason.

### Documented

- The mock hardware plugin does not clamp out-of-range position commands; travel limits
  are descriptive metadata, not an enforced constraint.
- `/joint_states` reports `NaN` for `effort`, because no effort state interface is
  declared.
- `gazebo.launch.py` remains unexecuted — Gazebo is not installed in the verification
  environment.
- The Python SDK's calibration routine does not measure the gripper's stroke: it derives
  its mm scale by dividing an **assumed** stroke by the measured angular range. The
  shipped assumption is 120 mm while the measured total mechanical stroke of this gripper
  is 85.452 mm (42.726 mm per finger), so as shipped every millimetre reading is about
  1.404× too large. Eight further
  inconsistencies in the SDK are catalogued in
  [docs/calibration-guide.md](docs/calibration-guide.md#known-inconsistencies-in-the-sdk).

---

## [1.0.0] — 2026-09-15

Initial versioned state of the package: ported from a ROS 1 `catkin` description package
produced by the SolidWorks URDF Exporter, and rebuilt as a ROS 2 `ament_cmake` description
package.

### Added

- `urdf/litegrip_urdf.urdf.xacro` — parameterized robot description, with `stroke`,
  `effort`, `velocity`, `joint_damping`, `joint_friction`, and `hardware_plugin` as
  xacro arguments.
- `launch/display.launch.py` — RViz visualization with `joint_state_publisher_gui`.
- `launch/ros2_control.launch.py` — ros2_control pipeline with
  `mock_components/GenericSystem` as the default hardware plugin.
- `launch/gazebo.launch.py` — Gazebo Classic simulation target. **Not verified**; Gazebo
  was not installed in the verification environment.
- `config/litegrip_controllers.yaml` — `joint_state_broadcaster` and a
  `position_controllers/JointGroupPositionController` on `/gripper_controller`.
- `config/joint_names_litegrip_urdf.yaml` — joint name list for MoveIt Setup Assistant.
- `config/litegrip_urdf.rviz` — RViz configuration using `base_footprint` as fixed frame.
- `<ros2_control>` block declaring `position` command interfaces and `position`/`velocity`
  state interfaces for both joints.
- `base_footprint` — inertia-free root link, removing the KDL `root link has an inertia`
  warning and preserving `base_link`'s inertia as a non-root link.

### Fixed

Repairs carried out relative to the SolidWorks export. **No geometric or inertial value
was altered.** Full rationale in [docs/design-notes.md](docs/design-notes.md#revision-history-against-the-solidworks-export).

- Invalid joint limit `upper="0.043.5"` — not a valid float; the export could not be parsed
  by any URDF parser.
- Duplicate joint name `gripper_slide_joint` — renamed to `gripper_slide_joint_right` and
  `gripper_slide_joint_left`.
- Invalid negative limit `upper="-0.067"` on the left finger with `lower="0"`.
- Empty material names (`name=""`).
- Missing `<dynamics>` damping and friction.
- Missing `<ros2_control>` hardware interface definitions.
- Package renamed from `夹爪urdf2` to `litegrip_urdf` — ROS 2 requires lowercase
  alphanumeric and underscore package names.
- `config/joint_names_*.yaml` contained an empty-string placeholder and a duplicate entry
  (`['', 'gripper_slide_joint', 'gripper_slide_joint', ]`).
- Removed the redundant `base_link → base_footprint` static transform from the Gazebo
  launch: its direction was reversed, and publishing it would have given the TF tree two
  parents for the same pair of frames.
- `package.xml` dependency declarations completed (`gazebo_ros`, `tf`, `rostopic`,
  `joint_state_publisher` were missing).

### Changed

- Build system migrated from `catkin` (`package format="2"`) to `ament_cmake`
  (`package format="3"`).

---

[Unreleased]: https://example.com/litegrip/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/litegrip/releases/tag/v1.0.0