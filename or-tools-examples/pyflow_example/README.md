# pyflow_example（最大流与最小费用流示例）

本示例演示如何使用 OR-Tools 的图算法库求解**最大流（MaxFlow）**和**最小费用流（MinCostFlow）**两类经典网络流问题。

## 问题描述

示例包含两个子问题：

1. **最大流问题**：在一个有向网络中，节点之间存在容量限制的管道（弧），需要计算从源点（source，节点 0）到汇点（sink，节点 5）最多能输送多少流量。可以类比为：物流网络中从发货仓库到收货仓库，每条运输线路有运力上限，求单位时间内能运送的最大货量。
   - 输入：9 条弧的起点 `tails`、终点 `heads` 和容量 `capacities`。
   - 要求：最大化从节点 0 到节点 5 的总流量，并输出每条弧上的实际流量以及最小割。

2. **最小费用流问题**：一个 4×4 的任务分配问题。4 个工人（source 节点 0~3）分别要完成 4 项任务（target 节点 4~7），每个工人恰好做一项任务，每项任务恰好由一人完成，不同工人做不同任务的成本不同（成本矩阵 `costs`）。
   - 输入：4×4 的成本矩阵。
   - 要求：在满足一一匹配的前提下，使总成本最小（期望最优成本 275）。

## 建模思路

**最大流部分（`max_flow_api`）**

- 决策变量：每条弧上的流量（由求解器内部决定）。
- 约束条件：
  - 每条弧的流量不超过其容量（通过 `add_arc_with_capacity(tails[i], heads[i], capacities[i])` 声明）。
  - 流量守恒：除源点和汇点外，每个节点的流入等于流出。
- 目标函数：最大化源点 0 到汇点 5 的总流量（通过 `smf.solve(0, 5)` 指定）。
- 求解后通过 `get_source_side_min_cut()` / `get_sink_side_min_cut()` 额外获得最小割两侧的节点集合。

**最小费用流部分（`min_cost_flow_api`）**

- 决策变量：每个"工人→任务"弧上的流量（取值 0 或 1，容量为 1）。
- 约束条件：
  - 每个工人节点供给 `set_node_supply(node, 1)`（发出 1 单位流）。
  - 每个任务节点供给 `set_node_supply(num_sources + node, -1)`（接收 1 单位流），共同实现一一匹配。
  - 每条弧容量为 1（`add_arc_with_capacity_and_unit_cost(source, num_sources + target, 1, costs[source][target])`）。
- 目标函数：最小化所有弧上"流量 × 单位成本"之和，即总分配成本（`optimal_cost()`）。

## 运行方法

```bash
python3 pyflow_example.py
```

本示例**没有定义任何 absl flags 命令行参数**。默认行为是：依次运行 `max_flow_api()` 和 `min_cost_flow_api()` 两个演示，打印最大流结果（总流量、每条弧的流量/容量、最小割节点）和最小费用流结果（最小总成本、被选中分配的工人-任务对）。若传入多余的位置参数，程序会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

代码结构为两个独立演示函数加一个 `main` 入口：

- `max_flow_api()`：最大流演示。
  - 使用 `ortools.graph.python.max_flow.SimpleMaxFlow` 简单接口。
  - `add_arc_with_capacity(tail, head, capacity)`：添加带容量的弧。
  - `solve(source, sink)`：求解并返回状态（`OPTIMAL` 表示成功）。
  - `optimal_flow()`：返回最大总流量。
  - `num_arcs()` / `tail(i)` / `head(i)` / `flow(i)` / `capacity(i)`：遍历每条弧并读取其流量与容量。
  - `get_source_side_min_cut()` / `get_sink_side_min_cut()`：返回最小割两侧的节点列表。
- `min_cost_flow_api()`：最小费用流演示。
  - 使用 `ortools.graph.python.min_cost_flow.SimpleMinCostFlow` 简单接口。
  - `add_arc_with_capacity_and_unit_cost(tail, head, capacity, unit_cost)`：添加带容量和单位费用的弧。
  - `set_node_supply(node, supply)`：设置节点供需（正数为供给，负数为需求）。
  - `solve()`：求解，`optimal_cost()` 返回最小总费用。
- `main(argv)`：absl 的 `app.run(main)` 入口，校验命令行参数后依次调用两个演示。

文档字符串中提示：该最小费用流示例本质上是一个线性指派问题（linear sum assignment），若专门求解指派问题，使用 `LinearSumAssignment` 类会更高效。
