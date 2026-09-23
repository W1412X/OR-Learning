# car_sequencing_optimization_sat

用 CP-SAT 求解带优化的汽车排序问题：确定装配线上的生产顺序，在满足各种选装件"滑动窗口"产能约束的前提下，使所需虚拟（填充）汽车最少。

## 问题描述

汽车装配线上要按顺序生产一批汽车。共有 7 个类别（`class_options` 的每一行给出该类别需要哪些选装件）：类别 0 是不带任何选装件的虚拟（填充）汽车，类别 1~6 是真实汽车；每种真实类别必须生产 `demands` 中给定的数量（本例各 5 辆，共 30 辆真实汽车）。

装配线每种选装件有一个专属工位，产能由滑动窗口规则限制（`capacity_constraints` 中的 `(max_cars, subsequence_len)`）：任意连续 `subsequence_len` 个槽位中，装有该选装件的汽车至多 `max_cars` 辆（如选装件 1 为"连续 3 辆中至多 1 辆"）。

当某些选装件需求密集而产能又紧时，30 辆真实汽车可能无法直接连续排开，此时需要插入不带选装件、不占工位产能的虚拟汽车作为间隔。要求：给出一个满足全部需求与产能规则的生产序列，使虚拟汽车数量最少（等价于总排程长度 `makespan` 最短）。

## 建模思路

- **决策变量**：
  - `produces[(c, s)]`（`new_bool_var`）：槽位 s 是否生产类别 c 的汽车（c 含虚拟类别 0，s 共 `num_real_cars + max_dummy_cars = 50` 个）；
  - `makespan`（`new_int_var(num_real_cars, num_slots)`）：有效排程长度，即首个虚拟汽车出现的槽位号（其后全为虚拟汽车）。
- **约束**：
  - 约束 1（每槽位一辆）：每个槽位 `add_exactly_one` 该槽位的全部 `produces[(c, s)]`；
  - 约束 2（需求）：每种真实类别在所有槽位中出现次数 `== demands[i]`（5）；
  - 约束 3（滑动窗口产能）：对每种选装件 `(max_cars, subsequence_len)`，枚举所有连续子窗口，把需要该选装件的类别在窗口内槽位的 `produces` 求和并限制 `<= max_cars`；
  - 约束 4（makespan 与虚拟汽车联动）：对每个槽位 s 引入 `makespan_le_s`，用两条 `only_enforce_if` 约束强制 `makespan_le_s <=> (makespan <= s)`，再用 `add_implication(makespan_le_s, produces[dummy_class, s])` 保证"makespan ≤ s 则槽位 s 必为虚拟汽车"。
- **目标函数**：`model.minimize(makespan)`——最短总排程，等价于使用最少的虚拟汽车。

## 运行方法

```bash
python3 car_sequencing_optimization_sat.py
```

本示例没有定义任何 absl flags：使用代码内置数据（30 辆真实汽车、最多 20 辆虚拟汽车、7 个类别、5 种选装件）直接求解。求解器限时 30 秒（`max_time_in_seconds = 30.0`），单线程（`num_search_workers = 1`）。输出最优/可行解的 makespan、所需虚拟汽车数、完整生产序列表格（类别 0 为虚拟汽车）以及求解器统计信息。

## 关键实现说明

- `solve_car_sequencing_optimization()`：唯一的主函数，按「数据 → 建模 → 变量 → 约束 → 目标 → 求解打印」六个编号小节组织。
- 关键 API：
  - `cp_model.CpModel` / `new_bool_var` / `new_int_var`：模型与变量创建；
  - `add_exactly_one`：每槽位恰好一辆车的约束；
  - `only_enforce_if`：实现 `makespan_le_s <=> (makespan <= s)` 的双向逻辑等价；
  - `add_implication`：`makespan_le_s => produces[dummy_class, s]` 的蕴含；
  - `model.minimize(makespan)` / `cp_model.CpSolver` / `solver.Solve(model)`：目标与求解；
  - `solver.Value(...)`：读取变量取值还原序列；`solver.response_stats()`：打印统计。
- 顶部模块 docstring 完整描述了问题背景与 CP-SAT 建模思路（决策变量、约束、目标三部分）。
- 无解时打印 `No solution found.`，其他异常状态打印求解器状态码。
