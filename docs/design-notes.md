# Design Notes

Why `litegrip_urdf` is built the way it is: the derivation of its geometry, the
conventions a consumer must respect, and the complete record of what was changed
relative to the original SolidWorks export.

**English** · [简体中文](design-notes.zh-CN.md)

---

## Source lineage

The URDF was not written by hand. It descends from a SolidWorks URDF Exporter run, and
three intermediate files exist in the original export. Understanding which file descends
from which matters, because the commonly circulated "original" values come from different
stages of that chain.

| Stage | File | State |
| --- | --- | --- |
| 1 | `夹爪urdf2.csv` | SolidWorks source of truth. Both joints are named `gripper_slide_joint` — **duplicate, illegal**. Travel limits `0.067` (right) and `-0.067` (left). |
| 2 | `夹爪urdf改前.urdf` | Joint names still duplicated. Limits `0.067` / `-0.067`. **Fails to parse:** `joint 'gripper_slide_joint' is not unique`. |
| 3 | `夹爪urdf2 (1).urdf` | Names split into `_right` / `_left`. Limits both written as `0.043.5` — a typo with a second decimal point. **Fails to parse:** `upper value (0.043.5) is not a valid float`. |
| 4 | `litegrip_urdf` (this package) | Parses cleanly. Limits parametrized as `0.0435`. |

Both parse failures were confirmed by running `check_urdf` against the respective files.
Note that stage 3 already attempted to correct the travel limit — but the intermediate
value `0.043.5` is unparseable, so neither intermediate file is usable as a reference.
**The geometry and inertia numbers in this package are byte-identical to the SolidWorks
export; only the defects listed below were repaired.**

---

## Gripper geometry

### Coordinate frame

Both fingers slide along the X axis of `base_link`. The joint origins are mirrored:

| Joint | Origin in `base_link` | Axis |
| --- | --- | --- |
| `gripper_slide_joint_right` | `(-0.067, 0.0010833, 0.034083)` | `+X` |
| `gripper_slide_joint_left` | `( 0.067, -0.0010833, 0.034083)` | `-X` |

### Deriving the travel limit

The SolidWorks export declares `Limit Upper = 0.067` for the right finger. That value is
wrong and would drive the fingers through each other. The correct travel is derived from
the finger mesh bounding box.

Measured from `meshes/gripper_slider_link1.STL` (binary STL, all triangle vertices):

```text
X range = [-0.00095, +0.0235]
```

The right finger's joint origin sits at `x = -0.067`, so at joint value `q` the mesh
occupies:

```text
x_min(q) = -0.067 + q - 0.00095
x_max(q) = -0.067 + q + 0.0235      <- inner face of the right finger
```

The gripper closes when the two inner faces meet at `x = 0`. Solving `x_max(q) = 0`:

```text
q = 0.067 - 0.0235 = 0.0435
```

Hence `stroke = 0.0435` m. The left finger is the mirror image and shares the same value.

**If `upper` were left at `0.067`, the fingers would overlap by 0.0235 m and
interpenetrate completely.** Do not revert this value.

### Verified behaviour at both travel limits

Measured via `tf2_echo base_footprint <link>` against a running `robot_state_publisher`:

| Command | Finger origins | Inner faces | Opening |
| --- | --- | --- | --- |
| `[0.0, 0.0]` | `x = ∓0.067` | `x = ∓0.0435` | **87 mm** |
| `[0.0435, 0.0435]` | `x = ∓0.0235` | `x = 0` | 0 (closed) |

The values in the "Finger origins" column match the joint origins in the URDF exactly at
`q = 0`, which confirms the joint origins and the mesh bounding box are consistent.

---

## Joint sign convention

**This is the single most common source of integration bugs with this model.**

The two joints have opposite axis directions (`+X` and `-X`). Because
`JointGroupPositionController` applies each value to its own joint along that joint's own
axis, **both entries must carry the same sign** to move the fingers symmetrically:

| Command | Result |
| --- | --- |
| `[0.0, 0.0]` | Fully open |
| `[0.0435, 0.0435]` | Fully closed |
| `[0.02, -0.02]` | ❌ Fingers move in the same direction — not a grasp |

The opposite axes are a property of the CAD model, not a defect introduced here; the
SolidWorks CSV declares `Joint Axis X = 1` for one finger and `-1` for the other. Because
`lower = 0` and `upper = 0.0435` for both joints, a symmetric "one positive, one negative"
command is not merely wrong but out of range for one of the joints.

---

## Why `base_footprint` exists

The SolidWorks export declared `base_link` as the root link, and `base_link` carries
inertia. KDL — and therefore MoveIt and most TF consumers — **does not support a root link
with inertia**: it emits `root link has an inertia` and silently discards that inertia.

The fix is a massless, inertia-free `base_footprint` link, coincident with `base_link`
and connected by a fixed joint. The TF tree then has a legal root, and `base_link`'s
inertia is preserved as a non-root link.

