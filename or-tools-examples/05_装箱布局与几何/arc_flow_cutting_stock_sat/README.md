# arc_flow_cutting_stock_sat

用弧流（arc-flow）建模求解下料问题（cutting stock）：用最少的原材料切出全部零件，目标是最小化浪费的空间。提供 CP-SAT 与 MIP（SCIP）两种求解方式。

## 问题描述

工厂要把一批零件（`DESIRED_LENGTHS`，136 个不同长度的零件）从标准原材料上切割下来。原材料有 5 种候选容量 `POSSIBLE_CAPACITIES = [4000, 5000, 6000, 7000, 8000]`，每种容量可无限量取用。要求：

- 每种零件必须按需求数量全部切出；
- 每根原材料上可切多个零件（总长不超过所选容量）；
- 目标：最小化总浪费 = Σ(每根原材料的所选容量 − 实际用量)。

输入是零件长度清单与候选容量列表；输出是最优总浪费（由求解器日志给出）。

## 建模思路

核心是把"一根原材料怎么切"编码为状态图（弧流模型）：

- **状态图构造**（`create_state_graph`）：状态 = 当前已装入的长度（动态规划生成，从 0 开始逐步累加各零件长度且不超过 `max_capacity`）；转移弧 `[当前状态, 新状态, 物品编号, card]` 表示一次装入 `card` 件同种零件。源点为状态 0。
- **决策变量**：
  - 每条转移弧一个整数变量 `count_var`（CP-SAT 版 `model.NewIntVar(0, max_count)`，上界 `count // card` 受该零件总量限制；MIP 版 `model.new_int_var(0, count)`）——该弧被多少根原材料使用；
  - 每个非源状态一条"结束弧"`exit_var`（`NewIntVar(0, num_items)`）——有多少根原材料在该状态完成切割，其代价 `price = price_usage(state, POSSIBLE_CAPACITIES)`（恰好容纳该用量的最小容量减去用量，即该根的浪费）。
- **约束**：
  - 流守恒：除源点外每个状态 `sum(incoming_vars) == sum(outgoing_vars)`；
  - `sum(outgoing_vars[0]) == sum(incoming_sink_vars)`（源点流出 = 汇点流入 = 使用的原材料根数）；
  - 需求覆盖：每种零件在所有弧上装载的总件数 `sum(item_vars[i] * item_coeffs[i]) == 需求量`。
- **目标函数**：`model.Minimize(sum(exit_var * price))`，即最小化总浪费。

## 运行方法

```bash
python3 arc_flow_cutting_stock_sat.py                 # 默认用 CP-SAT 求解
python3 arc_flow_cutting_stock_sat.py --solver=mip    # 用 MIP（SCIP）求解
```

absl flags 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `output_proto` | `""` | 若非空，把 CP-SAT 模型 proto 导出到该文件 |
| `params` | `num_search_workers:8,log_search_progress:true,max_time_in_seconds:10` | 传给 CP-SAT 求解器的参数（文本格式）：8 个搜索线程、输出搜索日志、限时 10 秒 |
| `solver` | `sat` | 求解方式：`sat`（CP-SAT）或 `mip`（SCIP） |

## 关键实现说明

- `regroup_and_count(raw_input)`：把零件长度归并计数为多重集 `[[size, count], ...]`。
- `price_usage(usage, capacities)`：返回选用"恰好装得下的最小容量"时的浪费量（容量 − 用量的最小值）。
- `create_state_graph(items, max_capacity)`：动态规划生成状态与转移弧列表。
- `solve_cutting_stock_with_arc_flow_and_sat(...)`：CP-SAT 实现。关键 API：`cp_model.CpModel`、`NewIntVar`、`model.Add`、`model.Minimize`、`model.ExportToFile`（`--output_proto` 时导出 proto）、`solver.parameters.parse_text_format`（解析 `--params`）。
- `solve_cutting_stock_with_arc_flow_and_mip()`：MIP 实现，使用 `ortools.linear_solver.python.model_builder`（别名 `mb`）API：`mb.ModelBuilder`、`model.new_int_var`、`model.add`、`mb.LinearExpr.sum`、`np.dot(objective_vars, objective_coeffs)` 作目标、`mb.ModelSolver("scip")` 求解并按 `mb.SolveStatus.OPTIMAL/FEASIBLE` 输出目标值。
- `main(_)`：按 `--solver` 参数分发给两个求解函数。
- 文件中保留了被注释的玩具数据（`DESIRED_LENGTHS = [12, 12, 8, 8, 8]` 等），取消注释即可用小算例调试。
