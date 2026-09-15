# 设计说明

`litegrip_urdf` 为何如此构建：几何参数的推导过程、使用方必须遵守的约定，
以及相对于原始 SolidWorks 导出文件的完整修订记录。

[English](design-notes.md) · **简体中文**

---

## 来源沿革

本 URDF 并非手写，而是源自一次 SolidWorks URDF Exporter 导出；原始导出中共存在三份
中间文件。厘清哪份文件派生自哪份很重要 —— 因为流传的所谓「原始值」来自这条链上
不同的阶段。

| 阶段 | 文件 | 状态 |
| --- | --- | --- |
| 1 | `夹爪urdf2.csv` | SolidWorks 的事实源。两个关节同名 `gripper_slide_joint` —— **重名，非法**。行程限位分别为 `0.067`（右）与 `-0.067`（左）。 |
| 2 | `夹爪urdf改前.urdf` | 关节名仍重名，限位 `0.067` / `-0.067`。**无法解析**：`joint 'gripper_slide_joint' is not unique`。 |
| 3 | `夹爪urdf2 (1).urdf` | 关节名已拆为 `_right` / `_left`。限位均写作 `0.043.5` —— 多了一个小数点的笔误。**无法解析**：`upper value (0.043.5) is not a valid float`。 |
| 4 | `litegrip_urdf`（本包） | 可正常解析，限位参数化为实测值 `0.042726`。 |

两处解析失败均已通过 `check_urdf` 实测确认。注意阶段 3 已经尝试修正行程限位 ——
但中间值 `0.043.5` 无法解析，因此两份中间文件都不能作为参照。
**本包沿用 SolidWorks 导出的 mesh 几何与惯性数值；除行程限位采用本机实测标定值外，其余几何与惯性数值未改。**

---

## 夹爪几何

### 坐标系

两指均沿 `base_link` 的 X 轴滑动，关节原点互为镜像：

| 关节 | 关节原点（`base_link` 系） | axis |
| --- | --- | --- |
| `gripper_slide_joint_right` | `(-0.067, 0.0010833, 0.034083)` | `+X` |
| `gripper_slide_joint_left` | `( 0.067, -0.0010833, 0.034083)` | `-X` |

### 行程限位的推导

SolidWorks 导出中右指标注 `Limit Upper = 0.067`。该值有误，会导致两指互穿。
正确的行程由手指 mesh 的包围盒推导得出。

从 `meshes/gripper_slider_link1.STL`（二进制 STL，遍历全部三角形顶点）实测：

```text
X 范围 = [-0.00095, +0.0235]
```

右指的关节原点位于 `x = -0.067`，故在关节值 `q` 处 mesh 占据：

```text
x_min(q) = -0.067 + q - 0.00095
x_max(q) = -0.067 + q + 0.0235      <- 右指内侧面
```

仅按 mesh 理论模型，两指内侧面在 `x = 0` 处贴合即完成闭合。解 `x_max(q) = 0`：

```text
q = 0.067 - 0.0235 = 0.0435
```

这得到 mesh 理论行程 `0.0435` m。随后对本机实物单独测量得到：总机械行程
`85.452 mm`、单指行程 `0.042726 m`、闭合间隙 `1.508 mm`、张开开口
`86.960 mm`。因此 xacro 限位采用实测值 `0.042726` m，并需要通过 RViz/Gazebo
重新验证 mesh 与 TF。`calibrate_guided` 已完成 3 次数据采集：闭合角度
`0.041380–0.041400 rad`、张开角度均为 `-1.272790 rad`、角度行程
`1.314170–1.314190 rad`、`rad_to_mm` 为 `65.0226–65.0236 mm/rad`。
张开端复测 5 次得到机械行程 `85.43–85.47 mm`，均值为 `85.452 mm`；对应
`rad_to_mm` 为 `65.0053–65.0372 mm/rad`，最终标定值采用 `65.0229 mm/rad`。

**若将 `upper` 保留为 `0.067`，两指将重叠 0.0235 m，完全互穿。**
请勿改回该值。

### 行程两端的实测行为

以下将 URDF 模型端点与本机卡尺实测值对照；更新后的限位仍需在运行时复核：