Two consequences:

1. **Attach the gripper to a robot arm at `base_footprint`**, not `base_link`.
2. **Do not also publish a static transform between them.** The original ROS 1
   `gazebo.launch` published `tf_footprint_base` with the arguments
   `0 0 0 0 0 0 base_link base_footprint` — note that `tf2`'s `static_transform_publisher`
   takes `frame_id child_frame_id` in that order, so this declared `base_link` as the
   *parent* of `base_footprint`. Since the URDF already defines `base_footprint` as the
   root with `base_link` as its child, publishing it would give the TF tree two parents
   for the same pair of frames. That node was removed.

The RViz configuration uses `base_footprint` as its fixed frame.

---

## Revision history against the SolidWorks export

Everything below is a repair. **No geometric or inertial value was altered.**

| # | Revision | Reason |
| --- | --- | --- |
| 1 | `<limit upper="0.043.5">` → parametrized `0.0435` | `0.043.5` is not a valid float; the export did not parse at all |
| 2 | Joint `gripper_slide_joint` → `gripper_slide_joint_right` / `_left` | Both joints carried the same name, which is illegal |
| 3 | Left finger `upper` `-0.067` → `0.0435` | Negative upper bound with `lower = 0` is an invalid range |
| 4 | Added inertia-free root `base_footprint` | Removes the KDL `root link has an inertia` warning; see above |
| 5 | Filled in empty material names (`name=""`) | Empty names are invalid; now `litegrip_base` and `litegrip_finger` |
| 6 | Added `<dynamics damping friction>` | The export defined none; needed to damp simulation oscillation |
| 7 | Added the `<ros2_control>` block | Required for any ros2_control integration |
| 8 | Package renamed `夹爪urdf2` → `litegrip_urdf` | ROS 2 package names must be lowercase alphanumeric/underscore |
| 9 | `config/joint_names_*.yaml` corrected | The export contained an empty-string placeholder and a duplicated entry: `['', 'gripper_slide_joint', 'gripper_slide_joint', ]` |
| 10 | Dropped the extra `base_link → base_footprint` static transform | Direction was reversed and it would conflict with the URDF's root link; see above |
| 11 | Completed `package.xml` dependencies | The export omitted `gazebo_ros`, `tf`, `rostopic`, and `joint_state_publisher` |

Items 1–3 were each confirmed by attempting to parse the corresponding source file; see
[Source lineage](#source-lineage).

---

## Mass properties

Carried over unmodified from the SolidWorks export. Total mass **0.5772 kg**.

| Link | Mass | ixx | iyy | izz |
| --- | --- | --- | --- | --- |
| `base_link` | 0.506299 kg | 1.40520e-04 | 3.08493e-04 | 3.45331e-04 |
| `gripper_slider_link1` | 0.0354537 kg | 1.73251e-05 | 1.26496e-05 | 6.96030e-06 |
| `gripper_slider_link2` | 0.0354537 kg | 1.73251e-05 | 1.26496e-05 | 6.96030e-06 |

The two fingers are mirror images: their inertia tensors are identical in `ixx`, `iyy`,
`izz`, and their products of inertia differ in sign on `ixz` and `iyz`, as expected.

Full tensors, including centres of mass and products of inertia, are in
[`urdf/litegrip_urdf.urdf.xacro`](../urdf/litegrip_urdf.urdf.xacro).

---

## Design decisions

### Why `JointGroupPositionController` and not `GripperActionController`

A gripper naturally wants an action interface — "close until stalled" is the operation
callers actually want. The obstacle is that `GripperActionController` accepts exactly
**one** joint. Driving two fingers with it would require a `<mimic>` joint on the second
finger, and **`<mimic>` does not take effect automatically in ros2_control** — it depends
on support from the hardware interface or simulator, which not every vendor plugin
provides.

`JointGroupPositionController` takes a joint array and needs no mimic support, so it works
uniformly across mock, Gazebo, and real hardware. The trade-off is that callers must send
a `Float64MultiArray` over a topic rather than calling an action. If you want the action
interface and your hardware supports `<mimic>`, that substitution is a supported change.

### Why collision geometry reuses the visual STL

The export points `<collision>` at the same meshes as `<visual>`. With three links the
cost is acceptable, and it guarantees that collision bounds match the rendered geometry
exactly. `base_link.STL` is ~925 KB, so if this model is integrated into a
performance-sensitive scene (many grippers, or a high-rate collision checker), replace the
`<collision>` meshes with primitives.

### What this package deliberately does not contain

No meshes were simplified, no collision padding was added, no `<safety_controller>` limits
were set, and no transmissions were defined. The SolidWorks export defined none of these,
and inventing values would have made the package appear more specified than it is. The
`effort` and `velocity` limits are export defaults and are flagged as uncalibrated in both
the xacro and the README.
