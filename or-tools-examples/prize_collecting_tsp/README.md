# prize_collecting_tsp

使用 OR-Tools 路由库（constraint_solver）求解带最大行驶距离限制的"奖赏收集"旅行商问题（Prize-Collecting TSP）。

## 问题描述

一名配送员从仓库（节点 0）出发，访问一批客户节点后返回仓库。每个客户带有不同的"奖赏"（完成该客户订单的收益），但车辆的总行驶里程有限。里程不够走遍所有客户时，必须舍弃部分客户（放弃其奖赏）。

- 输入（均为硬编码数据）：
  - `DISTANCE_MATRIX`：40 个节点两两之间的距离矩阵（单位：米）；
  - `MAX_DISTANCE = 80000`：单辆车的最大行驶里程；
  - `VISIT_VALUES`：访问每个节点可获得的奖赏（按 60000/50000/40000/30000 循环，节点 0 即仓库奖赏为 0）。
- 要求：规划一条从仓库出发并返回仓库的路线，在总里程不超过 `MAX_DISTANCE` 的前提下，最大化"收集到的奖赏 − 行驶里程"（丢弃节点的奖赏作为罚金计入目标）。
- 输出：目标值、被丢弃的节点及其奖赏、路线节点序列、路线总里程、收集的奖赏占全部奖赏的比例。

现实类比：快递/外卖单辆车配送——时间或油耗有限，需要权衡"多跑客户赚收益"与"少跑路省成本"，主动放弃收益低、绕路远的客户。

## 建模思路

使用路由库的经典"TSP + 可选节点"建模：

- **决策变量**：路由模型中每辆车各节点的"下一站"链变量（`NextVar`），隐式决定访问顺序；通过析取（disjunction）变量决定每个节点是否被访问。
- **约束条件**：
  1. 距离维度：`routing.AddDimension(transit_callback_index, 0, MAX_DISTANCE, True, 'Distance')`——累积行驶距离从 0 开始、无松弛（slack=0），且不得超过 `MAX_DISTANCE`；
  2. 路线本身必须是从仓库出发、回到仓库的一条链（由路由模型结构保证）。
- **目标函数**：弧成本为节点间距离（`SetArcCostEvaluatorOfAllVehicles`）；同时用 `AddDisjunction` 为节点 1~39 建立可选访问，"丢弃"某节点需支付罚金 `VISIT_VALUES[node]`（即放弃其奖赏）。求解器最小化"总行驶距离 + 被丢弃节点的罚金"，等价于最大化"收集的奖赏 − 行驶距离"。
- **搜索策略**：初始解用 `PATH_CHEAPEST_ARC`（最廉价弧优先），局部搜索用 `GUIDED_LOCAL_SEARCH`（引导式局部搜索）元启发式，时间限制 15 秒。

## 运行方法

```bash
python3 prize_collecting_tsp.py
```

本脚本**没有定义任何 absl flag**（未使用 `absl.flags`，入口为普通 `main()`），也不接受命令行参数。

默认行为：40 节点、1 辆车、仓库为节点 0、最大里程 80000 米、求解时间限制 15 秒；求解完成后打印目标值、被丢弃节点、车辆路线、路线里程与收集的奖赏汇总。

## 关键实现说明

- `pywrapcp.RoutingIndexManager(num_nodes, num_vehicles, depot)`：管理"路由内部索引"与"节点编号"之间的转换，指定仓库（depot=0）。
- `pywrapcp.RoutingModel(manager)`：创建路由模型。
- `distance_callback(from_index, to_index)`：距离回调函数，经 `manager.IndexToNode` 把路由索引转换为节点编号后查 `DISTANCE_MATRIX`；用 `routing.RegisterTransitCallback` 注册，并作为弧成本（`SetArcCostEvaluatorOfAllVehicles`）。
- `routing.AddDimension(...)`：添加名为 `'Distance'` 的距离维度，实现"车辆最大行驶里程"约束（无 slack、起始累计值为 0）。
- `routing.AddDisjunction([manager.NodeToIndex(node)], VISIT_VALUES[node])`：允许跳过节点，跳过的代价是其奖赏值——这是"奖赏收集"语义的关键 API。
- `pywrapcp.DefaultRoutingSearchParameters()`：搜索参数，设置 `first_solution_strategy = PATH_CHEAPEST_ARC`、`local_search_metaheuristic = GUIDED_LOCAL_SEARCH`、`time_limit.FromSeconds(15)`；用 `routing.SolveWithParameters(search_parameters)` 求解。
- `print_solution(manager, routing, assignment)`：打印目标值（`assignment.ObjectiveValue()`）、被丢弃节点（`NextVar(index) == index` 的节点）、路线（沿 `NextVar` 遍历）、里程（`routing.GetArcCostForVehicle`）与收集的奖赏。
