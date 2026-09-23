# rcpsp_sat（基于 CP-SAT 的 RCPSP 项目调度求解器）

本示例使用 **CP-SAT 求解器**求解**资源受限项目调度问题（RCPSP, Resource-Constrained Project Scheduling Problem）**及其变体（RCPSP/max、资源投资问题 RIP、生产者-消费者水库资源），输入为 `rcpsp.proto` 格式文件。

## 问题描述

项目管理中的经典调度问题：一个项目由一组任务组成，任务之间存在先后依赖关系，每个任务执行时需要按一定数量占用若干种资源，而每种资源的容量有限；部分任务有多种执行模式（代码中称为 recipe，即"工期 + 各资源用量"的不同组合）。

- 输入：`rcpsp.proto` 格式的问题文件（`RcpspProblem`），包含任务列表（工期、recipes、successors、successor_delays）、资源列表（容量、是否可再生等）。PSPLIB（http://www.om-db.wi.tum.de/psplib/data.html）等标准测试集均可转换使用；问题介绍见 https://www.projectmanagement.ugent.be/research/project_scheduling/rcpsp 。
- 要求：为每个任务安排开始时间并选择执行模式，在满足先后关系与资源容量约束的前提下**最小化项目总工期（makespan）**；若是资源投资问题（RIP），则**最小化资源容量投资成本**。

## 建模思路

代码在 `solve_rcpsp()` 中构建 CP-SAT 模型：

- **决策变量**：
  - 每个活动任务的时间变量：`task_starts[t]`（`start_of_task_t`）、`task_ends[t]`（`end_of_task_t`）、`task_durations[t]`（`duration_of_task_t`，取值域为该任务所有 recipe 的工期集合）以及区间变量 `task_intervals[t]`（`task_interval_t`）。
  - 多模式任务：每个 recipe 一个布尔变量 `is_present_{t}_{r}`，并用 `model.add_exactly_one(literals)` 保证**恰好选择一种执行模式**。
  - 需求变量：`demand_{t}_{res}`（`task_to_resource_demands`），取值域为该任务各 recipe 对该资源的需求量，并通过 `only_enforce_if(literals[r])` 与所选模式联动。
  - makespan 变量（项目总工期），以及可选的 `interval_makespan` 区间（起点为 makespan，长度 `interval_makespan_size`，结束于 `horizon + 1`）。
- **能量表达式**：`task_resource_to_energy[(t, res)] = sum(literals[r] * duration_r * demand_r)`，即"所选模式 × 工期 × 需求"的总能耗。
- **约束条件**：
  - 先后约束：普通 RCPSP 为 `task_ends[t] <= task_starts[n]`（任务结束早于后继开始）；RCPSP/max 变体中延迟可为负，按模式对编码 `s1 + delay <= s2`（`only_enforce_if([p1, p2])`）；后继为 sink 时改为 `task_ends[t] <= makespan`。
  - 可再生资源约束：`model.add_cumulative(intervals, demands, c)`（累积约束，任一时刻总需求不超过容量 c）；若 `use_interval_makespan` 开启，则把 `interval_makespan` 以满容量 c 加入，帮助压缩 makespan。
  - RIP 变体：容量本身是变量 `capacity_of_{res}`，`add_cumulative(intervals, demands, capacity)`。
  - 水库（生产者-消费者）资源：`model.add_reservoir_constraint(starts, demands, min_capacity, max_capacity)`。
  - 不可再生资源：直接对总需求求和 `<= c`。
- **目标函数**：RIP 问题为最小化 `objective == sum(unit_cost * capacity)`（容量投资成本）；否则最小化 `makespan`。通过 `model.minimize(objective)` 设置。
- **哨兵任务**：source（任务 0）的开始/结束时间固定为 0；sink（最后一个任务）的开始时间即 makespan。

## 运行方法

```bash
python3 rcpsp_sat.py --input=<rcpsp问题文件>
```

本示例定义了 5 个 absl flags：

| 参数 | 类型/默认值 | 含义 |
| --- | --- | --- |
| `--input` | string，`""` | 要解析并求解的输入文件（rcpsp.proto 格式） |
| `--output_proto` | string，`""` | 将 CpModel proto 导出到的输出文件路径（为空则不导出） |
| `--params` | string，`""` | 传给 SAT 求解器的参数字符串（文本格式） |
| `--use_interval_makespan` | bool，`True` | 是否用区间（interval）方式编码 makespan |
| `--horizon` | int，`-1` | 强制指定时间跨度 horizon；`-1` 表示自动计算 |

horizon 的自动计算逻辑：优先取 `problem.deadline`（非 -1 时），否则取 `problem.horizon`；均无效时朴素估计为所有任务最大工期之和（RCPSP/max 再加上所有延迟的绝对值）。

## 关键实现说明

- `print_problem_statistics(problem)`：打印问题统计信息——任务数（去掉 2 个哨兵任务）、资源数、带备选资源/可变工期/带后继延迟的任务数量，并区分 RIP、RCPSP/max、consumer-producer 等问题类型。
- `solve_rcpsp(problem, proto_file, params, active_tasks, source, sink)`：建模与求解核心。只考虑 `{source} + {sink} + active_tasks` 中的任务。
  - `cp_model.CpModel()` 建模；`new_int_var` / `new_int_var_from_domain` / `new_interval_var` / `new_bool_var` 创建变量。
  - `add_exactly_one`（模式选择）、`only_enforce_if`（模式与工期/需求联动、条件先后约束）、`add_cumulative`（可再生资源/容量变量）、`add_reservoir_constraint`（水库资源）、`LinearExpr.sum`（不可再生资源求和）。
  - `model.export_to_file(proto_file)`：可选导出模型 proto。
  - `solver.parameters.parse_text_format(params)`：应用用户参数；当工作线程数在 [16, 24) 时禁用 `objective_lb_search` 子求解器、启用 `objective_shaving`；`push_all_tasks_toward_start = True`（实验性：利用 makespan 特性把任务推向开始）；`log_search_progress = True` 输出日志。
- `main(_)`：用 `rcpsp.RcpspParser().parse_file()` 解析输入文件，取 `active_tasks = set(range(1, last_task))`、`source = 0`、`sink = last_task` 后调用 `solve_rcpsp`。
