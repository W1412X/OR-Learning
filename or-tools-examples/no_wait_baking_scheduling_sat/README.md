# 面包店无等待烘焙调度

用 CP-SAT 对面包店一整天的烘焙任务做无等待作业车间调度：为每个订单安排各道工序的时间与占用的资源，最小化所有订单的逾期时间之和。

## 问题描述

一家面包店安排一整天的烘焙生产：

- **时间设定**：凌晨 4 点开工（`start_work = 4 * 60`），晚上 10 点打烊（`horizon = 22 * 60`）；时长以分钟计，时间从午夜 0 点起算。
- **食谱（Recipe）**：4 种食谱——可颂、苹果派、奶油面包卷、巧克力蛋糕。每种食谱是一串有序工序（`Task`），例如可颂：烘焙(15 分钟，固定) → 发酵(60~90 分钟，可变) → 烹饪(20 分钟，固定) → 展示(5~300 分钟，可变)。
- **资源（Resource）**：
  - 人/机器/空间统一建模为资源：`baker1`、`baker2`（容量 1，具备烘焙技能）、`decorator1`（容量 1，装饰）、`waiting_space`（容量 4，发酵）、`oven`（容量 4，烹饪）、`display_space`（容量 12，展示）。
  - 工人容量为 1；机器/空间容量 ≥ 1。技能效率（efficiency）当前未使用。
- **订单（Order）**：9 个订单（如 `croissant_7am` 早上 7 点交付 3 份可颂、`apple_pie_1pm` 下午 1 点交付 10 个苹果派等），每个订单指明食谱、交期 `due_date`（午夜后分钟数）与数量 `quantity`（每份数量展开为一个独立的"批次"作业）。
- **要求**：同一作业内工序**无等待**衔接（上一道工序一结束下一道立即开始，如面团出烤箱前发酵已就绪）；每道工序由具备对应技能的资源之一执行；最后一个展示工序必须在交期之后结束；目标是最小化所有作业的逾期时间（tardiness = 实际结束时间 − 交期）之和。

## 建模思路

- **决策变量**：
  - 每个作业（`订单_批次`）的第一道工序创建开始时间变量 `start = new_int_var(start_work, horizon, ...)`；
  - 每道工序的时长为整型变量 `size = new_int_var(task.min_duration, task.max_duration, ...)`（固定工序的上下界相同）；
  - 每道工序为每个**具备所需技能的资源**创建一份可选区间副本 `copy = new_optional_interval_var(start, size, end, presence, ...)`，`presence` 表示"该工序由该资源执行"；
  - 最后一道工序的结束时间写成 `end = tardiness + due_date`，`tardiness = new_int_var(0, horizon - due_date, ...)` 即逾期变量。
- **约束条件**：
  - **无等待衔接**：后一道工序的 `start` 直接取上一道工序的 `end` 变量（`start = previous_end`，共享同一变量，等价于 `Add(start == previous_end)`）；
  - **唯一资源指派**：`model.add_exactly_one(presence_literals)`——每道工序必须且只能由一份资源副本执行；
  - **资源能力**：对每个资源汇总其全部区间副本：容量为 1 的资源用 `model.add_no_overlap(intervals)`（互斥），容量 > 1 的用 `model.add_cumulative(intervals, [1]*n, capacity)`（容量累积约束）；
  - **交期约束**：展示工序结束后才允许 `tardiness >= 0` 的隐式保证（tardiness 非负且 end = tardiness + due_date ⟹ end ≥ due_date）。
- **目标函数**：`model.minimize(sum(tardiness_vars))`——最小化所有作业的逾期时间总和。

## 运行方法

```bash
python3 no_wait_baking_scheduling_sat.py
```

支持以下 absl flags：

| flag | 默认值 | 含义 |
|---|---|---|
| `--params` | `"num_search_workers:16, max_time_in_seconds:30"` | SAT 求解器参数（文本格式，经 `solver.parameters.parse_text_format` 解析）；本例设置 16 个搜索工作线程、30 秒时限。 |

- 代码中还强制开启 `solver.parameters.log_search_progress = True`（搜索日志）。
- 求解成功（OPTIMAL 或 FEASIBLE）后按订单批次打印每个事件（各工序的 start/end）发生的时刻（`时:分` 格式）。

## 关键实现说明

- **代码结构**：
  - 数据类：`Task`（单个烘焙任务，含 min/max 时长）、`Skill`（工人技能/机器能力，效率字段当前未用）、`Recipe`（有序工序序列，`add_task` 支持链式调用）、`Resource`（工人/机器/空间，`add_skill` 链式添加技能）、`Order`（唯一 ID + 食谱名 + 交期 + 数量）。
  - `set_up_data()`：构造 4 个食谱、6 个资源、9 个订单，返回 `(recipes, resources, orders)`。
  - `solve_with_cp_sat(recipes, resources, orders)`：构建优化模型并求解——展开订单为批次作业、创建区间与 presence 变量、添加无等待/唯一指派/资源能力约束、设置逾期最小化目标、求解并按订单打印各事件时刻。
  - `main(argv)`：组装数据并调用求解（`absl.app.run` 启动）。
- **关键 API**（`ortools.sat.python.cp_model`，即 CP-SAT）：
  - `model.new_int_var(lb, ub, name)`：整型变量（工序开始时间、时长、逾期）。
  - `model.new_bool_var(name)`：布尔变量（资源指派 presence）。
  - `model.new_optional_interval_var(start, size, end, presence, name)`：可选区间变量——presence 为假时该工序不被该资源执行，区间不参与冲突检查。
  - `model.add_exactly_one(literals)`：恰好一个为真（每道工序恰好指派给一份资源副本）。
  - `model.add_no_overlap(intervals)`：互斥约束（容量 1 的资源同一时刻只做一件事）。
  - `model.add_cumulative(intervals, demands, capacity)`：累积约束（容量 > 1 的资源，同一时刻并发占用不超过容量）。
  - `model.minimize(expr)`：设置最小化目标（逾期之和）。
  - `cp_model.CpSolver()`、`solver.parameters.parse_text_format(_PARAMS.value)`、`solver.solve(model)`：创建求解器、解析 flag 参数、求解。
  - `solver.value(var)`：读取解中变量值（打印各事件时刻）。
