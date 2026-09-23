# gate_scheduling_sat（闸门调度问题）

两台并行机器加工一组任务（每个任务有时长与宽度），任意时刻活动任务的宽度之和不得超过最大宽度，最小化所有任务的最大完工时间（makespan）。

## 问题描述

现实情景：闸门/装卸口调度。有 15 个任务（`jobs` 中每项为 `[时长, 宽度]`，如 `[3, 3]` 表示时长 3、宽度 3），两台并行机器（machine 0、machine 1）都可以执行这些任务：

- 一台机器同一时刻只能执行一个任务；
- 任意时刻，两台机器上正在执行的任务的宽度总和不得超过 `max_width = 10`。

要求：为每个任务选择执行机器与开始时间，使所有任务结束时间的最大值（makespan）最小。

- 输入：硬编码的 `jobs` 列表（15 个任务的时长与宽度）与 `max_width = 10`；
- 要求：输出 makespan 及每个任务的开始时间与所在机器。

## 建模思路

- 决策变量：
  - 每个任务一个主区间：`start = model.new_int_var(0, horizon, f"start_{i}")`、`end`（时长 `duration = jobs[i][0]` 为常量），`model.new_interval_var(start, duration, end, ...)`；`demands` 收集各任务的宽度；
  - 机器选择：布尔变量 `performed_on_m0 = model.new_bool_var(f"perform_{i}_on_m0")`（存入 `performed`），表示任务 i 是否在机器 0 上执行；
  - 为每个任务创建两个可选区间副本：机器 0 上的 `interval0 = model.new_optional_interval_var(start0, duration, end0, performed_on_m0, ...)`，机器 1 上的 `interval1 = model.new_optional_interval_var(start1, duration, end1, ~performed_on_m0, ...)`（presence 取反）；
  - `horizon = sum(t[0] for t in jobs)` 作为时间上界。
- 约束条件：
  1. 宽度约束（用累积约束建模）：`model.add_cumulative(intervals, demands, max_width)`——任意时刻正在执行的任务宽度总和 ≤ 10；
  2. 机器选择与互斥：`model.add_no_overlap(intervals0)` 与 `model.add_no_overlap(intervals1)`——每台机器上的任务不能重叠；任务在两台机器间二选一由两个可选区间的 presence（互补）保证；
  3. 同步约束：`model.add(start0 == start).only_enforce_if(performed_on_m0)`、`model.add(start1 == start).only_enforce_if(~performed_on_m0)`——只在任务被安排到该机器时，才把局部开始时间与主开始时间绑定；
  4. 对称性破除：`model.add(performed[0] == 0)`——强制任务 0 在机器 1 上执行，消除两台机器互换产生的对称解。
- 目标函数：`makespan = model.new_int_var(0, horizon, "makespan")`，`model.add_max_equality(makespan, ends)` 令其为所有任务结束时间的最大值，`model.minimize(makespan)` 最小化。

## 运行方法

```bash
python3 gate_scheduling_sat.py
```

本示例没有自定义 absl flags。默认行为：直接求解一次，然后根据运行环境输出：

- 在 IPython/Jupyter 环境中（`visualization.RunFromIPython()` 为真）：用 `ortools.sat.colab.visualization` 的 `SvgWrapper` 生成 SVG 甘特图——每个任务一个矩形（长度为时长、高度为宽度），两台机器上下排布（机器按 `1 - performed[i]` 换算），附标题 `Makespan = ...` 与坐标轴；
- 在普通终端：文本打印 `Solution`、`makespan = ...`、每个任务的 `Job i starts at T on machine M`，最后打印 `solver.response_stats()`。

## 关键实现说明

- 代码结构：单个函数 `main(_)`，按"数据 → 建模 → 求解 → 输出"组织（经 `app.run(main)` 启动）。
- 关键 API：
  - `model.new_interval_var(start, duration, end, name)`：主区间，参与累积宽度约束；
  - `model.new_optional_interval_var(start, duration, end, presence, name)`：可选区间，presence 为假时区间不生效，用于把任务"挂"到具体机器上；
  - `model.add_cumulative(intervals, demands, capacity)`：资源容量约束，此处表达"宽度总和不超过 max_width"；
  - `model.add_no_overlap(intervals)`：单机互斥约束（两台机器各一条）；
  - `model.add_max_equality(makespan, ends)` + `model.minimize(makespan)`：目标定义与最小化；
  - `constraint.only_enforce_if(literal)` 与取反运算符 `~performed_on_m0`：条件约束与互补的机器选择；
  - `ortools.sat.colab.visualization`（`SvgWrapper`、`ColorManager`、`RunFromIPython`）：notebook 环境下的可视化。
- 建模技巧：本例同时使用**累积约束**（全局宽度共享上限）与**两台机器的 NoOverlap**（单机互斥）的组合来刻画"两台机器共享总宽度"的闸门约束；机器选择的互补 presence（`performed_on_m0` 与 `~performed_on_m0`）保证每个任务恰好分配到一台机器。
