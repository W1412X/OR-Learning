# chemical_balance_sat（化学平衡问题）

用 CP-SAT 求解"如何搭配若干种化工原料，使 7 种养分元素的供给总量尽可能贴近各自目标上限"的化学配料平衡问题。

## 问题描述

现实情景：化肥（或饲料）配方设计。需要把 A、B、C、D、E 五种化工原料按一定数量混合，混合物中每种养分元素（N_Total、P2O5、K2O、CaO、MgO、Fe、B 共 7 种）的供给量既不能超过目标用量，又希望尽量贴近目标，避免浪费原料。

- 输入：
  - `max_quantities`：7 种养分元素的目标用量（上限），例如 N_Total 为 1944、P2O5 为 1166.4、Fe 为 9.7；
  - `chemical_set`：5 种化工原料（A~E），每行给出该原料对 7 种养分的单位贡献量（0 表示不含该养分）。
- 要求：确定每种原料的使用量，使每种养分的总供给量不超过目标上限，并且总短缺量（缺口）尽可能小。

## 建模思路

由于数量带有小数，代码将所有数量统一放大（使用量放大 1000 倍、约束中的贡献量放大 10000 倍）后用整数建模。

- 决策变量：
  - `set_vars[s]`（`model.new_int_var(0, max_set[s], f"set_{s}")`）：第 s 种原料的使用量（放大 1000 倍后的整数值）；上界 `max_set[s]` 按"任一养分都不超目标"反推：对原料 s 含有的各养分 q，取 `max_quantities[q][1] * 1000 / chemical_set[s][q+1]` 的最小值再向上取整；
  - `epsilon`（`model.new_int_var(0, 10000000, "epsilon")`）：允许的最大总短缺量（目标偏差）。
- 约束条件：对每种养分 p，要求组合出的供给量夹在 `[目标 - epsilon, 目标]` 区间内：
  - 上界约束：`sum(int(chemical_set[s][p+1] * 10) * set_vars[s]) <= int(max_quantities[p][1] * 10000)`，即总供给量不超过目标上限；
  - 下界约束：`sum(...) >= int(max_quantities[p][1] * 10000) - epsilon`，即短缺量不超过 `epsilon`。
- 目标函数：`model.minimize(epsilon)`，最小化最大短缺量，使各养分供给量尽可能贴近目标。

## 运行方法

```bash
python3 chemical_balance_sat.py
```

本示例没有自定义 absl flags。`main` 中若传入多余的命令行参数会抛出 `Too many command-line arguments` 错误。

默认行为：对内置数据求解最优解，并打印：
- 最优目标值（`solver.objective_value / 10000.0`，还原为真实短缺量）；
- 每种原料的使用量（`solver.value(set_vars[s]) / 1000.0`，还原为真实数量）；
- 每种养分元素的实际供给量与目标上限的对比（形如 `N_Total: 1943.999 out of 1944`）。

## 关键实现说明

- 代码结构：单个函数 `chemical_balance()`，按"数据 → 建模 → 求解 → 打印"四段组织；`main` 负责校验命令行参数。
- 关键 API：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_int_var(lb, ub, name)`：定义整数变量（原料用量、epsilon）；
  - `model.add(...)`：添加线性约束（每种养分的上界/下界约束）；
  - `model.minimize(epsilon)`：设置目标函数；
  - `cp_model.CpSolver().solve(model)`：创建求解器并求解，返回状态码；
  - `status == cp_model.OPTIMAL`：仅在求得最优解时打印结果；
  - `solver.objective_value` / `solver.value(var)`：读取目标值与变量取值。
- 实现细节：`max_set` 用生成器表达式对每种原料计算用量上界，只统计该原料中含量非 0 的养分（`if chemical_set[s][q + 1] != 0`），避免除以 0。
