# jobshop_with_maintenance_sat（带机器维护的作业车间调度）

用 CP-SAT 求解带机器维护时段的小型作业车间调度问题，最小化总完工时间（makespan）。

## 问题描述

作业车间调度（Job Shop Scheduling）问题：有若干作业，每个作业由一组按固定顺序执行的任务组成，每个任务在一台指定机器上加工；同一机器同一时刻只能加工一个任务。

本示例在标准作业车间的基础上增加了现实工厂中常见的"计划性维护"约束：机器 0 在时间区间 {4, 5, 6, 7} 不可用（例如周末停机检修），该时段内不能安排任何加工任务。

代码内置的数据（`jobs_data`）为 3 个作业、3 台机器（编号 0、1、2）：

- Job0：(0, 3), (1, 2), (2, 2)——三道工序，依次在机器 0/1/2 上加工，时长分别为 3/2/2；
- Job1：(0, 2), (2, 1), (1, 4)——三道工序，机器 0/2/1，时长 2/1/4；
- Job2：(1, 4), (2, 3)——两道工序，机器 1/2，时长 4/3。

- 输入：作业的（机器编号, 加工时长）序列列表，以及机器 0 的维护时段。
- 要求：确定每个任务的开始时间，使所有作业的最大完工时间（makespan）最小。

## 建模思路

- 决策变量：
  - 对每个作业 `job_id` 的每道工序 `task_id` 创建整数变量 `start`（开始时间）与 `end`（结束时间），取值范围 `[0, horizon]`（`horizon` 动态取所有任务时长之和）；区间变量 `interval` 由 `new_interval_var` 绑定三者。所有变量存放在 `all_tasks[(job_id, task_id)]` 中。
  - 维护时段建模为一个普通区间变量：`model.new_interval_var(4, 4, 8, "weekend_0")`——从时刻 4 开始、时长 4、在时刻 8 结束，被追加进机器 0 的区间列表。
- 约束条件：
  - 机器互斥（析取约束）：对每台机器，把其上所有任务区间（机器 0 还包括维护区间）收集到 `machine_to_intervals`，调用 `model.add_no_overlap(...)`。由于维护区间也参与 `add_no_overlap`，任何任务都不能与维护时段重叠。
  - 作业内先后顺序：`all_tasks[job_id, task_id + 1].start >= all_tasks[job_id, task_id].end`，即同一作业的下一道工序必须等上一道工序结束。
- 目标函数：`obj_var = model.new_int_var(0, horizon, "makespan")`，用 `model.add_max_equality` 令其等于每个作业最后一道工序结束时间的最大值，再 `model.minimize(obj_var)` 最小化 makespan。

## 运行方法

```bash
python3 jobshop_with_maintenance_sat.py
```

本示例没有定义任何 absl flags，默认行为是：求解内置的带维护作业车间算例。求解时传入 `SolutionPrinter` 回调，每找到一个（更优的）中间解就打印一行 `Solution N, time = ... s, objective = ...`；求得最优解后打印 `Optimal Schedule Length: ...`、每台机器上各任务的排程表（按开始时间排序、列对齐），以及 `solver.response_stats()` 统计信息。若命令行传入多余参数会抛出 `app.UsageError`。

## 关键实现说明

- 代码结构：
  - `SolutionPrinter(cp_model.CpSolverSolutionCallback)`：自定义求解回调类，在 `on_solution_callback` 中打印每次发现中间解时的序号、耗时与目标值。
  - `jobshop_with_maintenance()`：核心函数，完成建模、求解与结果输出；用 `task_type` 命名元组保存任务变量，用 `assigned_task_type` 命名元组保存解中的任务分配（start/job/index/duration），最后按机器分组输出对齐的排程表。
  - `main(argv)`：检查命令行参数个数后调用求解函数。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：创建模型与求解器；`solver.solve(model, solution_printer)` 求解并注册回调。
  - `cp_model.CpSolverSolutionCallback`：中间解回调基类，可用 `self.wall_time`、`self.objective_value` 读取当前耗时与目标值。
  - `model.new_int_var(lb, ub, name)` / `model.new_interval_var(start, duration, end, name)`：创建时间变量与区间变量。
  - `model.new_interval_var(4, 4, 8, "weekend_0")`：用固定数值直接创建维护区间，参与 `add_no_overlap` 实现机器不可用时段。
  - `model.add_no_overlap(intervals)`：机器容量约束（任务之间以及任务与维护时段互不重叠）。
  - `model.add_max_equality(target, exprs)` / `model.minimize(target)`：定义并最小化 makespan。
  - `solver.value(var)` / `solver.objective_value` / `solver.response_stats()`：读取解与统计信息。
