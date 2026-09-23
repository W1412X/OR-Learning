# wedding_optimal_chart_sat（婚礼最优座位安排）

用 CP-SAT 求解婚礼宾客的座位安排问题：把 17 位宾客分配到若干张桌子上，在满足桌容量和"至少认识一位同桌邻居"的前提下，最大化所有同桌宾客之间关系强度的总和。

## 问题描述

源自 Meghan L. Bellows 和 J. D. Luc Peterson 的论文《Finding an optimal seating chart for a wedding》：婚礼筹备中最令人头疼的任务之一就是安排宾客座位。宾客回执已收、宴会厅已订、菜单已选，但座位表仍是最大的难题。本文给出该问题的数学模型，求解后即可得到宾客在各桌的最优安排。

本示例的数据（`build_data()`）：

- 5 张桌子（`num_tables = 5`），每桌容量 4 人（`table_capacity = 4`）；
- 17 位宾客，名字在 `names` 中标注所属阵营（B = 新娘方，G = 新郎方）；
- 认识关系矩阵 `connections`（17x17 对称矩阵）：`connections[g1][g2]` 表示两位宾客的关系强弱，0 表示互不相识，1/10/50 表示相识且关系越来越亲密；
- `min_known_neighbors = 1`：要求每位宾客至少与 1 位认识的人同桌。

代码中另有一组被注释掉的更简单参数（2 桌、每桌 10 人），也来自上述论文。

目标：找出使"所有同桌宾客对的关系强度之和"最大的座位安排。

## 建模思路

- **决策变量**：
  - `seats[(t, g)]`：布尔变量，宾客 g 是否坐在桌 t；
  - `colocated[(g1, g2)]`：布尔变量，宾客 g1 与 g2 是否同桌（对 g1 < g2 建）；
  - `same_table[(g1, g2, t)]`：布尔变量，宾客 g1 与 g2 是否同在桌 t（对 g1 < g2 与每张桌子建）。
- **目标函数**：`model.maximize(sum(connections[g1][g2] * colocated[g1, g2]))`——对每一对相识（`connections > 0` 过滤）的宾客，若同桌则计入其关系强度，最大化总和。
- **约束条件**：
  - 每人恰好坐一张桌：`model.add(sum(seats[(t, g)] for t in all_tables) == 1)`；
  - 桌容量限制：`model.add(sum(seats[(t, g)] for g in all_guests) <= table_capacity)`；
  - 变量联动：
    - 用 `model.add_bool_or([~seats[(t, g1)], ~seats[(t, g2)], same_table[(g1, g2, t)]])` 表达"g1、g2 都在桌 t ⇒ same_table 为真"；
    - 用 `model.add_implication(same_table[(g1, g2, t)], seats[(t, g1)])` 与 `... seats[(t, g2)])` 表达反向蕴含"same_table ⇒ 两人都在桌 t"；
    - `model.add(sum(same_table[(g1, g2, t)] for t in all_tables) == colocated[(g1, g2)])`，把"同桌"与"同某桌"关联起来；
  - 最少认识邻居约束：对每位宾客 g，将其所有认识的宾客（g2 > g 用 `same_table[(g, g2, t)]`，g1 < g 用 `same_table[(g1, g, t)]`）的同桌布尔量求和，要求 `>= min_known_neighbors`；
  - 对称性破除：`model.add(seats[(0, 0)] == 1)`，固定第一位宾客坐在第一张桌，消除桌子编号的对称解。

## 运行方法

```bash
python3 wedding_optimal_chart_sat.py
```

本示例没有定义任何 absl flags，直接运行即可。默认行为：使用 `solve_with_discrete_model()`（离散/布尔变量建模）构建 5 桌 x 4 座、17 位宾客的模型并求解，每找到一个中间解就由回调打印解序号、耗时、目标值以及每桌的宾客名单，最后输出统计信息（conflicts、branches、wall time、解的数量）。

若传入多余的位置参数，会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

- 类 `WeddingChartPrinter(cp_model.CpSolverSolutionCallback)`：求解回调。`on_solution_callback()` 打印解编号、距开始时间、目标值 `self.objective_value`，以及每张桌子上的宾客名单（用 `self.value(self.__seats[(t, g)])` 判断布尔变量真假）；`num_solutions()` 返回已找到的解数量。
- 函数 `build_data()`：返回 `num_tables, table_capacity, min_known_neighbors, connections, names` 五项数据（含被注释掉的"简单问题"参数）。
- 函数 `solve_with_discrete_model()`：主流程——创建 `cp_model.CpModel()`，声明三组布尔决策变量，设置目标与全部约束，再用 `cp_model.CpSolver()` 求解并传入回调，最后打印统计信息。
- 关键 API：`CpModel.new_bool_var`、`CpModel.maximize`、`CpModel.add`、`CpModel.add_bool_or`、`CpModel.add_implication`、`CpSolverSolutionCallback`（含 `value`、`objective_value`）。

依赖：`time`、`absl.app`、`ortools.sat.python.cp_model`。
