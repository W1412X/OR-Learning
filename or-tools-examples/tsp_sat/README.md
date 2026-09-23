# tsp_sat（基于 CP-SAT 的旅行商问题）

使用 CP-SAT 求解器的 `add_circuit` 约束求解城市之间的旅行商问题（TSP），找出访问所有城市恰好一次并回到起点的最短路线。

## 问题描述

旅行商问题（TSP）：一名商人需要访问 n 个城市，从某地出发，经过每个城市恰好一次，最后返回出发地，要求总行程最短。

本示例内置一个 **40 个节点**的距离矩阵 `DISTANCE_MATRIX`（对称矩阵，对角线为 0，其余元素为两节点间的距离，单位可理解为米）。输入即该距离矩阵；要求输出一条访问全部 40 个节点恰好一次的回路，使经过的弧的距离总和最小，并打印该路线与总距离。

## 建模思路

- **决策变量**：对每一对不同的节点 (i, j) 创建布尔变量 `lit`（命名如 `"%j follows %i"`），其含义是"路线中包含弧 i→j"。所有弧存入 `arcs = [(i, j, lit), ...]`，并建立 `arc_literals[(i, j)] = lit` 映射以便事后还原路线。
- **约束条件**：`model.add_circuit(arcs)` —— 电路/回路约束，要求每个节点恰有一条出弧和一条入弧，且整体构成单一哈密尔顿回路（未添加自环弧 (i, i, lit)，因此解必须是一条经过所有节点的单一回路）。
- **目标函数**：`model.minimize(sum(obj_vars[i] * obj_coeffs[i]))`，即最小化所有被选中弧的距离加权和：每条弧的布尔变量乘以其距离 `DISTANCE_MATRIX[i][j]` 后求和。
- **求解器参数**：`log_search_progress = True` 打开搜索日志；`linearization_level = 2` 提高 circuit 约束的线性化程度，利用 LP 松弛/割平面加速求解。

## 运行方法

```bash
python3 tsp_sat.py
```

本示例没有定义任何 absl flags，直接运行即可。默认行为：

1. 打印节点数（`Num nodes = 40`）；
2. 输出 CP-SAT 求解日志（因 `log_search_progress=True`）；
3. 打印求解统计信息 `solver.response_stats()`；
4. 从节点 0 开始沿被选中的布尔弧还原并打印路线 `Route:` 与总距离 `Travelled distance:`。

## 关键实现说明

- 数据：模块级常量 `DISTANCE_MATRIX` —— 40x40 对称距离矩阵（含 `# fmt:off / # fmt:on` 格式化标记）。
- `main()` 为唯一函数，流程如下：
  - 创建 `cp_model.CpModel()` 模型；
  - 双重循环为所有 i≠j 的有序对创建布尔弧变量（`new_bool_var`），收集 `arcs`、`arc_literals`、目标项 `obj_vars`/`obj_coeffs`；
  - `model.add_circuit(arcs)` 添加回路约束；
  - `model.minimize(...)` 设置目标函数；
  - 创建 `cp_model.CpSolver()`，配置参数后 `solver.solve(model)` 求解；
  - `solver.boolean_value(arc_literals[current_node, i])` 逐段判断弧是否被选中，从节点 0 走回节点 0，累计 `route_distance` 并拼出路线字符串；
  - 打印路线与总距离。
- 关键 API：`CpModel.new_bool_var`、`CpModel.add_circuit`、`CpModel.minimize`、`CpSolver.solve`、`CpSolver.boolean_value`、`CpSolver.response_stats`、`solver.parameters.linearization_level`。

依赖：`ortools.sat.python.cp_model`。
