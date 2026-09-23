# appointments

用"枚举 + 聚合"两阶段方法为安装队伍规划预约（安装工单）日程：在工人数固定的前提下最大化可完成的预约数，并让各类型预约的占比尽量接近理想比例。

## 问题描述

一家安装服务公司要为一队安装工人安排工作日的预约工单。共有若干种"预约类型"（示例中 3 种：Type1/Type2/Type3），每种类型由三元组（理想占比百分比、名称、单次时长分钟）描述，例如 `(45.0, "Type1", 90)` 表示 Type1 理想上应占全部预约的 45%，每次 90 分钟。每次预约之间还需要通勤时间（默认 30 分钟）。

输入：

- 各预约类型的（理想占比、名称、时长）列表；
- 一名工人一天的总工作负载（含通勤）必须落在 `[load_min, load_max]`（默认 [480, 540] 分钟）；
- 可用的工人数（默认 98，即日程组合的选用总数）。

要求：

1. 每个工人的日程由若干预约组成，总负载在允许区间内；
2. 使用的"日程模板"总数固定（等于工人数）；
3. 目标：完成的预约总数尽量多，同时各类型预约的实际占比尽量贴近理想占比。

## 建模思路

代码分两个阶段求解：

**阶段一（CP-SAT 枚举，`enumerate_all_knapsacks_with_repetition`）**：把"一个工人一天的日程"建模为可重复背包。

- 决策变量：`variables[i]`（`new_int_var(0, total_size_max // size)`）表示第 i 种预约被选中的次数；
- 约束：`load = sum(variables[i] * size)` 落在 `[total_size_min, total_size_max]`（`add_linear_constraint`），其中物品大小 = 预约时长 + 通勤时间；
- 求解配置：`solver.parameters.enumerate_all_solutions = True`，配合解收集器枚举出全部可行日程模板。

**阶段二（SCIP MIP 聚合，`aggregate_item_collections_optimally`）**：从全部日程模板中选出一组（可重复选用），总数固定为工人数。

- 决策变量：`num_selections_of_collection[j]`（模板 j 被选用次数，`IntVar(0, max_num_collections)`）、`num_overall_item[i]`（物品 i 的合计数量）、`num_all_items`（预约总数）、`deviation_vars[i]`（占比偏差，`NumVar`）；
- 约束：
  - `solver.Add(solver.Sum(num_selections_of_collection) == max_num_collections)`（工人数固定）；
  - `num_overall_item[i]` 与各模板选用次数线性绑定（`solver.Constraint(0.0, 0.0)` + `SetCoefficient`）；
  - `num_all_items == sum(num_overall_item)`；
  - `deviation_vars[i] >= num_overall_item[i] - 理想占比[i] * num_all_items` 与反向不等式（两条不等式共同实现绝对值偏差）；
- 目标函数：`solver.Maximize(num_all_items - solver.Sum(deviation_vars))`——预约总数尽量多、偏差尽量小。

## 运行方法

```bash
python3 appointments.py
```

absl flags 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `load_min` | 480 | 每个工人一天的最小工作负载（分钟） |
| `load_max` | 540 | 每个工人一天的最大工作负载（分钟） |
| `commute_time` | 30 | 每次预约之间的通勤时间（分钟） |
| `num_workers` | 98 | 最大工人数（= 选用的日程模板总数） |

示例：`python3 appointments.py --load_min=420 --load_max=600 --num_workers=50`

## 关键实现说明

- `AllSolutionCollector(cp_model.CpSolverSolutionCallback)`：解收集回调类，`on_solution_callback` 中用 `self.value(v)` 读取每个解并把组合存入 `self.__collect`，`combinations()` 返回全部组合。
- `enumerate_all_knapsacks_with_repetition(...)`：用 CP-SAT 枚举所有满足负载区间的可重复背包组合；关键 API：`cp_model.CpModel`、`new_int_var`、`add_linear_constraint`、`parameters.enumerate_all_solutions`、`solver.solve(model, collector)`。
- `aggregate_item_collections_optimally(...)`：用 `pywraplp.Solver.CreateSolver("SCIP")` 建立 MIP 模型；关键 API：`solver.IntVar`、`solver.NumVar`、`solver.Constraint` + `SetCoefficient`、`solver.Add`、`solver.Sum`、`solver.Maximize`、`solver.Solve`。
- `get_optimal_schedule(demand)`：串联两阶段——先以物品大小 `a[2] + _COMMUTE_TIME.value` 枚举日程模板，再以理想比例 `a[0] / 100.0` 选出最优组合，并转换为可读输出。
- `main(_)`：构造示例数据 `[(45.0, "Type1", 90), (30.0, "Type2", 120), (25.0, "Type3", 180)]`，调用求解并打印各类预约的计划数量与占比。
