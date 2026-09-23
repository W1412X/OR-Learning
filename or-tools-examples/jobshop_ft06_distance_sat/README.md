# jobshop_ft06_distance_sat（带机器间隔的 ft06 作业车间调度）

用 CP-SAT 求解 ft06 作业车间调度问题的变体：同一机器上相邻任务之间必须保持最小时间间隔。

## 问题描述

作业车间调度（Job Shop Scheduling）是一类经典的调度问题：有若干个作业（job），每个作业由一组按固定顺序执行的任务（task）组成，每个任务在一台指定的机器上加工。不同作业的任务可能争用同一台机器，因此每台机器同一时刻只能加工一个任务，任务的执行顺序与加工时长均由任务决定。

本示例使用经典的 ft06 算例：6 个作业（`jobs_count`）、6 台机器（`machines_count`），每个作业按顺序经过 6 道工序；`durations[i][j]` 给出作业 i 的第 j 道工序的加工时长，`machines[i][j]` 给出该工序所用的机器编号。

本变体在标准作业车间的基础上额外引入"最小间隔距离"：在同一台机器上，若任务 x 排在任务 y 之前，则 y 的开始时间必须不早于 x 的结束时间加上 `distance_between_jobs(x, y) = abs(x - y)` 的间隔。

- 输入：作业的工序时长矩阵 `durations` 与机器分配矩阵 `machines`（写死在代码中），以及机器上任务间的最小间隔函数。
- 要求：给出所有任务在机器上的排产顺序与开始时间，使整个工程的总完工时间（makespan，即所有作业完成时间的最大值）最小。

## 建模思路

- 决策变量：
  - 对每个作业 i、每道工序 j 创建 `start_{i}_{j}`（开始时间）、`end_{i}_{j}`（结束时间），均为 `[0, horizon]` 内的整数变量（`horizon = 150` 静态设定，大于所有时长之和的保守上界）；并用 `new_interval_var` 关联成区间变量 `interval_{i}_{j}`（长度 = `durations[i][j]`）。
  - 每台机器上为任务对的先后关系创建布尔"弧"变量（如 `"{j2} follows {j1}"`、`"{j1} is first job"`、`"{j1} is last job"`），构成机器上任务排序的有向哈密顿回路。
- 约束条件：
  - 机器互斥：对每台机器，收集在其上加工的所有区间并调用 `model.add_no_overlap(job_intervals)`，保证同一机器上的任务不重叠。
  - 机器排序与最小间隔：对每台机器，用 `model.add_circuit(arcs)` 要求所有任务节点构成一条经过全部节点的回路（即给出机器上任务的一个全序）。当弧 `lit`（j2 紧跟 j1）为真时，通过条件约束 `model.add(job_starts[j2] >= job_ends[j1] + min_distance).only_enforce_if(lit)` 强制后继任务开始时间与前驱结束时间之间至少间隔 `min_distance = abs(j1 - j2)`。
  - 作业内部先后顺序：`all_tasks[(i, j + 1)].start >= all_tasks[(i, j)].end`，即作业 i 的第 j+1 道工序必须等第 j 道工序结束。
- 目标函数：`obj_var = model.new_int_var(0, horizon, "makespan")`，通过 `model.add_max_equality(obj_var, [...])` 令其等于所有作业最后一道工序结束时间的最大值，并 `model.minimize(obj_var)` 最小化总完工时间。

## 运行方法

```bash
python3 jobshop_ft06_distance_sat.py
```

本示例没有定义任何 absl flags，也没有使用 `absl.app`。默认行为是：脚本被导入/执行时直接调用 `jobshop_ft06_distance()` 求解 ft06 带间隔变体，找到并打印最优 makespan（`Optimal makespan: ...`），随后打印求解统计 `solver.response_stats()`。

## 关键实现说明

- 代码结构：
  - `distance_between_jobs(x, y)`：返回作业 x 与作业 y 的任务之间的最小间隔（本例为 `abs(x - y)`）。
  - `jobshop_ft06_distance()`：核心函数，读取数据、建模、求解并输出结果。
  - `task_type = collections.namedtuple("task_type", "start end interval")`：命名元组，把同一任务的开始/结束/区间变量组织在一起，存放在字典 `all_tasks[(i, j)]` 中。
  - 模块末尾直接调用 `jobshop_ft06_distance()`（脚本无 main 函数）。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：创建 CP-SAT 模型与求解器，`solver.solve(model)` 求解。
  - `model.new_int_var(lb, ub, name)`：创建开始/结束时间整数变量。
  - `model.new_interval_var(start, duration, end, name)`：创建区间变量（start + duration == end）。
  - `model.add_no_overlap(intervals)`：机器容量约束（同机器任务互斥不重叠）。
  - `model.new_bool_var(name)` + `model.add_circuit(arcs)`：用回路约束（circuit）为每台机器构造任务全序，弧 `(0, j+1, lit)` 与 `(j+1, 0, lit)` 表示首/尾任务，弧 `(j1+1, j2+1, lit)` 表示 j2 紧随 j1。
  - `model.add(...).only_enforce_if(lit)`：条件（reified）约束，仅在对应弧变量为真时生效，用于把排序关系与最小间隔绑在一起。
  - `model.add_max_equality(target, exprs)` / `model.minimize(target)`：定义并最小化 makespan。
  - `solver.objective_value`：读取最优目标值。
