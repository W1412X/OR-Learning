# flexible_job_shop_sat（柔性作业车间调度）

用 CP-SAT 求解柔性作业车间（flexible jobshop）调度问题，最小化所有作业的最大完工时间（makespan）。

## 问题描述

现实情景：车间生产排程。有 3 个作业（job 0~2），每个作业由 3 道工序（task）组成，同一作业内的工序必须按给定顺序依次完成；每道工序可以在 3 台机器（machine 0~2）中的任意一台加工，但在不同机器上的加工时长不同。一台机器同一时刻只能加工一道工序。

- 输入（硬编码在 `jobs` 中）：每个任务是若干备选方案的列表，每个方案为 `(加工时间, 机器编号)`，例如 `[(3, 0), (1, 1), (5, 2)]` 表示该工序可在机器 0 上花 3 个时间单位、或在机器 1 上花 1、或在机器 2 上花 5 完成；
- 要求：为每道工序选定一台机器和一个开始时间，使所有作业的完工时间（结束时间）的最大值——即 makespan——最小。

## 建模思路

- 决策变量：
  - 每道工序一个"主区间"：`start`（`new_int_var(0, horizon, ...)`）、`duration`（在所有备选方案加工时间的最小/最大值之间取值）、`end`，并用 `model.new_interval_var(start, duration, end, ...)` 组成区间；`starts[(job_id, task_id)]` 全局保存开始时间；
  - 每个备选方案（机器选择）：布尔变量 `l_presence = model.new_bool_var("presence...")`（存入 `presences[(job_id, task_id, alt_id)]`），以及一个可选区间 `l_interval = model.new_optional_interval_var(l_start, l_duration, l_end, l_presence, ...)`；按机器编号把可选区间收集到 `intervals_per_resources[machine_id]`；
  - `job_ends` 收集每个作业最后一道工序的结束时间；
  - `horizon` 为所有工序最大加工时间之和，作为时间上界。
- 约束条件：
  1. 工序先后（同一作业内）：`model.add(start >= previous_end)`——当前工序的开始时间不早于上一道工序的结束时间；
  2. 方案选择：`model.add_exactly_one(l_presences)`——每道工序恰好选中一个备选方案；选中时主变量与局部变量同步：`model.add(start == l_start).only_enforce_if(l_presence)`、`model.add(duration == l_duration).only_enforce_if(l_presence)`、`model.add(end == l_end).only_enforce_if(l_presence)`；
  3. 机器互斥：对每台机器 `model.add_no_overlap(intervals)`——同一机器上被选中的可选区间不能重叠（若某机器只有一个区间则无需约束）。
- 目标函数：`makespan = model.new_int_var(0, horizon, "makespan")`，用 `model.add_max_equality(makespan, job_ends)` 令其等于所有作业结束时间的最大值，再 `model.minimize(makespan)` 最小化。

## 运行方法

```bash
python3 flexible_job_shop_sat.py
```

本示例没有 absl flags。注意：该脚本末尾直接执行 `flexible_jobshop()`（不经过 `app.run`），因此也不解析任何命令行参数。

默认行为：
- 先打印 `Horizon = ...`（时间上界）；
- 每找到一个更优解，`SolutionPrinter` 回调打印一行 `Solution N, time = ... s, objective = ...`；
- 求解结束后，若状态为 OPTIMAL/FEASIBLE，打印 `Optimal objective value: ...` 以及每个作业每道工序的安排：`task_j_t starts at X (alt A, machine M, duration D)`；
- 最后打印 `solver.response_stats()` 统计信息。

## 关键实现说明

- 代码结构：
  - 类 `SolutionPrinter(cp_model.CpSolverSolutionCallback)`：求解过程中的解回调，每次发现新解时打印序号、墙钟时间与当前目标值；
  - 函数 `flexible_jobshop()`：数据定义、建模、求解、结果打印。
- 关键 API：
  - `model.new_interval_var(start, duration, end, name)`：构造工序的主区间；
  - `model.new_optional_interval_var(start, duration, end, presence, name)`：构造"可选"区间——当对应的 `presence` 布尔变量为假时该区间不生效，用于表达"只有选中该机器时才占用它"；
  - `model.add_exactly_one(literals)`：恰好选一个备选方案；
  - `model.add_no_overlap(intervals)`：机器资源互斥约束；
  - `model.add_max_equality(target, exprs)`：令 makespan 等于所有作业结束时间的最大值；
  - `constraint.only_enforce_if(literal)`：条件约束，仅在方案被选中时同步主/局部变量；
  - `solver.solve(model, solution_printer)`：求解并挂载解回调；
  - `solver.boolean_value(presences[...])`：读取每个方案的选中状态，用于还原"该工序用了哪台机器"；
  - `collections.defaultdict(list)`：按机器编号分组存放可选区间。
- 建模技巧：用"主区间 + 可选区间"的双层结构表达柔性（flexible）机器选择——主区间保证工序时间语义完整，可选区间按 presence 挂到具体机器上参与 NoOverlap。
