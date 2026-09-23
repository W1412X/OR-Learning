# 魔幻序列（Magic Sequence）问题

用经典 CP 求解器 `pywrapcp` 的 `Distribute`（计数/分配）全局约束构造"魔幻序列"：序列中数字 i 出现的次数恰好等于序列第 i 个位置的值。

## 问题描述

**魔幻序列**是一个著名的约束满足问题：给定长度 `size`，要构造一个序列 \(s_0, s_1, \dots, s_{size-1}\)，使得数字 i 在序列中出现的次数等于 \(s_i\)。例如当 size=4 时，序列 `(1, 0, 2, 1)` 是一个解：0 出现 1 次（s0=1），1 出现 2 次（s2=2），2 出现 0 次，3 出现 1 次。

- **输入**：序列长度 `size`（通过命令行第一个参数给定，默认 100）。
- **要求**：找出满足上述自指性质的一个序列（存在即打印，不做优化）。

## 建模思路

- **决策变量**：`all_vars = [solver.IntVar(0, size, "vars_%d" % i) for i in all_values]`，即 `size` 个取值范围 `[0, size]` 的整型变量，`all_vars[i]` 表示序列第 i 个位置的值。
- **核心约束（自指计数）**：`solver.Add(solver.Distribute(all_vars, all_values, all_vars))`——`Distribute(变量列表, 取值列表, 计数变量列表)` 是聚合的 count 约束，它要求"值 j 在 `all_vars` 中出现的次数 == `all_vars[j]`"。这正是魔幻序列的定义。
- **冗余但加速的约束**：`solver.Add(solver.Sum(all_vars) == size)`——所有值之和等于序列长度。该约束在数学上可由 Distribute 约束推出（各类出现次数之和必然等于元素总数），但显式加入可以显著加快搜索。
- **目标函数**：无（纯可行性问题，找到第一个可行解即停）。

## 运行方法

```bash
python3 magic_sequence_distribute.py 100
```

- 命令行第一个位置参数 `NUMBER`：序列长度 `size`；**未提供时默认为 100**（代码 `size = int(argv[1]) if len(argv) > 1 else 100`）。
- 本示例**没有定义任何 absl flags**（只用了 `absl.app` 解析命令行），传入的参数被当作位置参数读取。
- 运行后找到第一个解并打印全部变量取值。

## 关键实现说明

- **代码结构**：单函数 `main(argv)` 脚本，使用 `absl.app.run(main)` 启动。
- **关键 API**（均来自 `ortools.constraint_solver.pywrapcp`，即经典 CP 求解器）：
  - `pywrapcp.Solver("magic sequence")`：创建求解器实例。
  - `solver.IntVar(lb, ub, name)`：创建取值范围 `[lb, ub]` 的整型决策变量。
  - `solver.Distribute(vars, values, counts)`：全局计数约束——对每个 `values[j]`，其在 `vars` 中的出现次数必须等于 `counts[j]`（本例中 counts 也是 `all_vars`，形成自指）。
  - `solver.Sum(all_vars) == size`：求和约束。
  - `solver.NewSearch(solver.Phase(...))` / `solver.NextSolution()` / `solver.EndSearch()`：经典 CP 求解器的搜索控制三件套；`Phase` 指定决策序列（`CHOOSE_FIRST_UNBOUND`：总是选第一个未绑定的变量；`ASSIGN_MIN_VALUE`：优先尝试最小值），`NextSolution()` 迭代出下一个解（本例只取第一个）。
