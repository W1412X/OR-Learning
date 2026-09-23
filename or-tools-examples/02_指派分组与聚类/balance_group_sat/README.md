# balance_group_sat

用 CP-SAT 求解分组平衡问题：把 100 个物品分成 10 个等大小的小组，使各组取值之和尽量接近总平均值，并满足"同色至少 k 个"的颜色规则。

## 问题描述

有 100 个物品（每个有取值 `values[i]` 和颜色 `colors[i]`），要把它们分成 10 个组、每组恰好 10 个物品。要求：

1. 各组取值之和尽可能接近全体物品取值的平均值（`average_sum_per_group = sum(values) // num_groups`）；
2. 颜色规则：如果某种颜色出现在某组中，该组必须至少包含 `min_items_of_same_color_per_group = 4` 个该颜色的物品（不能只混进一两个"孤儿"色物品）。

"接近程度"用统一的偏差变量 epsilon 度量：所有组的和与平均值的偏差都不超过 epsilon，最小化 epsilon 即为最优分组。

## 建模思路

- **决策变量**：
  - `item_in_group[(i, g)]`（布尔）：物品 i 是否分到组 g；
  - `color_in_group[(c, g)]`（布尔）：颜色 c 是否出现在组 g 中；
  - `e`（整数变量，`new_int_var(0, 550, "epsilon")`）：允许的最大偏差。
- **约束**：
  - 组大小相同：每组 `sum(item_in_group[(i, g)]) == num_items_per_group`（= 100 // 10 = 10）；
  - 每物品恰属一组：`sum(item_in_group[(i, g)] for g) == 1`；
  - 组和贴近均值：每组 `sum(item_in_group[(i, g)] * values[i])` 落在 `[平均值 − e, 平均值 + e]`；
  - 蕴含关系：`add_implication(item_in_group[(i, g)], color_in_group[(colors[i], g)])`——物品在组中则其颜色"在"该组；
  - 颜色最少数量：`only_enforce_if(color_in_group[(c, g)])` 时，组 g 中颜色 c 的物品数 `>= min_items_of_same_color_per_group`；
  - 冗余约束（加速求解）：每组出现的颜色数 `<= max_color = num_items_per_group // min_items_of_same_color_per_group`。
- **目标函数**：`model.minimize(e)`，最小化全局偏差 epsilon。

## 运行方法

```bash
python3 balance_group_sat.py
```

本示例没有定义任何 absl flags：使用内置算例（100 物品 / 10 组 / 3 色）直接求解。求解器使用 16 个并行线程（`solver.parameters.num_workers = 16`）；`SolutionPrinter` 回调会打印搜索过程中的中间解；最优时打印 `Optimal epsilon: ...` 及求解统计信息。

## 关键实现说明

- `SolutionPrinter(cp_model.CpSolverSolutionCallback)`：解打印回调类；`on_solution_callback` 中用 `self.boolean_value(item_in_group[(item, g)])` 还原每组的物品列表并打印组和。
- 关键 API：
  - `cp_model.CpModel` / `new_bool_var` / `new_int_var`：创建模型与变量；
  - `add_implication`：布尔蕴含（物品在组 ⇒ 颜色在组）；
  - `only_enforce_if`：条件约束（仅当 `color_in_group[(c, g)]` 为真时才要求最少数量）；
  - `model.minimize(e)` / `cp_model.CpSolver` / `solver.solve(model, solution_printer)`：目标与求解；
  - `solver.parameters.num_workers`：并行搜索线程数。
- `# solver.parameters.log_search_progress = True` 为注释掉的调试开关，取消注释即可输出求解日志。
