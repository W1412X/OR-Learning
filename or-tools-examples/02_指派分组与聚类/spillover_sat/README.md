# spillover_sat（Spillover：服务器采购溢出问题）

用 CP-SAT 近似求解"采购物理机以满足虚拟机（VM）需求"的成本最小化问题，同时保证达到目标服务水平。

## 问题描述

这是一个云数据中心容量规划问题：

- 有 M 种类型的物理机，第 j 类物理机单价为 c_j，且可购买数量有上限 l_j。
- 有 V 种类型的虚拟机（VM），第 i 类 VM 的总需求量为 d_i。
- 一台第 j 类物理机可以承载 n_ij 台第 i 类 VM（即 `vms_per_machine`），但每种 VM 只能由一个**按优先级排列的兼容物理机类型列表**（`compatible_machines`）来满足：需求到达时优先使用列表中靠前的机器类型，该类型机器用尽后"溢出（spillover）"到下一优先级类型；列表全部耗尽后，剩余需求无法满足。
- 各类 VM 的需求在时间区间 [0, 1] 上等间隔到达。

**输入**：每类机器的成本与数量上限、每种 VM 的兼容机器列表（含承载能力）与需求量、目标服务水平（如 95%）、时间离散步数。

**要求**：决定购买每类物理机的数量，使采购总成本最小，且被满足的需求总量不少于服务水平的比例（默认 95%）。

由于购买量与需求量都很大，可以用连续（分数）近似问题代替整数问题；本例展示了如何用没有连续变量的 CP-SAT 近似求解该连续松弛问题（若单独求解此类问题，直接用 LP 求解器即可；若要嵌入更大的模型（如两阶段问题）并附加约束，CP-SAT 才是合适的选择）。

## 建模思路

模型构建在 `_solve_spillover_problem` 中，对应代码中的注释块（下标 i 遍历 VM 需求，j 遍历机器类型）：

**决策变量**
- `s[j]`（s_j）：购买第 j 类机器的数量，域 `[0, machine_limit[j]]`。
- `w[j]`（w_j）：第 j 类机器被用光（耗尽）的时刻，域 `[0, T]`（永不耗尽则为 T）。
- `v[i][j]`（v_ij）：开始用第 j 类机器满足第 i 类 VM 需求的时刻，域 `[0, T]`。
- `o[i]`（o_i）：第 i 类 VM 需求开始无法满足（断供）的时刻，域 `[0, T]`。
- `m[i]`（m_i）：第 i 类 VM 被满足的需求总量，域 `[0, d_i]`。

其中 T 为时间离散步数 `time_horizon`。

**约束条件**
1. 服务水平约束：`sum(m) >= ceil(service_level * 总需求)`——被满足的需求至少占总需求的比例。
2. `T * m[i] <= o[i] * d[i]`——VM i 被满足的需求量与断供时刻线性相关（需求等间隔到达）。
3. `v[i][j] >= w[r]`（对每个更高优先级机器 r）——使用机器 j 满足需求 i 之前，所有更高优先级机器类型必须已经耗尽。
4. `v[i][j] <= w[j]`——机器 j 的耗尽时刻不早于开始将其用于需求 i 的时刻。
5. `o[i] == sum(w[j] - v[i][j])`——断供时刻等于用各兼容机器服务的时长之和。
6. 机器容量约束：对每类机器 j，`sum_i ceil(d_i/n_ij) * (w_j - v_ij) <= T * s_j`——机器 j 的总使用量不超过其供应量（当 d_i/n_ij 非整数时，ceil 引入近似误差）。

**目标函数**

最小化采购总成本：`obj = sum_j c_j * s[j]`，即 `model.minimize(obj)`。

## 运行方法

```bash
python3 spillover_sat.py
```

代码中定义的全部 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--machine_types` | `100` | 可用于满足需求的机器类型数量（M）。 |
| `--vm_types` | `500` | 需要供应的 VM 类型数量（V）。 |
| `--fungibility` | `10` | 每种 VM 可由多少种机器类型满足（随机均匀选取）。 |
| `--max_demand` | `100` | 每种 VM 的需求量在 `[max_demand//2, max_demand]` 内均匀随机。 |
| `--test_data` | `False` | 使用小型测试实例（最优目标值为 360）代替随机数据。 |
| `--seed` | `13` | 生成实例的随机数种子。 |
| `--time_steps` | `100` | 时间离散化的步数（T）。 |

默认行为：以 `--seed` 为种子生成随机实例（100 种机器、500 种 VM），打印实例数据后调用 CP-SAT 求解，输出最优目标值（成本）。求解器参数为 `num_workers=16`、`log_search_progress=True`、最长求解时间 30 秒，若未达到 OPTIMAL 则抛出 `RuntimeError`。

## 关键实现说明

- **数据结构**：三个 `@dataclasses.dataclass(frozen=True)`：
  - `MachineUse`：一种机器的用途（`machine_type` 机器类型、`vms_per_machine` 每台机器可承载的 VM 数）。
  - `VmDemand`：一种 VM 的需求（`compatible_machines` 兼容机器元组、`vm_quantity` 需求量）。
  - `SpilloverProblem`：完整问题实例（`machine_cost` 成本、`machine_limit` 上限、`vm_demands` 各 VM 需求、`service_level` 服务水平、`time_horizon` 时间离散步数）。
- **实例生成**：`_random_spillover_problem()` 用 `random` 模块生成随机实例；`_test_problem()` 返回手工构造的小实例（用于验证，最优值 360）。
- **模型构建**：`_solve_spillover_problem()` 中用 `cp_model.CpModel()` 建模，关键 API：
  - `model.new_int_var(lb, ub, name)`：创建整数决策变量（`s`、`w`、`o`、`m`、`v`）。
  - `model.add(...)`：添加线性约束（上述 6 组约束）。
  - `model.minimize(obj)`：设定最小化目标。
  - `cp_model.CpSolver().solve(model)`：求解；`solver.parameters.num_workers` / `log_search_progress` / `max_time_in_seconds` 配置并行数、日志与时间上限。
  - `solver.objective_value`：读取最优目标值。
- **技术要点**：将"先耗尽高优先级机器再溢出到下一级"的分配规则改写成时间维度上的不等式（约束 3、4、5），从而只用整数变量近似建模连续溢出过程。
