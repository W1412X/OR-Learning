# chemical_balance_lp

用线性规划（GLOP 求解器）求解化肥配比问题：决定各化肥组合的使用份数，使各养分总量尽量贴近但不突破配额，并最小化最大缺口 epsilon。

## 问题描述

生产肥料时需要满足 7 种养分的配额上限（`max_quantities`：N_Total 1944、P2O5 1166.4、K2O 1822.5、CaO 1458、MgO 486、Fe 9.7、B 2.4）。市场上有 5 种化肥组合（`chemical_set` 的 A~E，每行给出名称及单份组合中各养分的含量）。

输入：各养分配额、各化肥组合的单份养分含量。要求：决定每种组合各使用多少份，使每种养分的实际总量尽量接近（但不得超过）其配额；"贴近程度"用统一的缺口变量 epsilon 度量——任何一种养分允许的最大不足额。

## 建模思路

- **决策变量**：
  - `set_vars[s]`（`solver.NumVar(0, max_set[s])`）：化肥组合 s 使用的份数；上界 `max_set[s]` 预计算——对含量非零的养分取"配额 / 单份含量"的最小值（保证单用该组合也不超配额）；
  - `epsilon`（`solver.NumVar(0, 1000)`）：允许的最大养分缺口。
- **约束**（对每种养分 p，用 `solver.Add` 添加两条）：
  - 上限：`sum(chemical_set[s][p+1] * set_vars[s]) <= max_quantities[p][1]`（总量不得超过配额）；
  - 下限：`sum(chemical_set[s][p+1] * set_vars[s]) >= max_quantities[p][1] - epsilon`（总量至少达到配额减 epsilon）。
- **目标函数**：`solver.Minimize(epsilon)`——最小化最大缺口，使各养分的配给量整体上尽可能贴近配额。

## 运行方法

```bash
python3 chemical_balance_lp.py
```

本示例没有定义任何 absl flags，也没有 `main` 函数：脚本自顶向下直接执行。依次打印变量数与约束数、求解耗时、最优目标值（最优 epsilon）、各化肥组合的使用份数（`A = ...` 等），以及每种养分的实际配给量与配额对比（如 `N_Total: 1900.2 out of 1944`）。

## 关键实现说明

- 脚本式结构（无类/函数），使用 `ortools.linear_solver.pywraplp` 的经典 LP API：
  - `pywraplp.Solver("chemical_set_lp", pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)`：创建 GLOP 线性规划求解器；
  - `max_set` 列表推导：预计算每种组合的最大可用份数；
  - `solver.NumVar(...)`：连续型决策变量（LP，非整数）；
  - `solver.Add(...)`：养分上限/下限两组约束；
  - `solver.Minimize(epsilon)`：目标函数；
  - `solver.Solve()`：求解；`assert result_status == pywraplp.Solver.OPTIMAL` 确认最优；
  - `solver.VerifySolution(1e-7, True)`：按容差校验解的正确性；
  - `solver.Objective().Value()`：读取目标值；`set_vars[s].solution_value()`：读取各组合份数。
- 注意：文件顶部模块 docstring 是上游模板遗留文字（与 balance_group_sat 相同的分组平衡问题描述），已翻译并加"译注"说明实际内容为化肥配比 LP。