| 指令 | 手指原点 | 内侧面 | 开口 |
| --- | --- | --- | --- |
| `[0.0, 0.0]` | `x = ∓0.067` | 理论 `x = ∓0.0435` | 实测 **86.960 mm** |
| `[0.042726, 0.042726]` | 实测闭合位置 | 实测闭合位置 | 实测间隙 **1.508 mm** |

`q = 0` 时的手指原点可用于检查模型。由于实测闭合间隙并非理想 mesh 接触值，
更新后的 `0.042726` 限位仍需运行时做 mesh/TF 验证，暂不能直接称为几何验证完成。

位置指令的卡尺读数已记录：`0 mm` 为 `0.12、0.04、0.16、0.06、0.12 mm`；
`20 mm` 为 `20.40、20.04、20.08、19.98、18.80 mm`；`40 mm` 为
`40.02、40.20、40.22、39.86、39.90 mm`；`60 mm` 为
`60.22、59.86、60.02、60.06、59.98 mm`；`80 mm` 为
`80.06、80.10、79.88、80.02、79.96 mm`；`85.452 mm` 为
`85.24、85.52、85.60、85.40、85.80 mm`。其中 `20 mm` 位置的 `18.80 mm`
为明显离群读数；按原始读数计算的最大绝对误差为 `1.20 mm`，因此位置绝对误差
尚未完成最终验收，需复测该点。50 次循环（`2 mm ↔ 83 mm`）已完成：第 1 次到
第 50 次闭合端开口漂移 `+0.01 mm`、张开端开口漂移 `+0.02 mm`，闭合角度和
张开角度漂移均为 `+0.000009 rad`；该项重复性定量数据已完成。

---

## 关节符号约定

**这是本模型最常见的集成错误来源。**

两个关节的 axis 方向相反（`+X` 与 `-X`）。由于 `JointGroupPositionController` 会把每个值
沿各自关节的 axis 施加到对应关节上，**两个元素必须同号**才能使两指对称运动：

| 指令 | 结果 |
| --- | --- |
| `[0.0, 0.0]` | 完全张开 |
| `[0.042726, 0.042726]` | 实测闭合标定位置 |
| `[0.02, -0.02]` | ❌ 两指同向运动 —— 不是抓取 |

axis 相反是 CAD 模型本身的属性，并非此处引入的缺陷：SolidWorks CSV 中一指标注
`Joint Axis X = 1`、另一指标注 `-1`。又因为两关节均为 `lower = 0`、`upper = 0.042726`，
「一正一负」的对称直觉不仅错误，还会使其中一个关节越界。

---

## 为何存在 `base_footprint`

SolidWorks 导出将 `base_link` 声明为根节点，而 `base_link` 是带惯性的。
KDL —— 以及依赖它的 MoveIt 和大多数 TF 使用方 —— **不支持带惯性的 root link**：
它会给出 `root link has an inertia` 告警，并静默丢弃该惯性。

解决办法是引入一个无质量、无惯性的 `base_footprint` link，与 `base_link` 位姿重合，
以 fixed 关节相连。这样 TF 树就具有合法树根，而 `base_link` 的惯性作为非根节点得以保留。

由此带来两个后果：

1. **将夹爪安装到机械臂时，请以 `base_footprint` 为附着基准**，而非 `base_link`。
2. **不要再额外发布二者之间的静态变换。** 原始 ROS 1 的 `gazebo.launch` 发布了一个
   `tf_footprint_base` 节点，参数为 `0 0 0 0 0 0 base_link base_footprint` —— 注意
   `tf2` 的 `static_transform_publisher` 参数顺序是 `frame_id child_frame_id`，
   因此该行实际是声明 `base_link` 为 `base_footprint` 的**父节点**。而 URDF 中已定义
   `base_footprint` 为根、`base_link` 为其子节点，再发布一次会让同一对 frame 在 TF
   树中出现两个父节点。该节点已被移除。

RViz 配置使用的固定坐标系即为 `base_footprint`。

---

## 相对于 SolidWorks 导出的修订记录

以下全部为修复。**未改动任何几何或惯性数值。**

