# Calibration Guide

Step-by-step procedure to replace every placeholder value in this package with a
measured one — from the physical gripper, through the Python SDK, to the URDF/xacro
parameters.

**English** · [简体中文](calibration-guide.zh-CN.md)

> **Read this first.** The SDK's calibration routine does **not** measure the gripper's
> stroke. It measures the motor's *angular* range and then derives the mm scale by
> **dividing an assumed stroke by that range**. As shipped, that assumed stroke is
> **120 mm**; the actual mechanical stroke of this gripper is **87 mm**. Until you correct
> it, every millimetre reading the SDK reports is **1.38× too large**. Step 2 exists solely
> to fix this, and it is not optional.

---

## What gets calibrated

| Quantity | Affects | Method | Tool | Written to |
| --- | --- | --- | --- | --- |
| Mechanical stroke | Everything downstream | Direct measurement | Digital caliper | `GripperConfig.max_stroke_mm`, URDF `stroke` |
| Angular range at the limits | mm scale | SDK driven to both hard stops | — | `travel_range_rad` in the calibration JSON |
| `rad_to_mm` | Every mm reading | Computed: `stroke / travel_range` | — | `rad_to_mm` in the calibration JSON |
| Position accuracy | Grasp reliability | Command and measure | Digital caliper | Acceptance record |
| N per Nm | Grip force accuracy | Load cell between the jaws | Force gauge | `UnitConversion.NM_TO_N` / `N_TO_NM` |
| Maximum grip force | URDF `effort` | Load cell, increasing torque | Force gauge | URDF `effort` |
| Maximum finger speed | URDF `velocity` | Timed travel over a measured distance | Caliper + stopwatch | URDF `velocity` |
| Joint friction | URDF `joint_friction` (**simulation only**) | Breakaway pull with the motor disabled | Force gauge | URDF `joint_friction` |
| Joint damping | URDF `joint_damping` (**simulation only**) | Force versus speed sweep | Force gauge | URDF `joint_damping` |

`effort` and `velocity` are enforced constraints on real hardware. `joint_damping` and
`joint_friction` are read only by physics simulators — a ros2_control hardware interface
ignores them. Do not spend force-gauge time on damping and friction until the rest is done.

---

## Coordinate systems — read before touching anything

Three different position representations describe the same physical opening, and they do
not share a zero or a direction. Conflating them is the most likely way to produce a wrong
number.

| Representation | Fully closed | Fully open | Direction |
| --- | --- | --- | --- |
| **Motor position** (rad) | ≈ `+0.114` | ≈ `-1.491` | **Decreases** as the gripper opens |
| **SDK position** (mm) | `0` | `max_stroke_mm` (= 87) | Increases as the gripper opens |
| **URDF joint** `q` (m) | `0.0435` | `0.0` | **Decreases** as the gripper opens |

The rad values above are from the shipped factory calibration and must be re-measured in
Step 3.

**Conversions.** Let `p` be SDK position (mm), `q` the URDF joint value (m), `r` the motor
position (rad), `r_closed` the closed-limit rad value, and `k` = `rad_to_mm`.

```text
p = (r_closed - r) * k                    r = r_closed - p / k
q = 0.0435 * (1 - p / 87.0)               p = 87.0 * (1 - q / 0.0435)
```

Check the bridge against the geometry: `p = 0` (closed) gives `q = 0.0435` ✓; `p = 87`
(open) gives `q = 0` ✓.

---

## Prerequisites

**Power and wiring.** The motor needs a **24 V** supply to produce torque. CAN is powered
separately by the USB-CAN adapter, so the gripper will answer on the bus without 24 V — but
it will report `UV_FAULT` and refuse to move. If calibration appears to hang with position
readings that never change, check 24 V before anything else.

**Bring up CAN.** Classic CAN at 1 Mbps:

```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000 fd off
sudo ip link set can0 up
ip -details link show can0        # confirm state UP and bitrate 1000000
```

