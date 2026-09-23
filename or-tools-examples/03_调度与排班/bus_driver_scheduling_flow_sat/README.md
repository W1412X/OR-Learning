# bus_driver_scheduling_flow_sat

用"流网络 + CP-SAT"求解公交司机排班问题：把每名司机一天的班次序列看成流网络中一条"源点 → 班次…→ 汇点"的路径，求完成全部班次所需的最少司机数。

## 问题描述

公交公司某一天有一批班次，每行数据为「班次编号、开始时间 hh:mm、结束时间 hh:mm、开始分钟数、结束分钟数、班次时长（分钟）」。要为每个班次安排恰好一名司机；一名司机一天内可以连续执行多个班次，但必须满足：

- 每位司机一天的总驾驶时间 ≤ 540 分钟（9 小时）；
- 每位司机一天的总工作时间 ≤ 720 分钟（12 小时）；
- 一天结束时总工作时间 ≥ 390 分钟（6.5 小时，软性最短工时）；
- 连续驾驶不超过 240 分钟（4 小时），之后必须休息至少 30 分钟（班次间隔 ≥ 30 分钟即视为"休息"、重置连续驾驶计时）；
- 相邻两个班次之间至少间隔 2 分钟（含上下客等待）；
- 两个班次间隔超过 180 分钟（3 小时）则视为不衔接（相当于换一名司机）；
- 司机一天从首个班次开始计起，起点状态以 `extra_time = 10 + 25` 计入首班前准备与收尾的附加时间。

代码内置三个算例：`--instance 1`（SMALL，50 个班次）、`--instance 2`（MEDIUM，200 个班次）、`--instance 3`（LARGE，1356 个班次）。输出为完成全部班次所需的最少司机数。

## 建模思路

把「一名司机一天的班次序列」建模为流网络中一条从源点（source）到汇点（sink）的路径，"最少司机数" = 最少路径数：

- **弧**：
  - 源点 → 班次 s（司机的一天从 s 开始，弧变量 `source_lit`）；
  - 班次 s → 班次 t（仅当间隔 `delay = t 开始时间 − s 结束时间` 满足 2 ≤ delay ≤ 180 时建弧，弧变量 `lit`；班次按开始时间排序，delay > 180 时直接 break）；
  - 班次 s → 汇点（司机在 s 之后结束一天，弧变量 `sink_lit`）。
- **节点状态变量**（每个班次 `s` 一组，均为 `NewIntVar`）：
  - `driving_time[s]`：到该班次为止的累计驾驶时间；
  - `working_time[s]`：到该班次为止的累计工作时间；
  - `no_break_driving_time[s]`：自上次休息以来的连续驾驶时间。
- **弧上转移**（条件等式 `model.Add(...).OnlyEnforceIf(弧变量)`）：
  - 源点→s：状态初始化（`working_time[s] == duration + extra_time` 等）；
  - s→t：`driving_time[t] == driving_time[s] + t 的时长`；`delay >= 30` 时 `no_break_driving_time[t]` 重置为 t 的时长，否则累加（上界 240）；`working_time[t] == working_time[s] + delay + t 的时长`；
  - s→汇点：`working_time[s] >= min_working_time`（390 分钟）。
- **流守恒**：每个班次节点 `sum(outgoing_literals[s]) == 1` 且 `sum(incoming_literals[s]) == 1`，即每班次恰好被一条"司机路径"经过。
- **司机数变量**：`num_drivers = NewIntVar(min_num_drivers, min_num_drivers * 3)`，并约束源点流出弧数 = 汇点流入弧数 = `num_drivers`；下界 `min_num_drivers = ceil(总驾驶时长 / 540)` 预计算。
- **目标函数**：`model.Minimize(num_drivers)`。

## 运行方法

```bash
python3 bus_driver_scheduling_flow_sat.py                # 默认求解算例 1（SMALL）
python3 bus_driver_scheduling_flow_sat.py --instance 2   # 求解算例 2（MEDIUM）
```

本文件使用 argparse（不是 absl flags）解析命令行参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--instance` | `1` | 算例编号（1、2、3 分别对应 SMALL/MEDIUM/LARGE 数据表） |
| `--output_proto_file` | `""` | 若非空，把 cp_model proto 写入该文件 |
| `--params` | `""` | 传给 CP-SAT 求解器的参数（文本格式），非空时经 `parse_text_format` 生效 |

## 关键实现说明

- 数据：`SAMPLE_SHIFTS_SMALL`（50 班次）、`SAMPLE_SHIFTS_MEDIUM`（200 班次）、`SAMPLE_SHIFTS_LARGE`（1356 班次）三张长表（以 `# yapf:disable` 保持紧凑格式）。
- `find_minimum_number_of_drivers(shifts, params)`：核心函数，构建流网络模型并求解：
  - `cp_model.CpModel` / `NewIntVar` / `NewBoolVar`：创建模型、节点状态变量与弧变量；
  - `model.Add(...).OnlyEnforceIf(lit)`：仅在对应弧被选中时生效的状态转移等式；
  - `model.Add(sum(...) == 1)`：流守恒约束与司机数关联约束；
  - `model.Minimize(num_drivers)`：目标函数；
  - `cp_model.CpSolver` + `solver.Solve(model)`：求解（默认开启 `log_search_progress = True`；文件中注释掉了 `num_search_workers`、`boolean_encoding_level`、`lns_focus_on_decision_variables` 等可选参数，取消注释即可启用）。
- `main(args)`：解析参数、按 `--instance` 选择数据并调用求解；文件末尾被注释的代码是"第二阶段"（固定司机数、最小化总工作时长）的入口，本示例默认不启用。
- 求解成功时打印 `minimal number of drivers = ...`；未找到可行/最优解时返回 -1。
