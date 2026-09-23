# jobshop_ft06_sat（标准 ft06 作业车间调度）

用 CP-SAT 求解经典的 ft06 作业车间调度问题，最小化总完工时间（makespan）。

## 问题描述

作业车间调度（Job Shop Scheduling）是一类标准的调度问题：需要在一组机器上对一系列任务（task）进行排序。每个作业（job）在每台机器上各有一个任务，任务的执行顺序与加工时长均由具体任务决定。同一台机器同一时刻只能加工一个任务，而同一作业内的工序必须按既定顺序依次完成。

本示例使用经典的 ft06 算例：6 个作业（`jobs_count`）、6 台机器（`machines_count`），每个作业包含 6 道工序。数据写死在代码中：

- `durations[i][j]`：作业 i 的第 j 道工序的加工时长；
- `machines[i][j]`：作业 i 的第 j 道工序所用的机器编号。

- 输入：上述两个 6x6 矩阵。
- 要求：确定每台机器上各任务的加工顺序与开始时间，使所有作业的最大完工时间（makespan，即每个作业最后一道工序结束时间的最大值）最小。

## 建模思路

- 决策变量：
  - 对每个作业 i、每道工序 j 创建整数变量 `start_{i}_{j}`（开始时间）与 `end_{i}_{j}`（结束时间），取值范围 `[0, horizon]`；`horizon` 动态计算为所有工序时长之和（最保守的时间上界）。
  - 用区间变量 `interval_{i}_{j}`（`new_interval_var`）把开始时间、固定时长 `durations[i][j]` 与结束时间绑定在一起。
  - `task_type` 命名元组把三者组织存放在 `all_tasks[(i, j)]` 中。
- 约束条件：
  - 机器互斥（析取约束）：对每台机器收集其上所有任务的区间，调用 `model.add_no_overlap(machines_jobs)`，保证同一机器上的任务两两不重叠。
  - 作业内先后顺序：`all_tasks[(i, j + 1)].start >= all_tasks[(i, j)].end`，即作业 i 的第 j+1 道工序必须等第 j 道工序结束才能开始。
- 目标函数：`obj_var = model.new_int_var(0, horizon, "makespan")`，用 `model.add_max_equality` 令其等于所有作业最后一道工序结束时间的最大值，再 `model.minimize(obj_var)` 最小化 makespan。

## 运行方法

```bash
python3 jobshop_ft06_sat.py
```

本示例没有定义任何 absl flags，也没有使用 `absl.app`。默认行为是：脚本被导入/执行时直接调用 `jobshop_ft06()` 求解标准 ft06 问题。求解器参数在代码中设置 `solver.parameters.log_search_progress = True`，因此运行时会打印 CP-SAT 的搜索进度日志；求解完成后，若在终端环境则打印 `Optimal makespan: ...`（最优 makespan 值），若在 IPython/Jupyter 环境（`visualization.RunFromIPython()` 为真）则调用 `visualization.DisplayJobshop` 以甘特图形式展示调度方案。

## 关键实现说明

- 代码结构：
  - `jobshop_ft06()`：核心函数，完成数据读取、建模、求解与结果输出。
  - `task_type = collections.namedtuple("task_type", "start end interval")`：命名元组，组织每个任务的变量。
  - 模块末尾直接调用 `jobshop_ft06()`（脚本无 main 函数）。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：创建 CP-SAT 模型与求解器，`solver.solve(model)` 执行求解，`solver.objective_value` 读取最优目标值。
  - `model.new_int_var(lb, ub, name)`：创建开始/结束时间变量。
  - `model.new_interval_var(start, duration, end, name)`：创建区间变量（start + duration == end）。
  - `model.add_no_overlap(intervals)`：机器容量约束，同机器任务互斥。
  - `model.add(...)`：作业内工序的先后顺序约束。
  - `model.add_max_equality(target, exprs)` / `model.minimize(target)`：定义并最小化 makespan。
  - `solver.parameters.log_search_progress`：开启搜索日志。
  - `ortools.sat.colab.visualization`：`RunFromIPython()` 判断运行环境；`DisplayJobshop(starts, durations, machines, "FT06")` 在 notebook 中绘制调度甘特图。