**Install the SDK.**

```bash
cd /path/to/lite-grip
pip install -e .
```

**Verify communication before calibrating.** Never start calibration on a bus you have not
confirmed:

```bash
python examples/can_diag.py --channel can0 --can-id 0x08
```

Expect valid status frames with plausible position values. If this fails, stop and fix the
link — calibration moves the gripper into hard stops and is the wrong place to discover a
flaky connection.

**Clear the workspace.** During Steps 3 and 4 the gripper drives itself into both mechanical
limits. Mount it securely or hold it so that nothing is between the jaws and nothing is in
the path of either finger. Keep fingers clear.

---

## Step 1 — Measure the true stroke

The stroke is the one quantity the SDK cannot discover. Measure it directly.

1. **Remove drive.** Enter zero-gravity mode so the jaws move freely:
   `gripper.enter_zero_gravity()`, or run the gripper in `manual` calibration mode
   (see Step 3, Option B). Power down is also acceptable if the mechanism does not
   self-lock.
2. **Close the jaws fully by hand** and hold them against the closed hard stop.
3. **Measure between the two inner faces** with the digital caliper at the finger tips.
   This is the zero reference — record it as `O_closed`. It should read **0.00 mm** for a
   correctly modelled gripper. A non-zero value means the jaws are not fully seated, or the
   hard stop is contaminated.
4. **Open the jaws fully by hand** against the open hard stop and measure again between the
   same two faces. Record as `O_open`.
5. **Compute the stroke:** `stroke = O_open − O_closed`.
6. **Repeat the close/open cycle 5 times** and record every reading. Take the mean as the
   stroke and the spread as your measurement uncertainty. A spread above ~0.3 mm indicates a
   loose mechanism or an inconsistent hand force — investigate before continuing.

Expected result for LiteGrip:

| Quantity | Expected |
| --- | --- |
| `O_open` (fully open, inner face to inner face) | **87.0 mm** |
| Per-finger travel | **43.5 mm** (= stroke / 2) |

The per-finger figure is what the URDF's `stroke` parameter holds (as `0.0435` m), because
the model has one prismatic joint per finger. The 87 mm figure is what the SDK's
`max_stroke_mm` holds, because SDK position spans the whole opening.

