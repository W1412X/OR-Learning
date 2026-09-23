# 内存布局与不可行性解释

求解内存分配（2D 装箱/排布）问题；当所有需求无法同时放下时，用三种建模技巧找出导致不可行的最小任务集合。

## 问题描述

一个**内存缓冲区分配**问题（芯片设计/内存规划场景）：

- 内存总容量 `CAPACITY = 98304`（缓冲区高度，y 方向）。
- 有 7 个任务（`DEMANDS`），每个任务形如 `[start, end, demand, alignment]`：
  - `start`/`end`：任务占用内存的**时间窗口**（x 方向，固定区间）；
  - `demand`：任务需要的缓冲区大小（y 方向长度）；
  - `alignment`（对齐要求）：在本例建模中未使用。
- **要求**：为每个任务在 y 方向（缓冲区位置）选择一个起点，使同一时间窗口内的任务在内存中互不重叠（即任何时刻被占用的内存总量不超过容量，且同时间的任务不重叠）。
- 本例的输入数据实际上**放不下全部 7 个任务**，因此示例演示了三步走：
  1. 硬模型：所有任务都必须放置 → 判定不可行；
  2. 假设（assumptions）软模型：找出"足以解释不可行"的任务子集；
  3. 最大化软模型：最大化能放置的任务数，找出放不下的任务及其可行摆放。

## 建模思路

三个模型共用同一套 2D 区间结构（时间 x 内存）：

- **决策变量**：
  - x 方向：任务 i 的时间区间 `x_interval = new_fixed_size_interval_var(start, end - start + 1, ...)`（固定起点、固定长度，硬模型）；软模型中为可选区间（`new_optional_fixed_size_interval_var`，由布尔变量 `presence` 控制是否占用）。
  - y 方向：整型变量 `y_start = new_int_var(0, CAPACITY - demand, ...)` 表示任务缓冲区在内存中的起点；`y_interval = new_fixed_size_interval_var(y_start, demand, ...)` 是起点可动、长度为 demand 的区间。
- **约束条件**：`model.add_no_overlap_2d(x_intervals, y_intervals)`——2D 无重叠约束：任何两个任务的 (时间, 内存) 矩形不得重叠，等价于"同一时间不共享内存"。
- **三个模型的目标/机制差异**：
  1. `solve_hard_model`：所有任务强制存在（无目标，纯可行性）→ 本例返回 INFEASIBLE；
  2. `solve_soft_model_with_assumptions`：每个任务对应布尔变量 `presence`（可选区间），并用 `model.add_assumptions(presences)` 把全部 presence 声明为假设；求解为 INFEASIBLE 时，调用 `solver.sufficient_assumptions_for_infeasibility()` 得到足以解释不可行的最小假设集合；
  3. `solve_soft_model_with_maximization`：`model.maximize(sum(presences))` 最大化成功放置的任务数；未放置（presence 为假）的任务即放不下的任务，已放置的打印其缓冲区起点。
- **无目标函数**（模型 1、2）；模型 3 的目标为最大化已放置任务数。

## 运行方法

```bash
python3 memory_layout_and_infeasibility_sat.py
```

支持以下 absl flags：

| flag | 默认值 | 含义 |
|---|---|---|
| `--output_proto` | `""`（空） | 输出文件路径；非空时把硬模型的 cp_model proto 写入该文件。默认不导出。 |
| `--params` | `"num_workers:1,linearization_level:2"` | SAT 求解器参数（文本格式）；本例设置单工作线程、线性化级别 2。 |

- 默认执行流程：先跑硬模型；若不可行（返回 False），再依次跑假设软模型与最大化软模型。

## 关键实现说明

- **代码结构**（三个独立建模/求解函数 + 调度入口）：
  - `solve_hard_model(output_proto, params) -> bool`：硬模型（任务全部强制存在），返回是否可行（`status != cp_model.INFEASIBLE`）；可行时打印各任务缓冲区起点，并打印 `solver.response_stats()` 统计。
  - `solve_soft_model_with_assumptions()`：假设软模型，利用 `solver.sufficient_assumptions_for_infeasibility()` 输出"使用哪些任务即足以解释不可行"。
  - `solve_soft_model_with_maximization(params)`：最大化软模型，输出每个任务是"放不下"还是"缓冲区起点在哪"。
  - `main(argv)`：先硬模型，不可行才触发两个软模型（`absl.app.run` 启动）。
- **关键 API**（`ortools.sat.python.cp_model`，即 CP-SAT）：
  - `model.new_fixed_size_interval_var(start, size, name)`：创建固定起点、固定长度的区间变量（时间维）。
  - `model.new_optional_fixed_size_interval_var(start, size, presence, name)`：可选区间变量，`presence` 为假时该区间不参与约束（软任务）。
  - `model.new_int_var(lb, ub, name)`：创建整型变量（缓冲区起点 `y_start`）。
  - `model.add_no_overlap_2d(x_intervals, y_intervals)`：2D 无重叠约束（时间×内存两维都不能重叠）。
  - `model.add_assumptions(literals)`：声明假设文字；不可行时配合 `solver.sufficient_assumptions_for_infeasibility()` 做不可行性解释（MUS 风格分析）。
  - `model.maximize(expr)`：设置最大化目标。
  - `solver.solve(model)`、`cp_model.INFEASIBLE/FEASIBLE/OPTIMAL`：求解与状态判断；`solver.value(var)`、`solver.boolean_value(var)` 读取解。
