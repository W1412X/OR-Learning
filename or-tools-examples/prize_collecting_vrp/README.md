# prize_collecting_vrp

使用 OR-Tools 路由库（constraint_solver）求解带最大行驶距离限制的多车辆"奖赏收集"问题（Prize-Collecting VRP），是 `prize_collecting_tsp` 的多车辆版本。

## 问题描述

一个车队（4 辆车）从同一仓库（节点 0）出发，服务一批客户节点后返回。每个客户带有不同的"奖赏"，但每辆车的行驶里程都有限（80000 米），无法走遍所有客户，必须舍弃部分客户。

- 输入（均为硬编码数据）：
  - `DISTANCE_MATRIX`：40 个节点两两之间的距离矩阵（单位：米）；
  - `MAX_DISTANCE = 80_000`：每辆车的最大行驶里程；
  - `VISIT_VALUES`：访问每个节点可获得的奖赏（按 60000/50000/40000/30000 循环，节点 0 仓库奖赏为 0）；
  - 车辆数 `num_vehicles = 4`。
- 要求：为每辆车规划一条从仓库出发并返回的路线，在每车里程不超限的前提下，最大化收集的总奖赏（减去行驶距离，见目标函数）。
- 输出：目标值、被丢弃的节点及其奖赏、每辆车的路线与里程、收集的奖赏、全队总里程与总奖赏汇总。

现实类比：多辆配送车共同覆盖一片客户区域——需要决定"派哪辆车去赚哪个客户的收益"，以及放弃哪些收益低、绕路远的客户。

## 建模思路

- **决策变量**：每辆车各节点的"下一站"链变量（`NextVar`）；通过析取（disjunction）变量决定每个节点是否被任何一辆车访问。
- **约束条件**：
  1. 距离维度：`routing.AddDimension(transit_callback_index, 0, MAX_DISTANCE, True, 'Distance')`——每辆车的累积行驶距离从 0 开始（无 slack），不得超过 `MAX_DISTANCE`；
  2. `distance_dimension.SetGlobalSpanCostCoefficient(1)`：全局跨度成本系数为 1，鼓励各车路线的累计距离更加均衡（减小"最长路线与最短路线的差距"在目标中的权重）。
- **目标函数**：
  - 弧成本为节点间距离（`SetArcCostEvaluatorOfAllVehicles`）；
  - 节点 1~39 均通过 `AddDisjunction` 设为可选访问，"丢弃"节点的罚金为其奖赏值 `VISIT_VALUES[node]`；
  - 求解器最小化"总行驶距离 + 全局跨度项 + 被丢弃节点的罚金"。
- **搜索策略**：初始解 `PATH_CHEAPEST_ARC`，元启发式 `GUIDED_LOCAL_SEARCH`，时间限制 15 秒。

## 运行方法

```bash
python3 prize_collecting_vrp.py
```

本脚本**没有定义任何 absl flag**（未使用 `absl.flags`，入口为普通 `main()`），也不接受命令行参数。

默认行为：40 节点、4 辆车、仓库为节点 0、每车最大里程 80000 米、求解时间限制 15 秒；求解完成后打印目标值、被丢弃节点、每辆车的路线/里程/奖赏以及全队总计。

## 关键实现说明

- `pywrapcp.RoutingIndexManager(num_nodes, num_vehicles, depot)`：索引管理器，指定节点数、车辆数与仓库（depot=0）。
- `pywrapcp.RoutingModel(manager)`：创建路由模型。
- `distance_callback(from_index, to_index)`：距离回调，经 `manager.IndexToNode` 转换索引后查 `DISTANCE_MATRIX`；用 `RegisterTransitCallback` 注册并作为弧成本。
- `routing.AddDimension(...)`：距离维度，实现"每车最大里程"约束（无 slack、起始累计值为 0）。
- `routing.GetDimensionOrDie('Distance')` 与 `SetGlobalSpanCostCoefficient(1)`：在目标中加入全局跨度成本，促进负载均衡。
- `routing.AddDisjunction([manager.NodeToIndex(node)], VISIT_VALUES[node])`：允许跳过节点并支付奖赏作为罚金——"奖赏收集"语义的关键 API。
- `pywrapcp.DefaultRoutingSearchParameters()`：`PATH_CHEAPEST_ARC` 初始解 + `GUIDED_LOCAL_SEARCH` 元启发式 + `time_limit.FromSeconds(15)`；用 `routing.SolveWithParameters(search_parameters)` 求解。
- `print_solution(manager, routing, assignment)`：打印目标值；用 `routing.IsVehicleUsed(assignment, v)` 过滤未用车辆，沿 `NextVar` 遍历每辆车的路线，累计 `GetArcCostForVehicle` 得到里程，最后汇总总里程与总奖赏。
