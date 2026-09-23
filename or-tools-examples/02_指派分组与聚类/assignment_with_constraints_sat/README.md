# assignment_with_constraints_sat

用 CP-SAT 求解带有"工人组合"约束的指派问题：把任务分给工人，除常规成本最小化外，还要求每 4 名一组的工人中"谁参与工作"的组合必须取自允许列表。

## 问题描述

一支 12 人的队伍（`cost` 为 12×6 的成本矩阵，`cost[i][j]` 是工人 i 承担任务 j 的成本）要完成 6 个任务。除指派关系外还有两类业务规则：

- 每名工人有总工作量上限：`sizes` 给出各任务的工作量，每人承担任务的工作量之和不超过 `total_size_max = 15`；
- 组合约束：12 名工人按编号分成 3 组（0~3、4~7、8~11），每组 4 人中"谁参与工作"不能任意组合，只能取 `group1`/`group2`/`group3` 中列出的允许模式（每种模式都恰好选中该组的 2 名工人，例如 `group1` 的 `[0, 0, 1, 1]` 表示只有工人 2、3 参与）。

要求：每个任务至少由一名工人承担，总成本最小。

## 建模思路

- **决策变量**：
  - `selected[i][j]`（`new_bool_var`）：工人 i 是否承担任务 j；
  - `works[i]`（`new_bool_var`）：工人 i 是否参与工作。
- **约束**：
  - 变量关联：`model.add_max_equality(works[i], selected[i])`，即 `works[i] == max(selected[i])`——承担任一任务则该工人"参与工作"；
  - 任务覆盖：每个任务 `sum(selected[i][j]) >= 1`（至少一名工人承担）；
  - 工作量上限：每名工人 `sum(sizes[j] * selected[i][j]) <= total_size_max`；
  - 组合约束：`model.add_allowed_assignments([works[0..3]], group1)`（对 group2、group3 同理）——4 个布尔变量的取值元组必须落在允许列表中。
- **目标函数**：`model.minimize(sum(selected[i][j] * cost[i][j]))`，最小化总成本。

## 运行方法

```bash
python3 assignment_with_constraints_sat.py
```

本示例没有定义任何 absl flags：直接使用代码内置的算例数据求解，并打印最优总成本与"工人 → 任务"的指派明细，最后输出求解器统计信息（`response_stats()`）。

## 关键实现说明

- `solve_assignment()`：唯一的求解函数，包含数据定义、建模、求解与打印。
- 关键 API：
  - `cp_model.CpModel` / `new_bool_var`：创建模型与布尔决策变量；
  - `add_max_equality`：用"取最大"等式把 `works[i]` 与该工人的所有 `selected[i][j]` 关联（任一为真则为真）；
  - `add_allowed_assignments`：约束一组变量的取值元组必须属于给定列表（本例实现"工人组合"业务规则的关键 API）；
  - `model.minimize` / `cp_model.CpSolver` / `solver.solve(model)`：目标函数与求解；
  - `solver.boolean_value(...)`：读取布尔变量取值并打印指派结果。
- 若无解，代码只打印 `solver.response_stats()` 的统计信息。
