# horse_jumping_show（马术场地障碍赛排期）

用 CP-SAT 为一场为期三天的马术场地障碍赛（Horse Jumping Show）安排 15 场比赛的时间与场地。

## 问题描述

日内瓦将在冬季举办一场为期三天的马术场地障碍赛。骑手们在赛前六个月提交参赛报名（骑手 + 马匹 + 参加的比赛），一场比赛可以报名多次（同一比赛用多匹马，或参加多场比赛）。

赛事组织方需要为每场比赛确定举办日期、场地和开始时间，并满足以下要求：

- 比赛之间不能在同一时段、同一场地重叠。
- 比赛开始时间要分散在全天各处（并且尽量不要太早）。
- 开始时间只能是整点或半点（如 9:30、10:00、10:30 等），即以 30 分钟为粒度。
- 比赛只能安排在白天有自然光的时段；唯一例外是带顶棚和照明的 Main Stage 场地。
- 初学者比赛（障碍高度 1.10m 及以下）安排在第一天；高级比赛（1.50m 及以上）安排在最后一天。

代码中的数据（`generate_horse_jumping_show_data`）为：3 天赛程、15 场比赛（高度 0.8m-1.6m，时长 60-240 分钟）、3 个场地——Main Stage（9AM-9PM，带顶棚照明）、Highlands（9AM-5PM）、Sawdust（9AM-5PM）。

- 输入：比赛列表（编号、障碍高度、时长）与场地列表（名称、开放时段）。
- 要求：输出每天每场比赛的场地与起止时间（形如 `Day 2: C_1.20m_Jumpers in Highlands from 10:00 to 12:00`）的完整赛程表。

## 建模思路

- 决策变量：
  - `competition_assignments[c, a, d]`：布尔变量（`competition_scheduled_...`），表示比赛 c 是否安排在场地 a、第 d 天举办。
  - `competition_start_times[c, a, d]`：整数变量（`start_time_...`），表示开始时间所在的时间槽编号，以 30 分钟为一格（`time_to_slot` 把分钟转换为槽号），下界/上界由场地的开放时段减去比赛时长决定。
  - `competition_intervals[c, a, d]`：可选定长区间变量（`task_...`），长度为 `time_to_slot(comp.duration)`，其存在性由布尔变量 `competition_assignments[c, a, d]` 控制（`new_optional_fixed_size_interval_var`）。
- 约束条件：
  - 每场比赛必须恰好安排一次：`model.add(np.sum(competition_assignments[c, :, :]) == 1)`。
  - 初学者比赛（`comp.height <= 1.10`）必须在第一天（day 0）举办。
  - 高级比赛（`comp.height >= 1.50`）必须在最后一天（day 2）举办。
  - 同一场地、同一天的比赛不能重叠：`model.add_no_overlap(competition_intervals[:, a, day])`。
  - 同一场地、同一天各比赛的开始时间两两不同（错开比赛）：`model.add_all_different(competition_start_times[:, a, day])`。
- 目标函数：`model.maximize(np.sum(competition_start_times))`——最大化所有比赛开始时间槽之和，即让比赛尽量安排在一天中较晚的时段（满足"不要太早"的偏好）。

## 运行方法

```bash
python3 horse_jumping_show.py
```

本示例没有定义任何 absl flags，默认行为是：求解内置数据（3 天、15 场比赛、3 个场地），并打印按日期与开始时间排序的完整赛程表。求解器参数在代码中写死：`max_time_in_seconds = 30.0`（限时 30 秒）、`log_search_progress = True`（打印搜索日志）、`num_workers = 16`（16 个并行 worker）。若无可行解则打印 `Problem is infeasible.` 或 `No solution found.` 并返回空列表。

## 关键实现说明

- 代码结构：
  - 数据类（`@dataclasses.dataclass(frozen=True)`）：`Arena`（场地：名称与开放时段字符串）、`Competition`（比赛：编号、高度、时长）、`HorseJumpingShowData`（全部输入数据）、`ScheduledCompetition`（一条赛程结果：比赛、天、场地、起止时间）。
  - `generate_horse_jumping_show_data()`：构造内置的比赛与场地数据。
  - `solve()`：核心函数，完成建模、求解并返回 `ScheduledCompetition` 列表。
  - 内部辅助函数：`parse_time(t_str)` 把 "9AM"/"5PM" 解析成分钟数；`time_to_slot` / `slot_to_time` 在分钟与 30 分钟时间槽之间换算。
  - `main`：调用 `solve()`。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：建模与求解；`solver.solve(model)` 返回状态（`OPTIMAL` / `FEASIBLE` / `INFEASIBLE` 等）。
  - `model.new_bool_var(...)`：创建比赛-场地-天分配布尔变量。
  - `model.new_int_var(lb, ub, name)`：创建开始时间槽变量。
  - `model.new_optional_fixed_size_interval_var(start, size, presence, name)`：创建可选定长区间，未选中（presence 为假）时不占用资源——配合 `add_no_overlap` 实现条件化占用。
  - `model.add_no_overlap(...)`：同场地同天互斥（互不重叠）。
  - `model.add_all_different(...)`：同场地同天开始时间错开。
  - `model.maximize(...)`：以开始时间之和为目标做最大化。
  - `solver.value(var)` / `solver.boolean_value(var)`：读取解中变量的取值，用于还原赛程表。
  - `numpy` 多维数组（`np.empty(..., dtype=object)`）用于按 (比赛, 场地, 天) 三维组织变量，`np.sum` 便于写"恰好安排一次"约束。
