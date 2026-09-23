# prize_collecting_tsp_sat

使用 CP-SAT 求解带最大行驶距离限制的"奖赏收集"旅行商问题（Prize-Collecting TSP），是 `prize_collecting_tsp`（路由库版本）的 CP-SAT 对照实现。

## 问题描述

一名配送员从仓库（节点 0）出发访问客户后返回。每个客户带有不同的"奖赏"，但总行驶里程有限（80000 米），必须舍弃部分客户。

- 输入（均为硬编码数据）：
  - `DISTANCE_MATRIX`：40 个节点两两之间的距离矩阵（单位：米）；
  - `MAX_DISTANCE = 80_000`：最大行驶里程；
  - `VISIT_VALUES`：每个节点的奖赏（按 60000/50000/40000/30000 循环，仓库节点 0 奖赏为 0）。
- 要求：规划一条从仓库出发并回到仓库的回路，在总里程不超过上限的前提下，最大化"收集的奖赏 − 行驶里程"。
- 输出：被丢弃节点及其奖赏、路线节点序列、路线总里程、收集的奖赏汇总。

与路由库版本的区别：本例是精确数学规划建模，通过 `add_circuit` 电路约束表达回路，可用 CP-SAT 全局最优求解。

## 建模思路

- **决策变量**：
  - `visited_nodes[i]`（变量名 `"{i} is visited"`）：节点 i 是否被访问的布尔变量；
  - `used_arcs[i, j]`（变量名 `"{j} follows {i}"`）：弧 (i→j) 是否被使用的布尔变量；约定 `used_arcs[i, i] = ~is_visited`（自环表示"未访问"）。
- **约束条件**：
  1. `model.add_circuit(arcs)`：电路约束——所有被访问节点由所选弧连成**一条**哈密顿回路，未访问节点走自环（脱离回路）；
  2. `model.add(visited_nodes[0] == 1)`：仓库节点 0 必须被访问；
  3. 里程约束：`sum(used_arcs[i, j] * DISTANCE_MATRIX[i][j]) <= MAX_DISTANCE`——所用弧的距离之和不超过最大里程。
- **目标函数**：`model.maximize(sum(obj_vars[i] * obj_coeffs[i]))`——最大化"访问节点的奖赏（系数 `+VISIT_VALUES[i]`）+ 使用弧的距离惩罚（系数 `-DISTANCE_MATRIX[i][j]`）"，即奖赏收集的目标。
- **求解器参数**：`max_time_in_seconds = 15.0`（时限）、`num_search_workers = 8`（并行 worker）、`log_search_progress = True`（日志）。代码注释指出：多 worker 求解有助于利用电路约束的线性化。

## 运行方法

```bash
python3 prize_collecting_tsp_sat.py
```

本脚本**没有定义任何 absl flag**（虽然使用 `app.run(main)`，但只校验不接受多余的位置参数，否则触发 `UsageError`）。

默认行为：40 节点、单辆车、仓库为节点 0、最大里程 80000 米、求解时限 15 秒；求得 `FEASIBLE` 或 `OPTIMAL` 解后打印被丢弃节点、路线、里程与收集的奖赏，并输出 CP-SAT 搜索日志。

## 关键实现说明

- `cp_model.CpModel` / `model.new_bool_var`：创建模型与布尔决策变量。
- `arcs` 列表的三元组 `(i, j, literal)` 与 `model.add_circuit(arcs)`：电路约束 API，是表达 TSP 回路的核心——字面量为真表示弧被选中；自环字面量 `~is_visited` 为真表示节点未访问。
- `~is_visited`：布尔变量的取反（Python 重载运算符），用于自环。
- `model.add(...)`：线性约束（访问节点 0、里程上限）。
- `model.maximize(...)`：设置最大化目标函数（奖赏 − 距离惩罚）。
- `cp_model.CpSolver` 与 `solver.parameters`：求解器及时限/并行/日志参数；`solver.solve(model)` 返回状态，与 `cp_model.FEASIBLE`、`cp_model.OPTIMAL` 比较；`solver.boolean_value(var)` 读取布尔变量取值。
- `print_solution(solver, visited_nodes, used_arcs, num_nodes)`：先打印被丢弃节点（`visited_nodes[i]` 为假者），再从节点 0 出发沿 `used_arcs` 为真的弧逐步游走（回到 0 结束），累计距离与奖赏后打印。
