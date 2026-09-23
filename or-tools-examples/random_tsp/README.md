# random_tsp（随机旅行商问题示例）

本示例使用 OR-Tools 的 **Routing（路径规划）库**求解**旅行商问题（TSP, Traveling Salesman Problem）**，支持随机生成距离矩阵，并可选地随机禁用若干条节点间的连接（forbidden arcs）。

## 问题描述

旅行商问题：一名旅行商要访问 n 个城市各一次，最后回到出发点，求总路程（总成本）最短的访问顺序。

- 输入：节点数量 `--tsp_size`；距离来源有两种——默认使用随机生成的成本矩阵（`RandomMatrix`，元素为 0~99 的随机整数，对角线为 0），也可切换为演示用的简单距离函数 `node_i + node_j`；还可通过 `--tsp_random_forbidden_connections` 指定随机禁用的连接数。
- 要求：输出一条从节点 0 出发、经过所有节点恰好一次并回到起点的路径，以及该路径的总成本（目标值）。求解引擎使用局部搜索（local search）改进解，初始解由"最廉价弧添加"（cheapest addition）启发式生成。

## 建模思路

Routing 库把 TSP 视为"1 辆车、路径长度不限"的车辆路径问题：

- **决策变量**：每个节点的"下一跳"变量 `routing.NextVar(node)`（隐式定义了访问顺序排列），由 `pywrapcp.RoutingIndexManager(tsp_size, 1, 0)` 创建模型（1 辆车，起点为节点 0）。
- **约束条件**：
  - 每个节点在路径中恰好被访问一次（Routing 库内置的路径结构约束）。
  - 可选：随机禁用的连接。通过 `routing.NextVar(from_node).RemoveValue(to_node)` 把某条"下一跳"取值移除，即禁止从某节点直接跳到另一节点（循环直到成功移除 `tsp_random_forbidden_connections` 条）。
- **目标函数**：最小化路径总成本。成本由注册的回调函数给出：
  - 随机矩阵模式：`matrix.Distance(manager, from_index, to_index)`，从 `RandomMatrix.matrix` 查表返回距离；
  - 演示模式：`Distance(manager, i, j)` 返回 `node_i + node_j`。
  回调通过 `routing.RegisterTransitCallback(...)` 注册，再用 `routing.SetArcCostEvaluatorOfAllVehicles(cost)` 设为全局弧成本。
- **求解**：`routing.Solve()` 返回解 `assignment`；`first_solution_strategy` 设为 `PATH_CHEAPEST_ARC`（最廉价弧添加启发式）。

## 运行方法

```bash
python3 random_tsp.py
```

本示例使用 **argparse**（而非 absl）解析命令行参数，可用参数如下：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--tsp_size` | `10` | TSP 实例的规模（节点数） |
| `--tsp_use_random_matrix` | `True` | 是否使用随机成本矩阵（否则使用 `node_i + node_j` 演示距离函数） |
| `--tsp_random_forbidden_connections` | `0` | 随机禁用的连接（禁止弧）数量 |
| `--tsp_random_seed` | `0` | 随机数种子（同时控制矩阵生成与禁用连接） |

示例：

```bash
python3 random_tsp.py --tsp_size=20 --tsp_random_forbidden_connections=5
```

默认行为：求解 10 个节点的随机矩阵 TSP，打印最优目标值（总成本）和路径（形如 `0 -> 3 -> 7 -> ... -> 0`）。若 `--tsp_size <= 0`，则提示 `Specify an instance greater than 0.`；若无解（例如禁用连接导致不可行），打印 `No solution found.`。

## 关键实现说明

- `Distance(manager, i, j)`：演示用距离回调；`manager.IndexToNode(i)` 把 Routing 内部索引转换回原始节点编号。
- `RandomMatrix` 类：
  - `__init__(size, seed)`：用 `random.Random(seed)` 生成 `size×size` 随机矩阵，对角线为 0，其余元素为 `rand.randrange(100)`，存储在 `self.matrix` 字典中。
  - `Distance(manager, from_index, to_index)`：查表返回两个节点间的距离。
- `main(args)`：主流程。
  - `pywrapcp.RoutingIndexManager(tsp_size, 1, 0)`：创建索引管理器（节点数、车辆数 1、起点 0）。
  - `pywrapcp.RoutingModel(manager)`：创建路径规划模型。
  - `pywrapcp.DefaultRoutingSearchParameters()`：默认搜索参数，并把 `first_solution_strategy` 设为 `routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC`。
  - `routing.RegisterTransitCallback(...)` + `routing.SetArcCostEvaluatorOfAllVehicles(cost)`：注册并设置成本函数。
  - `routing.NextVar(from_node).RemoveValue(to_node)`：实现"禁止连接"约束。
  - `routing.Solve()` 求解；通过 `assignment.ObjectiveValue()` 读取总成本，`assignment.Value(routing.NextVar(node))` 沿路径逐节点遍历并拼接输出。
