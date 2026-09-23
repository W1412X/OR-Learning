# 线性指派问题 API 示例

使用 `linear_sum_assignment`（线性求和指派）专用算法求解一个 4x4 成本矩阵的最小总成本指派。

## 问题描述

经典的**指派问题（Assignment Problem）**情景：有 4 个"源"（例如 4 名工人）和 4 个"目标"（例如 4 项任务），任意一个源都可以分配给任意一个目标，但每个源只能分配给恰好一个目标，每个目标也只能被恰好一个源承担。已知源 i 承担目标 j 的成本为 `cost[i][j]`：

| | 目标 0 | 目标 1 | 目标 2 | 目标 3 |
|---|---|---|---|---|
| 源 0 | 90 | 76 | 75 | 80 |
| 源 1 | 35 | 85 | 55 | 65 |
| 源 2 | 125 | 95 | 90 | 105 |
| 源 3 | 45 | 110 | 95 | 115 |

- **输入**：上述 4x4 成本矩阵（示例取自 http://www.ee.oulu.fi/~mpa/matreng/eem1_2-1.htm ，其中 `kCost[0][1]` 被修改过以保证最优解唯一）。
- **要求**：找出一个一一对应的完美匹配（每个源恰好对应一个目标），使总成本最小。

## 建模思路

这是图论中的**最小权完美匹配**问题，不需要手写约束，专用求解器 `SimpleLinearSumAssignment` 直接建模：

- **图结构**：左侧节点为源（0..3），右侧节点为目标（0..3），通过 `add_arc_with_cost(source, target, cost[source][target])` 为每一对（源, 目标）添加一条带成本的有向弧，共 16 条弧。
- **决策**：求解器内部为每条弧决定"选/不选"，隐式约束是每个左节点恰好匹配一个右节点（完美匹配）。
- **目标函数**：最小化被选中弧的成本之和，即最小化 \(\sum cost[i][j] x_{ij}\)。
- **验证基准**：代码预先计算了已知最优解 `expected_cost = cost[0][3] + cost[1][2] + cost[2][1] + cost[3][0]`，用于与求解结果对比。

本例的最优指派为：源 0→目标 3、源 1→目标 2、源 2→目标 1、源 3→目标 0。

## 运行方法

```bash
python3 linear_assignment_api.py
```

- 本示例**没有定义任何 absl flags**，默认行为是直接对内置的 4x4 成本矩阵求解并打印结果。
- 若传入多余的位置参数会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

- **代码结构**：单文件脚本，仅包含一个主函数 `run_assignment_on_4x4_matrix()` 和标准的 `main(argv)` 入口（使用 `absl.app.run` 启动）。
- **关键 API**（均来自 `ortools.graph.python.linear_sum_assignment` 模块的 `SimpleLinearSumAssignment` 类）：
  - `linear_sum_assignment.SimpleLinearSumAssignment()`：创建最小权和指派求解器实例（底层为匈牙利算法风格的专用图算法）。
  - `add_arc_with_cost(source, target, cost)`：添加一条从左节点到右节点的带成本弧。
  - `solve()`：求解，返回状态；可能的状态有 `OPTIMAL`（找到最优完美匹配）、`INFEASIBLE`（不存在完美匹配）、`POSSIBLE_OVERFLOW`（某些成本过大可能导致整数溢出）。
  - `optimal_cost()`：返回最优总成本。
  - `num_nodes()`：返回左（右）侧节点数。
  - `right_mate(i)`：返回左节点 i 被指派到的右节点编号。
  - `assignment_cost(i)`：返回左节点 i 对应弧的成本。
