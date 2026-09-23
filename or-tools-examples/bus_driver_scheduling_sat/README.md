# bus_driver_scheduling_sat

用 CP-SAT 求解公交司机排班问题：为每名司机构建独立的"班次路径"子网络，分两个阶段先最小化司机数、再最小化总工作时长。

## 问题描述

公交公司某一天有一批班次，每行数据为「班次编号、开始时间 hh:mm、结束时间 hh:mm、开始分钟数、结束分钟数、班次时长（分钟）」。要为每个班次安排恰好一名司机，一名司机一天可连续执行多个班次，且必须满足：

- 每位司机一天总驾驶时间 ≤ 540 分钟（9 小时）；
- 每位司机一天总工作时间 ≤ 720 分钟（12 小时）；
- 每位司机一天总工作时间 ≥ 390 分钟（6.5 小时，软约束）；
- 每驾驶 4 小时（240 分钟）后必须休息至少 30 分钟（班次间隔 ≥ 30 分钟即重置连续驾驶计时）；
- 首班前有 10 分钟准备时间（`setup_time`）、末班后有 15 分钟清扫时间（`cleanup_time`）；
- 相邻两个班次之间至少间隔 2 分钟（含上下客等待）。

代码内置 4 个算例（`--instance` 选择）：0=TINY（27 班次）、1=SMALL（50 班次）、2=MEDIUM（200 班次）、3=LARGE（1356 班次）。程序分两阶段运行：第一阶段求最少司机数；第二阶段用该司机数求"总工作时长"最短的排班并打印每名司机的班次序列。

## 建模思路

与流模型版本不同，这里为**每名司机**单独建立一套"源点 → 班次节点 → 汇点"的路径网络：

- **决策变量**：
  - `performed[d, s]`（`new_bool_var`）：司机 d 是否执行班次 s；
  - `total_driving[d, s]` / `no_break_driving[d, s]`（`new_int_var`）：司机 d 执行到班次 s 时的累计驾驶时间 / 自上次休息以来的连续驾驶时间；
  - 每名司机的 `start_times[d]`、`end_times[d]`、`driving_times[d]`、`working_times[d]`（`new_int_var`）；
  - `working_drivers[d]`：司机 d 是否出勤（仅最小化司机数模式）；
  - 弧变量 `source_lit`（源点→班次）、`sink_lit`（班次→汇点）、`lit`（班次→班次），以及加权目标的 `delay_literals`/`delay_weights`。
- **约束**：
  - 弧上条件转移（`only_enforce_if`）：源点弧设置司机开始时间 `start_times[d] == shift[3] - setup_time` 并初始化累计驾驶时间；班次间弧累加驾驶时间（间隔 ≥ 30 分钟时重置连续驾驶计时）；汇点弧设置结束时间 `end_times[d] == shift[4] + cleanup_time` 并填入 `driving_times[d]`；
  - 未执行班次：`total_driving`、`no_break_driving` 清零，并为该节点加自环弧（`~performed[d, s]` 同时入/出）；
  - 执行班次：给 `start_times[d]` 加上界、`end_times[d]` 加下界；
  - 工作时间：`working_times[d] == end_times[d] - start_times[d]`；出勤司机 ≥ 390 分钟；
  - 回路/流守恒：每名司机的源点、每个班次节点、汇点均 `add_exactly_one`（入度 = 出度 = 1）；
  - 覆盖约束：每个班次 `add_exactly_one(performed[d, s] for d)`，且全局入弧/出弧各恰好一条；
  - 对称性破除：`starting_shifts[0, 0] == 1` 等把前 3 个班次固定给前 3 名司机；最小化司机数时用 `add_implication(~working_drivers[d], ~working_drivers[d+1])` 把不出勤司机排到编号末尾；
  - 冗余约束（加速求解）：`LinearExpr.sum(driving_times) == total_driving_time`；固定司机数时 `sum(working_times) == 总驾驶时间 + 每人准备/清扫时间 + weighted_sum(delay_literals, delay_weights)`。
- **目标函数**（两阶段）：
  - 第一阶段（`minimize_drivers=True`）：`model.minimize(LinearExpr.sum(working_drivers))`，最小化出勤司机数；
  - 第二阶段（`minimize_drivers=False`）：`model.minimize(LinearExpr.weighted_sum(delay_literals, delay_weights))`，最小化班次间等待时间之和（总驾驶时间固定，等价于最小化总工作时长）。

## 运行方法

```bash
python3 bus_driver_scheduling_sat.py                    # 默认求解算例 0（TINY）
python3 bus_driver_scheduling_sat.py --instance=2       # 求解算例 2（MEDIUM）
```

absl flags 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `output_proto` | `""` | 若非空，把 CP-SAT 模型 proto 写入该文件（仅在第二阶段生效） |
| `params` | `num_search_workers:16,log_search_progress:true,max_time_in_seconds:30` | 传给 CP-SAT 求解器的参数（文本格式）：16 个搜索线程、输出搜索日志、限时 30 秒 |
| `instance` | `0` | 选择算例（0=TINY、1=SMALL、2=MEDIUM、3=LARGE，取值范围 0~3） |

## 关键实现说明

- 数据：`SAMPLE_SHIFTS_TINY`（27）、`SAMPLE_SHIFTS_SMALL`（50）、`SAMPLE_SHIFTS_MEDIUM`（200）、`SAMPLE_SHIFTS_LARGE`（1356）四张班次表，各带相同格式的列说明注释。
- `bus_driver_scheduling(minimize_drivers, max_num_drivers)`：核心函数，按 `minimize_drivers` 分两种目标建模并求解，返回模型目标值。
- `main(_)`：先调用 `bus_driver_scheduling(True, -1)` 求最少司机数，成功后再以该数为 `max_num_drivers` 调用一次求最短总工作时长。
- 关键 API：
  - `cp_model.CpModel` / `new_int_var` / `new_bool_var`：模型与变量创建；
  - `only_enforce_if`：弧上的条件状态转移；
  - `add_exactly_one`：每名司机的路径流守恒 + 全局班次覆盖；
  - `add_implication`：对称性破除（不出勤司机连续排在末尾）；
  - `cp_model.LinearExpr.sum` / `weighted_sum`：冗余约束与加权目标；
  - `solver.parameters.parse_text_format(_PARAMS.value)`：解析 `--params`；
  - `solver.solve(model)`、`solver.value(...)`、`solver.boolean_value(...)`：求解并还原每名司机的班次序列（用 `no_break_driving` 是否被重置来检测并打印 `**break**` 休息标记）。
- 未找到可行/最优解时返回 -1，main 跳过第二阶段。
