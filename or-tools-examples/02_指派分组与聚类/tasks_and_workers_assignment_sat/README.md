# tasks_and_workers_assignment_sat（任务与工人分组问题）

把任务和工人分配到若干组中，使**各组人均成本的最大值**（sum(cost)/#workers）最小。

## 问题描述

这是一个面向"组间公平"的分组/指派问题：

- 有 10 个任务，每个任务有一个成本 `task_cost[k]`（内置数据 `[24, 10, 7, 2, 11, 16, 1, 13, 9, 27]`，注意 CP-SAT 只支持整数）。
- 有 3 个工人与 2 个组。
- 每个任务必须恰好分到一个组，每个工人也必须恰好分到一个组。
- 组的成本 = 该组内任务的成本之和；组的人均成本 = 组成本 / 组内工人数。

**输入**：任务成本列表、工人数、组数（均为代码内置数据）。

**要求**：决定任务与工人到组的分配方案，**最小化各组人均成本中的最大值**（即让最"累"的组的人均负担尽可能小），从而实现组间负载均衡。

## 建模思路

模型构建在 `tasks_and_workers_assignment_sat()` 函数中：

**决策变量**

- `x[i, j]`：布尔变量，工人 i 是否分配到组 j；
- `y[k, j]`：布尔变量，任务 k 是否分配到组 j；
- `n`（`num_workers_in_group[j]`）：组 j 的工人数，域 `[1, num_workers]`；
- `c`（`scaled_sum_of_costs_in_group[j]`）：组 j 的成本 × `scaling`（缩放后）；
- `a`（`averages[j]`）：组 j 的人均成本 × `scaling`；
- `obj`：各组人均成本最大值。

**约束条件**

1. **任务唯一分组**：对每个任务 k，`sum(y[k, j] for j in all_groups) == 1`；
2. **工人唯一分组**：对每个工人 i，`sum(x[i, j] for j in all_groups) == 1`；
3. **组工人数**：`n == sum(x[i, j])`（组 j 内工人数）；
4. **组成本**：`c == sum(y[k, j] * task_cost[k] * scaling)`——为了处理"除法/浮点平均"问题，把成本乘以缩放因子 `scaling = 1000` 全程保持整数运算；
5. **人均成本**：`add_division_equality(a, c, n)`——组的人均成本 = 组成本 / 组人数（CP-SAT 的整数除法约束）；
6. **全员分配**：`sum(num_workers_in_group) == num_workers`（冗余但保证所有工人被分配）。

**目标函数**

- `model.add_max_equality(obj, averages)`：`obj` = 各组人均成本（缩放后）的最大值；
- `model.minimize(obj)`：最小化该最大值（min-max 公平目标）。

## 运行方法

```bash
python3 tasks_and_workers_assignment_sat.py
```

代码中**没有定义任何 absl flags**。默认行为：求解内置实例（10 个任务、3 个工人、2 个组），求解器时间上限设为 2 小时（`max_time_in_seconds = 60*60*2`）；通过 `ObjectivePrinter` 回调打印每个中间解的序号、用时与目标值；若达到最优，按组打印组内工人、任务及成本、组成本总和与人均成本（除以 scaling 换算回真实值），最后打印求解器统计信息。

注意：源代码在模块加载时会直接调用一次 `tasks_and_workers_assignment_sat()`（第 123 行），随后 `main()` 中又调用一次；因此作为脚本运行时模型会被**构建并求解两次**，这是保留原始行为。

## 关键实现说明

- **代码结构**：
  - `ObjectivePrinter(cp_model.CpSolverSolutionCallback)`：解回调类，打印中间解的序号、时间与目标值；
  - `tasks_and_workers_assignment_sat()`：建模、求解并按组打印解；
  - `main()`：命令行入口。
- **关键 API**：
  - `model.new_bool_var(name)`：创建工人/任务的组分配布尔变量 `x[i, j]`、`y[k, j]`；
  - `model.new_int_var(lb, ub, name)`：创建组人数、组成本、人均成本、目标等整数变量；
  - `model.add(sum(...) == 1)`：唯一分配约束；
  - `model.add_division_equality(a, c, n)`：整除约束 `a == c / n`，用于人均成本；
  - `model.add_max_equality(obj, averages)`：最大值约束 `obj == max(averages)`（min-max 目标的核心）；
  - `model.minimize(obj)`：设定目标；
  - `solver.solve(model, objective_printer)`：带回调求解；`solver.response_stats()` 输出统计；`solver.boolean_value()` / `solver.value()` 读取解。
- **技术要点**：
  - CP-SAT 仅支持整数，通过 `scaling = 1000` 把"除法求平均"转化为整数除法，避免浮点；
  - 用 `add_max_equality` 把"最小化最大组人均成本"（公平性目标）表达为标准 min-max 优化。
