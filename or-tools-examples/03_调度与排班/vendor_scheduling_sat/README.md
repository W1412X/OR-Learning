# vendor_scheduling_sat（商贩排班问题）

用 CP-SAT 求解一个简单的商贩（小贩/临时摊位工作人员）排班问题：从有限种候选班次中为每个商贩选择一个班次，使每个时段的在岗服务能力覆盖客流量，并枚举所有可行排班方案。

## 问题描述

某市场需要为 9 名商贩（vendors）安排 10 个时段（hours）的工作。每个时段有不同的客流量 `traffic = [100, 500, 100, 200, 320, 300, 200, 220, 300, 120]`，一名商贩在一个时段最多能服务 100 名顾客（`max_traffic_per_vendor = 100`）。

人力部门预先设计了 6 种候选班次（`possible_schedules`），每行描述一种班次：

- 前 10 列：该班次在各时段是否在岗（1 = 工作，0 = 休息）；
- 倒数第 2 列：班次索引（便于分支搜索）；
- 最后 1 列：该班次的总工作小时数。

要求：为每名商贩指定一种候选班次，使得每个时段"在岗人数 x 100 >= 该时段客流量"。问题没有优化目标，任务是**找出所有**满足约束的排班方案。

## 建模思路

- **决策变量**：
  - `x[v, h]`：整数变量，取值 0 ~ `num_work_types`（=1），表示商贩 v 在时段 h 的工作类型（0 表示不在岗）；
  - `selected_schedules[v]`：整数变量 `s[v]`，取值 0 ~ 5，表示商贩 v 被选中的候选班次索引；
  - `vendors_stat[v]`：整数变量 `h[v]`，取值 0 ~ 10，表示商贩 v 的总工作小时数；
  - `workers[h]`：整数变量（0 ~ 1000），表示时段 h 的在岗人数（统计变量）。
- **约束条件**：
  - 表约束 `model.add_allowed_assignments(tmp, possible_schedules)`：把 `(x[v,0..9], s[v], h[v])` 这 12 个变量限定为 `possible_schedules` 中的某一行，从而每小时是否在岗、所选班次索引、总工时三者天然一致；
  - 覆盖约束：`model.add(workers == sum(x[v, h] for v in all_vendors))` 统计在岗人数，且 `model.add(workers * max_traffic_per_vendor >= traffic[h])` 保证服务能力覆盖客流量；
  - 冗余的对称性破除约束：`model.add(selected_schedules[v] <= selected_schedules[v + 1])`，强制所选班次索引按商贩编号不降序排列，消除排列对称解、加速搜索。
- **目标函数**：无。模型为纯可行性问题，通过 `solver.parameters.enumerate_all_solutions = True` 枚举全部可行解。

辅助数据 `min_vendors = [t // max_traffic_per_vendor for t in traffic]` 计算各时段最少所需人数，仅用于在回调中打印。

## 运行方法

```bash
python3 vendor_scheduling_sat.py
```

本示例没有定义任何 absl flags，直接运行即可。默认行为：构建 9 商贩 x 10 时段的排班模型并求解，枚举并打印**所有**可行排班方案（每个解打印各商贩选中的班次、每时段在岗人数，以及辅助数据 `min_vendors`），最后输出求解状态（Status）与统计信息（conflicts、branches、wall time、找到的解数量）。

若传入多余的位置参数（如 `python3 vendor_scheduling_sat.py foo`），会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

- 类 `SolutionPrinter(cp_model.CpSolverSolutionCallback)`：求解回调，每找到一个解就调用 `on_solution_callback()`，打印解编号、各商贩选中的班次（通过 `self.value(selected_schedules[i])` 查询解值并索引 `possible_schedules`）、各时段在岗人数；`solution_count()` 返回已找到的解数量。
- 函数 `vendor_scheduling_sat()`：主流程——
  - 数据定义：`num_vendors=9`、`num_hours=10`、`num_work_types=1`、`traffic`、`max_traffic_per_vendor=100`、`possible_schedules`（6 种班次）；
  - 变量声明：`model.new_int_var` 创建 `x[v,h]`、`s[v]`、`h[v]`；
  - 约束：`add_allowed_assignments` 表约束、每时段人数统计与覆盖约束、班次索引排序的冗余约束；
  - 求解：`cp_model.CpSolver()` + `enumerate_all_solutions=True`，`solver.solve(model, solution_printer)` 边求解边打印；
  - 统计输出：`solver.status_name(status)`、`solver.num_conflicts`、`solver.num_branches`、`solver.wall_time`。
- 关键 API：`CpModel.new_int_var`、`CpModel.add_allowed_assignments`、`CpModel.add`、`CpSolverSolutionCallback`、`CpSolver.solve`、`CpSolver.status_name`。

依赖：`absl.app`、`ortools.sat.python.cp_model`。
