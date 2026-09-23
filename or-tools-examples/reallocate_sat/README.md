# reallocate_sat（生产再分配：平滑多年产量）

本示例使用 **CP-SAT 求解器**解决"把生产任务在多个年度间重新分配，使各年总产量尽可能平滑（均衡）"的问题。

## 问题描述

一家企业有若干项目（产品线），每个项目在若干年度上有既定的产量计划。计划往往不均衡：有的年份产量极高，有的年份接近于零。企业希望**重新分配各项目在各年度的产量**——每个项目的总量保持不变，但可以让某个项目把部分产量提前或推后到其他年份——目标是让**每个年度的总产量尽可能接近各年平均值**，从而使产能、人力与现金流在各年之间更加平滑。

- 输入：代码内置的数据集 `data_0`（4 个项目 × 5 年，`pr` 变量实际选用 `data_0`），其中 `data_1`、`data_2` 是另外两组更大规模的示例数据（7 个项目 × 4 年）。`pr[p][y]` 表示项目 `p` 在第 `y` 年的产量；为 0 表示该（项目, 年份）组合不可用。
- 要求：在"每个项目各年产量之和不变、且只能在原有非零格子上调整"的前提下，最小化各年总产量与平均值 `avg` 之间的最大偏差 `delta`。

## 建模思路

- **决策变量**：
  - `contrib`：每个非零格子（项目 `p`，年份 `y`）一个整数变量 `"r%d c%d" % (p, y)`，取值范围 `[0, total]`，表示重新分配后该项目在该年的产量（`all_contribs[p, y]` 记录，`contributions_per_years[y]` / `contributions_per_prs[p]` 按年份/项目分组收集）。
  - `year_var[y]`：第 `y` 年的年度总产量（`"y[%i]" % i`）。
  - `delta`：各年产量与平均值的最大偏差（目标变量）。
- **约束条件**：
  - 年度总量守恒：`year_var[y] == sum(contributions_per_years[y])`，即某年总产量等于该年所有项目贡献之和。
  - 项目总量守恒：`sum(pr[p]) == sum(contributions_per_prs[p])`，即每个项目被重新分配后的各年产量之和与原计划一致（注意：非零格子才创建变量，因此产量只能落在原本有产量的格子里）。
  - 平滑约束（与 `delta` 联动）：对每个年份 `y`，`year_var[y] >= avg - delta` 且 `year_var[y] <= avg + delta`。
- **目标函数**：`model.Minimize(delta)`——最小化年度产量与平均值之间的最大偏差；`delta = 0` 意味着各年产量完全均衡。

## 运行方法

```bash
python3 reallocate_sat.py
```

本示例**没有定义任何 absl flags 命令行参数**，也没有使用 absl 框架（入口为普通 `main()`）。默认行为：使用内置数据集 `data_0`（4 个项目 × 5 年）建模求解，打印原始数据（总量、年平均值、项目数、年数、输入产量表）、重新分配后的产量表以及各年的总产量行。代码中切换数据集只需修改 `pr = data_0` 一行（可改为 `data_1` 或 `data_2`）。

## 关键实现说明

- 数据部分：`data_0` / `data_1` / `data_2` 三组内置数据集；`pr = data_0` 选择当前使用的数据；`total` 为总产量，`avg = total // num_years` 为年度平均值。
- 建模部分（`cp_model.CpModel()`）：
  - `model.NewIntVar(...)`：创建 `delta`、各格子贡献变量 `contrib`、年度变量 `year_var`。
  - `collections.defaultdict(list)`：`contributions_per_years` / `contributions_per_prs` 分别按年份和项目聚合贡献变量。
  - `model.Add(...)`：添加年度守恒、项目守恒和 `avg ± delta` 平滑约束。
  - `model.Minimize(delta)`：设置最小化目标。
- 求解与输出：
  - `cp_model.CpSolver()` + `solver.Solve(model)`：求解模型，返回状态。
  - `status == cp_model.OPTIMAL` 时，用 `solver.Value(...)` 读取重新分配后的产量（`all_contribs[p, y]`）与各年总产量（`year_var[y]`）并格式化打印。