> If you measure something other than 87 mm, **stop**. Every constant in both the SDK and
> the URDF is derived from this number, and the geometric derivation in
> [design-notes.md](design-notes.md#deriving-the-travel-limit) is built on the mesh
> bounding box. A materially different measurement means the model and the hardware are
> different units; resolve that before calibrating either.

Record:

```text
O_closed  = ______ mm     (5 readings: ____ ____ ____ ____ ____)
O_open    = ______ mm     (5 readings: ____ ____ ____ ____ ____)
stroke    = O_open - O_closed = ______ mm        expected 87.0
per-finger travel = stroke / 2 = ______ mm       expected 43.5
```

---

## Step 2 — Correct the SDK's assumed stroke

The SDK derives its mm scale from an assumed stroke. That assumption is wrong and must be
fixed **before** any calibration run, otherwise you will bake a 1.38× scale error into the
saved calibration file.

There are two places to fix.

**2a. The configuration default** — `max_stroke_mm` is used by `calibrate()` and
`calibrate_manual()`:

```python
# litegrip/models.py, GripperConfig
max_stroke_mm: float = 87.0     # was 120.0
```

**2b. The hardcoded value in `calibrate_guided()`** — this method ignores the config
entirely and uses a literal:

```python
# litegrip/gripper.py, calibrate_guided()
rad_to_mm = 120.0 / travel      # was a literal 120.0
rad_to_mm = self._config.max_stroke_mm / travel     # fixed
```

Confirm no other occurrence remains:

```bash
grep -rn "120\.0" litegrip/gripper.py litegrip/models.py
```

Any remaining `120.0` in a position or conversion context is a defect. Cosmetic occurrences
in printed labels (for example `张开(120mm)`) and in docstrings should be corrected too, but
they do not affect behaviour — do not confuse the two when checking.

> **Why this matters.** `rad_to_mm = max_stroke_mm / travel_range`. With the assumed 120 mm
> and the measured 1.605 rad range, the shipped factory calibration records
> `rad_to_mm = 74.8`. With the true 87 mm the correct value is `87.0 / 1.605 = 54.21`.
> Every `goto(60.0)` under the wrong scale moves the gripper to a real opening of 43.5 mm,
> and `move_at_speed(speed_mm_s=40.0)` actually moves at 29 mm/s.

### Which APIs this does and does not affect

`rad_to_mm` sits only on the mm-facing surface. The rad-facing calls bypass it entirely, so
a wrong scale does **not** make the gripper collide with anything — it makes every
millimetre-denominated number wrong.

| API | Uses `rad_to_mm`? | Effect of a 1.38× too-large scale |
| --- | --- | --- |
| `get_state().position_mm`, `get_position()` | Yes | Reads 1.38× too large — a real 43.5 mm opening reports as 60 mm |
| `goto(position_mm)` | Yes | Target lands short: `goto(60)` reaches 43.5 mm |
| `move_at_speed(target_mm, speed_mm_s)` | Yes | Both target and speed scale down by 1.38× |
| `open()`, `close()`, `goto_rad()`, `move_to()` | **No** — these command radians | Unaffected; they still reach the true limits |
| `close(force_n=...)`, `set_force()` | **No** — torque domain | Unaffected by this constant; see Step 6 for force |
| `grasp()` | **No** — stall detection on radians | Unaffected |

So a mis-scaled calibration does not endanger the mechanism. It silently corrupts every
position you read and every mm-denominated command you send — which is harder to notice.

---

## Step 3 — Calibrate the angular range

Pick one method. All three drive the gripper to both hard stops and report
`travel_range_rad`; they differ in how much they trust the hardware to stop itself.

### Option A — Auto stall detection (`calibrate`)

Steps toward each limit and stops when the position stops changing. No operator
interaction. Drives into both hard stops under a probing stiffness.

```bash
python examples/calibrate.py --channel can0 --can-id 0x08 --kp 60 --step 0.1
```

Start with a low `--kp` (60) so the jaws meet the stop gently. Raise it only if stall
detection triggers early.

### Option B — Zero-gravity manual (`calibrate_manual`)

The motor goes limp; you move the jaws by hand. **Safest for a first calibration**, because
the gripper never drives itself into a stop.

```bash
python examples/calibrate_manual.py --channel can0 --mst-id 0x18 --mode manual --duration 30
```

Push the jaws fully closed, then fully open, and repeat several times during the 30 s window.
Watch the printed `open=` / `close=` extremes to confirm both limits were captured.

### Option C — Guided (`calibrate_guided`)

The gripper steps toward each limit at low stiffness and waits for you to confirm each one
with Enter. Use this if automatic stall detection is unreliable on your unit.

```bash
python examples/calibrate_manual.py --channel can0 --mst-id 0x18 --mode guided --kp 60
```

> **Do not run Option C until Step 2b is applied.** `calibrate_guided()` is the method with
> the hardcoded assumption; the other two read the config.

### Reading the result

Each method prints and returns a `CalibrationData`:

```text
闭合极限:   +0.114xxx rad  (0.0 mm)
张开极限:   -1.491xxx rad  (87.0 mm)
行程:        1.605xxx rad
转换系数:   54.2 mm/rad
```

Sanity checks before accepting:

| Check | Expected |
| --- | --- |
| `travel_range` | ≈ 1.6 rad, positive |
| Closed rad value | Positive, near `+0.11` |
| Open rad value | Negative, near `-1.49` |
| Open rad **less than** closed rad | Must hold — the sign convention is inverted relative to mm |
| Spread across 3 runs | Within ~0.01 rad. A larger spread means the stop detection is inconsistent. |

Run the calibration **three times** and compare `travel_range`. They should agree closely;
the mechanism is rigid, so a large run-to-run variation points at a detection problem
rather than real mechanical variation.

---

## Step 4 — Compute and verify `rad_to_mm`

If Steps 2 and 3 are done, the value is already correct:

```text
rad_to_mm = stroke_mm / travel_range_rad
          = 87.0 / 1.605
          = 54.21 mm/rad
```

**If you are patching an existing calibration file instead of re-running**, edit
`~/.litegrip/litegrip_calibration.json` directly. `load_calibration()` reads `rad_to_mm`
from the file, so this is the value that actually governs behaviour at runtime — the
`GripperConfig` default is not consulted once a calibration file loads:

```json
{
  "zero_position_rad": 0.114,
  "max_position_rad": -1.491,
  "travel_range_rad": 1.605,
  "rad_to_mm": 54.21
}
```

Recalculate `rad_to_mm` whenever `travel_range_rad` changes; never copy it across a
re-calibration.

### Three disagreeing values in the current codebase

Be aware that the repository currently contains three different mm-per-rad figures. Only
the last is correct:

| Source | Value | Basis |
| --- | --- | --- |
| `UnitConversion.RAD_TO_MM` in `constants.py` | 105.26 | `120 / 1.14` — assumes a 1.14 rad range that was never measured |
| `factory_calibration.json`, `rad_to_mm` | 74.8 | `120 / 1.605` — correct range, **wrong stroke** |
| Correct value for this gripper | **54.21** | `87.0 / 1.605` — measured stroke, measured range |

The 1.14 rad figure in `constants.py` matches neither the measured range nor the factory
file, and `UnitConversion.RAD_TO_MM` is not what `get_state()` uses at runtime. Treat it as
stale; do not use it as a reference.

---

## Step 5 — Verify position accuracy

Do not trust a calibration you have not measured against a caliper.

1. With the calibration loaded, command a series of positions and let each settle:
   `gripper.goto(p)` for `p` = 0, 20, 40, 60, 80, 87.
2. At each, measure the opening between the inner faces with the caliper.
3. Tabulate the error.

| Commanded (mm) | `get_state().position_mm` | Caliper (mm) | Error (mm) |
| --- | --- | --- | --- |
| 0 | ____ | ____ | ____ |
| 20 | ____ | ____ | ____ |
| 40 | ____ | ____ | ____ |
| 60 | ____ | ____ | ____ |
| 80 | ____ | ____ | ____ |
| 87 | ____ | ____ | ____ |

Acceptance: maximum absolute error below **0.5 mm**, with no systematic trend. The SDK's
specified repeatability is ±0.03 mm, but that is the motor's positioning repeatability, not
the calibration's absolute accuracy — do not hold the absolute figure to that standard.

**A constant offset** across all rows means `zero_position_rad` is off — the closed hard
stop was detected at the wrong point. **A proportional error** (small near 0, growing toward
87) means `rad_to_mm` is wrong — most likely the stroke assumption crept back in. Recheck
Step 2.

---

## Step 6 — Calibrate grip force

The SDK converts torque to newtons with a fixed constant:

```python
force_n = torque_nm * UnitConversion.NM_TO_N      # NM_TO_N = 10.0 as shipped
tau_ff  = force_n * UnitConversion.N_TO_NM        # N_TO_NM = 0.1 as shipped
```

`10.0` is an unverified nominal. The real ratio depends on the transmission — lead screw
pitch, gear ratio, linkage geometry — and must be measured.

**Procedure.**

1. Place the force gauge between the jaws, centred, on the same axis as the grasp.
2. Command a torque and read the steady-state force. Use the raw torque feed-forward so you
   are not also fighting the position loop:
   `gripper.set_force(force_n=F)` for a range of `F`, or drive `tau` directly through
   `send_mit_frame`.
3. Record the measured force against the commanded torque, not against the commanded
   newtons — the commanded newtons are themselves derived from the constant you are trying
   to find.
4. Repeat at 5–8 points spanning the working range, taking at least 3 readings each.
5. Fit `F_measured = k * tau`, forcing the fit through the origin (zero torque must give
   zero force).

   | Commanded `tau` (Nm) | Reading 1 (N) | Reading 2 (N) | Reading 3 (N) | Mean (N) |
| --- | --- | --- | --- | --- |
   | 0.1 | ____ | ____ | ____ | ____ |
   | 0.2 | ____ | ____ | ____ | ____ |
   | 0.3 | ____ | ____ | ____ | ____ |
   | 0.5 | ____ | ____ | ____ | ____ |
   | 0.8 | ____ | ____ | ____ | ____ |
   | 1.0 | ____ | ____ | ____ | ____ |

6. Set `NM_TO_N = k` and `N_TO_NM = 1/k` in `UnitConversion`.
7. **Maximum grip force** for the URDF is the highest force you measured at the torque you
   are willing to permit, not the value at the motor's torque ceiling. The DM4310 can
   deliver far more torque than the mechanism should absorb; pick the limit from the
   mechanism's rating, then record the force at that limit.

**Verification with weights.** Masses give you a force reference with no gauge calibration
to trust:

1. Grasp an object with a known mass `m` using `gripper.grasp(force_n=F)`.
2. Command increasing `F` until the object is held without slipping.
3. The minimum holding force must satisfy `F >= m * g / (2 * mu)`, where `mu` is the
   jaw-to-object friction coefficient. With unknown `mu` this gives a bound, not a precise
   value — useful for catching a gross scale error (a factor-of-10 mistake is obvious), not
   for setting the constant to three decimals.

> **Watch the temperature.** Sustained high-torque stalls heat the coil. Read
> `state.temperature_coil` and stop if it climbs past roughly 80 °C; `0xC` is a coil
> over-temperature fault.

---

## Step 7 — Calibrate speed, and derive the URDF `velocity`

The URDF `velocity` limit is **per finger**, in m/s. The SDK's `speed_mm_s` is the rate of
change of the whole opening. Each finger moves half as fast as the opening changes:

```text
per-finger speed = opening rate / 2
```

**Procedure.**

1. Open the gripper fully and let it settle.
2. Command a move at a known speed over a measurable distance:
   `gripper.move_at_speed(target_mm=0.0, speed_mm_s=40.0, ...)`.
3. Time it with a stopwatch, or log timestamps around the call.
4. Compute the achieved opening rate: `distance / elapsed`.
5. Repeat at 3–5 speeds and check that the achieved rate tracks the commanded rate.
   A consistent shortfall means the commanded speed exceeds what the mechanism can deliver
   — which is exactly the number you need.
6. **Find the true maximum** by commanding progressively higher speeds until the achieved
   rate stops increasing. That plateau is the mechanical maximum opening rate.

   | Commanded (mm/s) | Distance (mm) | Elapsed (s) | Achieved (mm/s) |
| --- | --- | --- | --- |
   | 20 | ____ | ____ | ____ |
   | 40 | ____ | ____ | ____ |
   | 60 | ____ | ____ | ____ |
   | 85 (spec) | ____ | ____ | ____ |

7. Convert to the URDF value:

```text
URDF velocity = (max opening rate mm/s) / 2 / 1000      [m/s]
```

With the specified 85 mm/s opening rate this gives `85 / 2 / 1000 = 0.0425 m/s`, against a
placeholder of `0.2` m/s. The placeholder is roughly 4.7× too high — a controller that
respects the limit would command moves the hardware cannot follow.

---

## Step 8 — Friction and damping (simulation only)

**Skip this step unless you are tuning Gazebo or another physics simulator.** These two
parameters are read only by simulators; a ros2_control hardware interface ignores
`<dynamics>`. They do not affect the real gripper's behaviour, limits, or safety.

Both are measured with the motor **disabled**, pulling a finger by hand with the force gauge.

**Friction** (`<dynamics friction>`, in N for a prismatic joint) is the breakaway force:

1. Disable the motor (`gripper.disable()`); confirm the finger moves freely.
2. Hook the force gauge to one finger and pull slowly along its axis of travel.
3. Record the **peak** force just before the finger starts to move. This is the static
   friction.
4. Repeat at least 5 times at different starting positions; take the median, not the mean —
   breakaway measurements have a long upper tail.
5. Record as `joint_friction` in newtons.

**Damping** (`<dynamics damping>`, in N·s/m) is the viscous term:

1. With the motor disabled, pull the finger at several steady speeds spanning the working
   range.
2. Record the steady force at each speed.
3. Fit a line: `F = friction + damping * v`. The **slope** is the damping coefficient.
4. Record as `joint_damping` in N·s/m.

| Speed (m/s) | Steady force (N) |
| --- | --- |
| 0.01 | ____ |
| 0.02 | ____ |
| 0.04 | ____ |
| 0.08 | ____ |

The shipped values (`joint_damping = 0.05`, `joint_friction = 0.02`) are conservative
placeholders chosen to damp simulation oscillation. They were not measured.

---

## Step 9 — Write the measured values into the package

| xacro argument | Source | How to obtain |
| --- | --- | --- |
| `stroke` | Step 1 | `stroke_mm / 2 / 1000` → `0.0435` m |
| `effort` | Step 6 | Maximum grip force at the permitted torque, in N |
| `velocity` | Step 7 | `(max opening rate mm/s) / 2 / 1000` |
| `joint_damping` | Step 8 | Fitted slope, N·s/m (**simulation only**) |
| `joint_friction` | Step 8 | Median breakaway force, N (**simulation only**) |

Edit the defaults in [`urdf/litegrip_urdf.urdf.xacro`](../urdf/litegrip_urdf.urdf.xacro):

```xml
<xacro:arg name="stroke"         default="0.0435"/>
<xacro:arg name="effort"         default="__._"/>    <!-- Step 6 -->
<xacro:arg name="velocity"       default="0.____"/>  <!-- Step 7 -->
<xacro:arg name="joint_damping"  default="0.____"/>  <!-- Step 8, sim only -->
<xacro:arg name="joint_friction" default="0.____"/>  <!-- Step 8, sim only -->
```

Then remove the corresponding ⚠ placeholders from the parameter table in
[README.md](../README.md#calibration-required) and update
[CHANGELOG.md](../CHANGELOG.md).

### A note on `effort` and the SDK's `force_n`

The URDF `effort` on a prismatic joint is the force that joint can exert along its axis —
that is, the force **one finger** applies to the object. The SDK's `force_n` is also
intended as the grip force. So the two should be numerically equal, with no factor of two
applied.

That equivalence is worth confirming during Step 6 rather than assuming: if the SDK's
`force_n` is calibrated as the *total* actuator force split across two fingers rather than
the jaw-to-object force, the URDF value must be halved. The load cell measures the
jaw-to-object force directly, so measure it and set `effort` from the measurement, not from
either convention.

---

## Step 10 — Record and verify

A calibration that is not recorded is not reproducible.

**Calibration record.** Fill this in and keep it with the unit:

```text
Serial / unit ID:            ______________________
Date:                        ______________________
Operator:                    ______________________

MEASURED
  stroke (inner face to inner face)     ______ mm      (5 readings: ____ ____ ____ ____ ____)
  per-finger travel                     ______ mm
  travel_range_rad (3 runs)             ______ / ______ / ______ rad
  rad_to_mm  = stroke / travel_range    ______ mm/rad
  NM_TO_N (k), fitted                   ______ N/Nm
  max opening rate                      ______ mm/s
  max grip force @ permitted torque     ______ N
  breakaway force (median, sim only)    ______ N
  damping slope (sim only)              ______ N·s/m

WRITTEN TO
  ~/.litegrip/litegrip_calibration.json   rad_to_mm = ______
  litegrip/models.py                      max_stroke_mm = ______
  litegrip/gripper.py                     calibrate_guided fixed: yes / no
  urdf/litegrip_urdf.urdf.xacro           stroke/effort/velocity/damping/friction = ______

VERIFICATION
  max position error over 0..87 mm      ______ mm     (accept < 0.5 mm, no trend)
  object held at force_n = ______ N, mass = ______ kg
```

**Repeatability check.** Run 50 open/close cycles with `examples/cycle_test.py`, then repeat
the Step 5 table. The error must not drift. Drift indicates mechanical wear, a slipping
coupling, or a hard stop that has moved — all of which invalidate the calibration.

**Re-calibrate when** the mechanism is disassembled, a hard stop is adjusted, the coupling
between the motor and the mechanism slips, the motor or its driver is replaced, or the
position error in Step 5 grows past 0.5 mm.

---

## Safety

- **Pinch hazard.** The jaws close with up to the maximum grip force you calibrate. Keep
  fingers out of the travel path whenever the motor is enabled, including during Step 3.
- **Calibration drives into hard stops.** Options A and C deliberately stall the motor
  against a mechanical limit. Use the lowest `kp` that still gives reliable stall detection.
- **Thermal.** Repeated stall tests heat the coil quickly. Read `temperature_coil` between
  runs and let the unit cool.
- **24 V.** Verify polarity and that the supply can source the stall current before
  connecting.
- **`close()` is not force-limited by the calibration.** The measured `NM_TO_N` only makes
  the `force_n` argument *accurate*; it does not add a safety limit. Clamp `force_n` and
  `tau` in your own application.

---

## Known inconsistencies in the SDK

These were found by reading the SDK at the revision paired with this package. They are
recorded here so you can tell a calibration problem from a code problem. None of them are
fixed by calibrating.

| # | Location | Issue | Effect |
| --- | --- | --- | --- |
| 1 | `models.py`, `GripperConfig.max_stroke_mm` | `120.0`, but the true stroke is 87 mm | All mm readings 1.38× too large once baked into `rad_to_mm` |
| 2 | `gripper.py`, `calibrate_guided()` | Hardcodes `120.0 / travel`, ignoring the config | Fixing the config alone does not fix this method |
| 3 | `gripper.py`, `home()` | Moves to the literal `POS_CLOSED_RAD = 0.0`, not `config.pos_closed_rad` | After calibration (closed ≈ `+0.114`), `home()` stops ~6 mm *open* rather than closing |
| 4 | `constants.py`, `POS_OPEN_RAD = 1.14` | Sign and magnitude disagree with the measured open limit (`≈ -1.491`) | Currently unused — dead constant, but misleading |
| 5 | `constants.py`, `UnitConversion.RAD_TO_MM = 105.26` | Assumes a 1.14 rad range that was never measured | Not used at runtime; three different mm/rad values circulate in the codebase |
| 6 | `models.py`, `GripperState.aperture_mm` | Docstring says "single-side displacement; for total jaw separation multiply by 2" | Contradicts `move_at_speed`'s "0=closed, 120=open" and the calibration math. The math treats `max_stroke_mm` as the **whole** opening; the docstring is wrong |
| 7 | `constants.py`, `UnitConversion.NM_TO_N = 10.0` | Unverified nominal | Grip force commands are approximate until Step 6 |
| 8 | `gripper.py`, `calibrate()` | Prints `张开(120mm)` | Cosmetic only; the computed values are correct once Step 2a is applied |

Item 3 is the one to be careful about: `home()` and `close()` do **not** go to the same
place, and `home()` is the outlier.
