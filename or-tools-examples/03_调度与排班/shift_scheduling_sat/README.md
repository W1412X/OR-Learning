# shift_scheduling_sat（员工轮班排班问题）

本示例使用 **CP-SAT 求解器**解决**员工轮班排班问题（Shift Scheduling）**：为多名员工安排数周内的班次，同时满足硬性规则并把软性规则的违反量作为罚分最小化。

## 问题描述

类似医院、工厂、客服中心的真实排班场景：

- 输入（均为代码内置数据）：
  - 8 名员工（`num_employees`）、3 周（`num_weeks`）、4 种班次 `shifts = ["O", "M", "A", "N"]`（休息 / 早班 / 中班 / 晚班）。
  - 固定排班 `fixed_assignments`：前 2 天部分员工的班次已指定。
  - 员工请求 `requests`：员工对某个（班次, 日期）组合的偏好，负权重表示"想要"，正权重表示"不想要"。
  - 连续班次约束 `shift_constraints`：如"休息必须连续 1~2 天（硬性）"、"夜班连续 2~3 天为宜，1 或 4 天可接受但要罚分"。
  - 每周总次数约束 `weekly_sum_constraints`：如"每周休息 1~3 天"、"每周至少 1 个夜班（违反罚分）、至多 4 个（硬性）"。
  - 班次转换惩罚 `penalized_transitions`：如"中班转夜班罚 4 分"、"夜班转早班禁止"。
  - 每日人力需求 `weekly_cover_demands`：周一到周日每天早/中/晚班所需人数。
  - 超额覆盖罚分 `excess_cover_penalties`：超出需求的人数按班次类型罚分。
- 要求：给每名员工每一天分配恰好一个班次，满足所有硬性约束，并**最小化总罚分**（软约束违反量与超额覆盖，同时把员工请求作为负罚分/奖励纳入目标）。

## 建模思路

- **决策变量**：`work[e, s, d]` —— 布尔变量 `work{e}_{s}_{d}`，表示员工 `e` 在第 `d` 天上班次 `s`。
- **约束条件**：
  - 每人每天恰好一个班次：`model.add_exactly_one(work[e, s, d] for s in range(num_shifts))`。
  - 固定排班：`model.add(work[e, s, d] == 1)`。
  - 连续序列约束（`add_soft_sequence_constraint`）：禁止长度 < `hard_min` 或 > `hard_max` 的连续段（硬约束），对长度 < `soft_min` 或 > `soft_max` 的连续段按超出量线性罚分。核心编码是 `negated_bounded_span`：把疑似连续段取反、并用左右相邻变量（不取反）包围，`add_bool_or` 之后恰好只禁止"该段全为真且两端为假"的孤立连续段。
  - 每周总次数约束（`add_soft_sum_constraint`）：`sum_var == sum(works)`，硬边界直接作为 `sum_var` 的取值域，软边界通过 `delta` / `excess` 变量和 `model.add_max_equality(excess, [delta, 0])` 生成线性罚分。
  - 班次转换约束：对相邻两天，`add_bool_or([~work[e, prev, d], ~work[e, next, d+1]])`；`cost == 0` 表示直接禁止，否则引入 `trans_var` 罚分变量。
  - 覆盖约束：每个工作班次、每天，统计出勤人数 `worked == sum(works)`（下界为最低需求），超出 `min_demand` 的部分记入 `excess` 变量并按 `excess_cover_penalties` 罚分。
- **目标函数**：`model.minimize(Σ obj_bool_vars[i] * obj_bool_coeffs[i] + Σ obj_int_vars[i] * obj_int_coeffs[i])`——所有布尔罚分（软序列、转换、请求的正负权重）与整数罚分（软求和、超额覆盖）的加权和最小。

## 运行方法

```bash
python3 shift_scheduling_sat.py
```

本示例定义了 2 个 absl flags：

| 参数 | 类型/默认值 | 含义 |
| --- | --- | --- |
| `--output_proto` | string，`""` | 将 cp_model proto 的文本形式写入该文件（为空则不写） |
| `--params` | string，`"max_time_in_seconds:10.0"` | 传给 SAT 求解器的参数（文本格式），默认限时 10 秒 |

默认行为：求解内置的 8 人 × 3 周排班实例；求解过程中通过 `ObjectiveSolutionPrinter` 打印每个改进解的目标值；结束后按周历（`M T W T F S S`）打印每名员工的班次序列，列出所有被违反的软约束（罚分）与被满足的请求（奖励），最后打印求解统计 `solver.response_stats()`。

## 关键实现说明

- `negated_bounded_span(works, start, length)`：构造"孤立连续段"的否定子句——段内变量取反，段外左右边界变量保持原样，是实现连续序列约束的关键技巧。
- `add_soft_sequence_constraint(...)`：连续序列的硬/软长度约束，返回 `(cost_literals, cost_coefficients)` 罚分项；过短序列直接 `add_bool_or` 禁止，接近软边界的序列引入罚分字面量，罚分与超出量成正比。
- `add_soft_sum_constraint(...)`：对"为真变量个数"的硬/软上下界约束，同样返回罚分项（`excess` 超额变量 + 线性系数）。
- `solve_shift_scheduling(params, output_proto)`：主函数——
  - 数据定义（员工数、周数、班次、固定排班、请求、各类约束参数、每日需求）。
  - 建模：`cp_model.CpModel()`，`new_bool_var` / `new_int_var` / `add_exactly_one` / `add_bool_or` / `add_max_equality` / `minimize` 等 API。
  - 可选导出 proto（`str(model)` 写文件）。
  - 求解：`solver.parameters.parse_text_format(params)` 应用参数；`cp_model.ObjectiveSolutionPrinter()` 作为回调展示搜索过程中的改进解。
  - 结果打印：`solver.boolean_value(...)` / `solver.value(...)` 读取解，按周历输出排班表与罚分明细。
- `main(_)`：absl 的 `app.run(main)` 入口，把 flag 值传给 `solve_shift_scheduling`。
