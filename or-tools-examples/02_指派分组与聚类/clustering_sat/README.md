# clustering_sat（聚类问题）

用 CP-SAT 将 40 个城市划分成 4 个等大小的组，最小化各组内城市对之间被"跨越"的距离总和。

## 问题描述

现实情景：市场/物流区域划分。给定 40 个城市之间的两两距离（40×40 的对称距离矩阵 `distance_matrix`，数值近似为米），要求把城市分成 4 个组、每组恰好 10 个城市，目标是让同组城市之间的距离总和尽可能小——即"关系紧密"的城市应被分到同一组。

- 输入：`distance_matrix`，一个 40×40 的对称矩阵，`distance_matrix[n1][n2]` 为城市 n1 到 n2 的距离；
- 要求：划分成 `num_groups = 4` 个等大小的组（`group_size = 40 // 4 = 10`），最小化所有同组城市对的距离之和。

## 建模思路

模型不直接给每个城市分配"组号"，而是对每一对城市建立"是否同组"的布尔变量，并利用等价关系（自反、对称、传递）刻画分组。

- 决策变量：
  - 对每对城市 `n1 < n2`，`same = model.new_bool_var("neighbors_%i_%i")`（存入 `neighbors[(n1, n2)]`）表示两城是否同组；
  - `obj_vars` 收集所有布尔变量，对应的目标系数 `obj_coeffs` 为双向距离之和 `distance_matrix[n1][n2] + distance_matrix[n2][n1]`。
- 约束条件：
  1. 每个城市恰好有 `group_size - 1 = 9` 个同组伙伴：对每个节点 `n`，`model.add(sum(...) == group_size - 1)`（把与 n 配对的所有布尔变量求和）；
  2. 传递性：对任意三元组 `(n1, n2, n3)`，`model.add(neighbors[n1,n3] + neighbors[n2,n3] + neighbors[n1,n2] != 2)`——三对关系不可能恰好成立两对，从而保证"同组"是等价关系，布尔解必然对应真实的划分；
  3. 冗余约束：所有布尔变量之和等于 `num_groups * group_size * (group_size - 1) // 2 = 4×10×9/2 = 180`（每组内的城市对数乘以组数）。
- 目标函数：`model.minimize(sum(obj_vars[i] * obj_coeffs[i]))`，即最小化同组城市对的距离总和（每对按双向距离计）。

## 运行方法

```bash
python3 clustering_sat.py
```

本示例没有自定义 absl flags。`main` 中若传入多余的命令行参数会抛出 `Too many command-line arguments` 错误。

默认行为：
- 求解器参数设置为 `log_search_progress = True`（打印搜索日志）、`num_search_workers = 8`（8 个并行搜索线程）；
- 求解后打印 `solver.response_stats()` 统计信息；
- 若找到可行解或最优解，通过 `visited` 集合逐组打印成员，形如 `Group 0 : 3 5 9 ...`。

## 关键实现说明

- 代码结构：模块级数据 `distance_matrix` + 函数 `clustering_sat()`（建模、求解、打印）。
- 关键 API：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_bool_var(name)`：为每对城市定义"是否同组"的布尔变量；
  - `model.add(...)`：添加邻居计数约束、三元组传递性约束（`!=` 线性约束）与冗余的总量约束；
  - `model.minimize(...)`：按距离系数加权求和并设为最小化目标；
  - `solver.parameters.log_search_progress` / `solver.parameters.num_search_workers`：配置求解器日志与并行度；
  - `solver.boolean_value(neighbors[n, o])`：读取布尔变量取值；
  - `solver.response_stats()`：输出求解统计摘要。
- 输出技巧：打印分组时不直接输出组号变量（模型中没有），而是遍历未访问城市，用 `neighbors` 关系把它所在组的其他成员一次性收集出来。
