# prize_collecting_vrp_sat

使用 CP-SAT 求解带最大行驶距离限制的多车辆"奖赏收集"问题（Prize-Collecting VRP），是 `prize_collecting_vrp`（路由库版本）的 CP-SAT 对照实现。

## 问题描述

一个车队（4 辆车）从同一仓库（节点 0）出发服务客户后返回。每个客户带有不同的"奖赏"，但每辆车的行驶里程都有限（80000 米），无法走遍所有客户，必须舍弃部分客户；且每个客户最多由一辆车服务一次。

- 输入（均为硬编码数据）：
  - `DISTANCE_MATRIX`：40 个节点两两之间的距离矩阵（单位：米）；
  - `MAX_DISTANCE = 80_000`：每辆车的最大行驶里程；
  - `VISIT_VALUES`：每个节点的奖赏（按 60000/50000/40000/30000 循环，仓库节点 0 奖赏为 0）；
  - 车辆数 `num_vehicles = 4`。
- 要求：为每辆车规划一条从仓库出发并返回的回路，在每车里程不超限、每个客户至多被访问一次的前提下，最大化"收集的总奖赏 − 总行驶里程"。
- 输出：被丢弃节点及其奖赏、每辆车的路线与里程/奖赏、全队总里程与总奖赏汇总。

## 建模思路

- **决策变量**（按车辆 v 分别创建）：
  - `visited_nodes[v][i]`（变量名 `"{i} is visited"`）：车辆 v 是否访问节点 i 的布尔变量；
  - `used_arcs[v][i, j]`（变量名 `"{j} follows {i}"`）：车辆 v 是否使用弧 (i→j)；约定 `used_arcs[v][i, i] = ~is_visited`（自环 = 未访问）。
- **约束条件**：
  1. 每辆车一个 `model.add_circuit(arcs)`：该车的被访问节点连成一条从仓库出发的回路，未访问节点走自环；
  2. `model.add(visited_nodes[v][0] == 1)`：每辆车都必须访问仓库节点 0；
  3. 每车里程约束：`sum(used_arcs[v][i, j] * DISTANCE_MATRIX[i][j]) <= MAX_DISTANCE`；
  4. `model.add_at_most_one([visited_nodes[v][node] for v in range(num_vehicles)])`：每个客户节点最多被一辆车访问（不重复服务）。
- **目标函数**：`model.maximize(...)`——最大化"所有访问变量的奖赏（`+VISIT_VALUES[i]`）+ 所有使用弧的距离惩罚（`-DISTANCE_MATRIX[i][j]`）"。
- **求解器参数**：`num_search_workers = 8`（并行 worker）、`max_time_in_seconds = 15.0`（时限）、`log_search_progress = True`（日志）。

## 运行方法

```bash
python3 prize_collecting_vrp_sat.py
```

本脚本**没有定义任何 absl flag**（虽然使用 `app.run(main)`，但只校验不接受多余的位置参数，否则触发 `UsageError`）。

默认行为：40 节点、4 辆车、仓库为节点 0、每车最大里程 80000 米、求解时限 15 秒；求得 `FEASIBLE` 或 `OPTIMAL` 解后打印被丢弃节点、每辆车路线及总计，并输出 CP-SAT 搜索日志。

## 关键实现说明

- `cp_model.CpModel` / `model.new_bool_var`：创建模型与布尔决策变量；`visited_nodes`、`used_arcs` 以车辆为键的字典组织。
- 弧三元组 `(i, j, literal)` 与 `model.add_circuit(arcs)`：电路约束，为每辆车表达一条回路；自环字面量 `~is_visited` 表示节点未访问。
- `model.add(...)`：线性约束（访问仓库、每车里程上限）。
- `model.add_at_most_one([...])`：至多选一约束，保证每个客户至多被一辆车服务。
- `model.maximize(...)`：设置最大化目标（奖赏 − 距离惩罚）。
- `cp_model.CpSolver` 与 `solver.parameters`：求解器及时限/并行/日志配置；`solver.solve(model)` 返回状态码，与 `cp_model.FEASIBLE`、`cp_model.OPTIMAL` 比较。
- `print_solution(solver, visited_nodes, used_arcs, num_nodes, num_vehicles)`：先汇总各车访问情况打印被丢弃节点（4 辆车都未访问者）；再对每辆车从节点 0 沿 `used_arcs[v]` 为真的弧游走一圈，累计里程与奖赏后打印。
