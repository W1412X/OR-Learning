# transit_time（路线行驶时间展示）

计算并展示给定车辆路线中每一段弧的"经过时间"（transit time = 服务时间 + 行驶时间），单位为分钟。

## 问题描述

这是一个城市配送场景：一辆容量为 15 的车辆从仓库（depot，节点 0）出发，服务于曼哈顿棋盘式街区中的 16 个客户地点。距离按曼哈顿距离计算（模拟纽约曼哈顿的街道格局），车辆平均速度为 5 km/h；在每个客户点需要按需求量装卸货物，每单位需求耗时 5 分钟。

本示例不做优化求解，而是针对 4 条**给定**的路线，逐段打印"从节点 i 到节点 j"所需的总时间（出发点 i 的服务时间 + i→j 的行驶时间），并汇总每条路线的总时间。

输入数据包括：

- 17 个地点坐标（先以"街区数"为单位给出，再按 114m x 80m 的街区实际尺寸换算为米），其中 (4, 4) 为仓库；
- 各地点需求量 `demands`（仓库为 0）；
- 各地点时间窗 `time_windows`（本示例仅作为数据展示，未参与计算）；
- 车辆速度 5 km/h、单位需求装载时间 5 分钟。

输出为 4 条路线（Route 0 ~ Route 3）中每段弧的耗时与每条路线的总耗时。

## 建模思路

本示例不含决策变量、约束条件与目标函数，属于"给定路线的时间评估器"示例（可视为车辆路径问题中 transit callback 的构造演示）：

- 距离度量：`manhattan_distance` 按 `|x1-x2| + |y1-y2|` 计算两点间的曼哈顿距离。
- 服务时间：`service_time` = `demands[node] * time_per_demand_unit`（需求量 x 5 分钟/单位）。
- 行驶时间：`travel_time` = 曼哈顿距离 / 车速 `vehicle.speed`（5 km/h 换算为 m/min，即 `5 * 60 / 3.6`）。
- 总时间（transit time）：从节点 i 到节点 j 的时间 = 出发点 i 的服务时间 + i→j 的行驶时间，结果取整（`int()`）。
- `CreateTimeEvaluator` 在构造时**预计算** 17x17 的总时间矩阵 `self._total_time`，使后续回调查询为 O(1)。

（代码虽然导入了 `ortools.constraint_solver.pywrapcp`，但并未创建求解器，也没有约束和目标，仅演示时间回调的构造方式。）

## 运行方法

```bash
python3 transit_time.py
```

本示例没有定义任何 absl flags，直接运行即可。默认行为：构建 `DataProblem` 数据与总时间矩阵，然后依次打印 Route 0 至 Route 3 这 4 条给定路线中每一段 `i -> j` 的耗时（分钟）以及每条路线的总时间。

## 关键实现说明

- 类 `Vehicle`：车辆属性（容量 `_capacity = 15`，速度 `_speed = 5 * 60 / 3.6` m/min）。
- 类 `CityBlock`：城市街区尺寸（宽 `228/2 = 114` 米、高 80 米），用于把街区单位坐标换算为米。
- 类 `DataProblem`：问题数据容器，以 property 形式暴露地点、需求量、时间窗、仓库下标、单位装载时间等数据。
- 函数 `manhattan_distance`：曼哈顿距离计算。
- 类 `CreateTimeEvaluator`：
  - `service_time(data, node)`：该地点按需求量计算的装载服务时间；
  - `travel_time(data, from_node, to_node)`：两点间的行驶时间；
  - `__init__`：预计算 `self._total_time` 总时间矩阵（服务时间 + 行驶时间，取整）；
  - `time_evaluator(from_node, to_node)`：O(1) 查询回调，可作为 routing 库的 transit callback。
- 函数 `print_transit_time(route, time_evaluator)`：遍历路线的弧列表，打印每段时间与总时间。
- `main`：实例化数据问题 → 创建时间评估器 → 打印 4 条给定路线的时间明细。

依赖：`ortools.constraint_solver`（仅导入 `pywrapcp`，实际计算为纯 Python 实现）。