| # | 修订内容 | 原因 |
| --- | --- | --- |
| 1 | `<limit upper="0.043.5">` → 参数化实测值 `0.042726` | `0.043.5` 不是合法浮点数，原文件完全无法解析 |
| 2 | 关节 `gripper_slide_joint` → `gripper_slide_joint_right` / `_left` | 两关节同名，非法 |
| 3 | 左指 `upper` 由 `-0.067` → 实测值 `0.042726` | `lower = 0` 时 upper 为负值，区间非法 |
| 4 | 新增无惯性根节点 `base_footprint` | 消除 KDL `root link has an inertia` 告警，见上文 |
| 5 | 补全空的材质名称（原为 `name=""`） | 空名非法；现为 `litegrip_base` 与 `litegrip_finger` |
| 6 | 补充 `<dynamics damping friction>` | 原导出未定义；抑制仿真振荡所必需 |
| 7 | 补充 `<ros2_control>` 块 | 任何 ros2_control 集成的前提 |
| 8 | 包名 `夹爪urdf2` → `litegrip_urdf` | ROS 2 要求包名为小写字母/数字/下划线 |
| 9 | 修正 `config/joint_names_*.yaml` | 原文件含空串占位与重复项：`['', 'gripper_slide_joint', 'gripper_slide_joint', ]` |
| 10 | 移除多余的 `base_link → base_footprint` 静态变换 | 方向写反，且会与 URDF 的根节点定义冲突，见上文 |
| 11 | 补全 `package.xml` 依赖声明 | 原导出缺 `gazebo_ros`、`tf`、`rostopic`、`joint_state_publisher` |

第 1–3 项均已通过尝试解析对应源文件加以确认，见[来源沿革](#来源沿革)。

---

## 质量属性

原样沿用 SolidWorks 导出结果。总质量 **0.5772 kg**。

| Link | 质量 | ixx | iyy | izz |
| --- | --- | --- | --- | --- |
| `base_link` | 0.506299 kg | 1.40520e-04 | 3.08493e-04 | 3.45331e-04 |
| `gripper_slider_link1` | 0.0354537 kg | 1.73251e-05 | 1.26496e-05 | 6.96030e-06 |
| `gripper_slider_link2` | 0.0354537 kg | 1.73251e-05 | 1.26496e-05 | 6.96030e-06 |

两指互为镜像：惯性张量的 `ixx`、`iyy`、`izz` 相同，惯性积在 `ixz`、`iyz` 上符号相反，
符合预期。

完整张量（含质心位置与惯性积）见
[`urdf/litegrip_urdf.urdf.xacro`](../urdf/litegrip_urdf.urdf.xacro)。

---

## 设计决策

### 为何选用 `JointGroupPositionController` 而非 `GripperActionController`

夹爪天然适合 Action 接口 —— 调用方真正想要的操作是「闭合直到堵转」。
障碍在于 `GripperActionController` 只接受**单个**关节。要用它驱动两指，就需要为第二指
配置 `<mimic>` 关节，而 **`<mimic>` 在 ros2_control 中不会自动生效** ——
它取决于硬件接口或仿真器的支持，并非每个厂商插件都提供。

`JointGroupPositionController` 接受关节数组，不依赖 mimic 支持，因此在 mock、Gazebo
与真机上行为一致。代价是调用方需要通过话题发送 `Float64MultiArray`，而非调用 Action。
若你需要 Action 接口且硬件支持 `<mimic>`，该替换是受支持的做法。

### 为何碰撞几何复用视觉 STL

原导出的 `<collision>` 与 `<visual>` 指向同一批 mesh。仅 3 个 link 时开销可接受，
且能保证碰撞边界与渲染几何完全一致。`base_link.STL` 约 925 KB，
若本模型被集成到对性能敏感的场景（大量夹爪，或高频碰撞检测），请将
`<collision>` 替换为简化几何体。

### 本包有意不包含的内容

未做 mesh 简化、未加碰撞余量、未设置 `<safety_controller>` 限位、未定义 transmission。
SolidWorks 导出中均无这些内容，凭空填入数值会让本包显得比实际更完善。
`effort` 与 `velocity` 限位是导出默认值，在 xacro 与 README 中均已标注为未标定。