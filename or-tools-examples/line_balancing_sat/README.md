# line_balancing_sat（单装配线平衡问题 SALBP）

读取 .alb 格式的装配线平衡算例文件，先用贪心启发式求初始解，再用 CP-SAT（布尔模型或调度模型）精确求解，最小化工位（pod）数量。

## 问题描述

简单装配线平衡问题（SALBP，Simple Assembly Line Balancing Problem）是装配线平衡研究中的基础优化问题（参见 https://assembly-line-balancing.de/salbp/）：给定一组任务，每个任务有确定性的作业时间；任务之间由先后关系（precedence relations）部分排序，构成一张先后关系图。

目标是把所有任务分配到流水线上的若干个连续"工位"（代码中称为 pod，即 SALBP 中的工作站 station）上，要求：

- 每个任务恰好分配到一个工位；
- 同一工位内所有任务的作业时间之和不超过节拍时间（cycle time）；
- 满足任务的先后关系（前序任务所在工位不能晚于后序任务）；
- 最小化使用的工位数量。

- 输入：`.alb` 格式文件（格式说明见 https://assembly-line-balancing.de/wp-content/uploads/2017/01/format-ALB.pdf），包含任务数、任务时间、先后关系、节拍时间等分节信息，由 `read_problem` 解析。
- 要求：输出使用工位最少的任务分配方案。

## 建模思路

代码先用 `solve_problem_greedily` 计算一个贪心解（作为搜索提示与工位数上界），再按 `--model` flag 选择两种精确建模之一：

1. 布尔模型（`solve_problem_with_boolean_model`，默认）：
   - 决策变量：`assign[t, p]`（布尔，任务 t 是否安排在工位 p）、`possible[t, p]`（布尔，任务 t 是否可能安排在工位 p 或更晚的工位）、`active[p]`（布尔，工位 p 是否被使用）。
   - 约束条件：
     - 每个任务恰好安排到一个工位：`model.add_exactly_one([assign[t, p] for p in all_pods])`。
     - 每个工位的任务总时长不超过节拍时间：`model.add(sum(assign[t, p] * durations[t] for t in all_tasks) <= cycle_time)`。
     - `possible` 的单调性：`possible[t, p] -> possible[t, p+1]`（`add_implication`）。
     - `possible` 与 `assign` 的联动：`assign[t, p] -> possible[t, p]`，且 `p > 1` 时 `assign[t, p] -> ~possible[t, p-1]`。
     - 先后关系：对每个 `(before, after)` 与工位 p，`assign[before, p] -> ~possible[after, p-1]`（后序任务必须安排在更晚的工位）。
     - `active` 与 `assign` 的联动：`assign[t, p] -> active[p]`，且 `model.add_bool_or(all_assign_vars + [~active[p]])`。
     - 工位连续使用：`~active[p-1] -> ~active[p]`（未激活的工位之后不能再用），这对获得好的目标下界至关重要。
   - 目标函数：`model.minimize(sum(active))`——最小化使用的工位数量。
   - 搜索提示：用 `model.add_hint(assign[t, hint[t]], 1)` 注入贪心解。

2. 调度模型（`solve_problem_with_scheduling_model`）：
   - 决策变量：`pods[t]`（整数，任务 t 所在的工位编号）；把每个任务建模为"起点 = pods[t]、固定长度 1"的区间变量；另建一个终止区间 `obj_interval`（起点 `obj_var`、长度 `obj_size`、终点 `num_pods + 1`、需求 `cycle_time`）作为目标。
   - 约束条件：
     - 累积约束：`model.add_cumulative(intervals, demands, cycle_time)`——任意时刻（工位）上的总需求不超过节拍时间，等效于"每个工位任务总时长 ≤ cycle_time"。
     - 先后关系：`model.add(pods[after] >= pods[before])`。
   - 目标函数：`model.minimize(obj_var)`——最小化终止区间的起点（即实际使用的工位数）。
   - 搜索提示：`model.add_hint(pods[t], hint[t])` 注入贪心解。

## 运行方法

```bash
python3 line_balancing_sat.py --input=<算例文件.alb> [--model=boolean|scheduling|greedy] [--params=...] [--output_proto=...]
```

代码中定义了以下 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--input` | `""`（空） | 要解析并求解的输入文件（.alb 格式）。 |
| `--params` | `""`（空） | SAT 求解器参数（文本格式，传给 `solver.parameters.parse_text_format`）。 |
| `--output_proto` | `""`（空） | 将 CP-SAT 模型 proto 写入指定的输出文件；为空则不写出。 |
| `--model` | `boolean` | 使用的模型：`boolean`、`scheduling` 或 `greedy`。 |

默认行为：读取 `--input` 指定的 .alb 文件（无输入文件时会报错退出），打印问题统计信息（`print_stats`），然后运行贪心启发式得到初始解（打印 `Solving using a Greedy heuristics` 与 `greedy solution uses N pods.`），最后用布尔模型（默认）精确求解，运行时打印 CP-SAT 搜索日志（`log_search_progress = True`）。若命令行传入多余的位置参数会抛出 `app.UsageError`。

## 关键实现说明

- 代码结构：
  - `SectionInfo`：保存 .alb 文件每个分节（section）的信息——单个值 `value`、键值映射 `index_map`（任务时间等）或成对关系集合 `set_of_pairs`（先后关系）。
  - `read_problem(filename)`：逐行用正则解析 .alb 文件（`<节名>`、单个数字、两个数字的键值对、逗号分隔的先后关系对），返回 `Dict[str, SectionInfo]`。
  - `print_stats(problem)`：打印问题各节内容。
  - `solve_problem_greedily(problem)`：贪心启发式——按拓扑顺序维护候选任务集，每次从候选中挑选"放入当前工位后剩余容量最小（且不超载）"的任务，装满则开新工位，返回任务到工位的映射。
  - `solve_problem_with_boolean_model(problem, hint)`：布尔模型建模与求解。
  - `solve_problem_with_scheduling_model(problem, hint)`：累积（cumulative）调度模型建模与求解。
  - `main(argv)`：解析输入、打印统计、求贪心解，并按 `--model` flag 分发到对应求解函数。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：建模与求解；`solver.parameters.parse_text_format(_PARAMS.value)` 解析求解器参数；`solver.parameters.log_search_progress = True` 打印搜索日志。
  - `model.new_bool_var(name)` / `model.new_int_var(lb, ub, name)`：创建布尔/整数变量。
  - `model.add_exactly_one([...])`：每个任务恰好分配一个工位。
  - `model.add_implication(a, b)`：布尔蕴含（possible 单调性、先后关系、工位连续性等）。
  - `model.add_bool_or([...])`：active 与 assign 的联动约束。
  - `model.new_fixed_size_interval_var(start, size, name)` / `model.new_interval_var(start, size, end, name)`：把"任务所在工位"建模为区间变量（起点 = 工位编号）。
  - `model.add_cumulative(intervals, demands, capacity)`：累积资源约束，实现"每工位总时长 ≤ 节拍时间"。
  - `model.add_hint(var, value)`：注入贪心解作为搜索提示，加速精确求解。
  - `model.export_to_file(_OUTPUT_PROTO.value)`：按需导出模型 proto 文件。
  - `collections`、`re`、`typing.Dict` 等标准库用于数据解析与组织。
