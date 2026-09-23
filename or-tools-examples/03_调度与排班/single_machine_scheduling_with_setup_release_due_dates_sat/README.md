# single_machine_scheduling_with_setup_release_due_dates_sat（带换型时间、释放时间与交货期的单机调度）

本示例使用 **CP-SAT 求解器**求解一个复杂的**单机作业车间调度问题**：单台机器按顺序加工所有作业，作业之间存在与顺序相关的换型时间（setup times），并考虑释放时间（release dates）、交货期（due dates）与先后约束，目标是最小化总完工时间（makespan）。

## 问题描述

一台机器（如一台 CNC 机床、一条灌装线）要依次完成 15 个作业：

- 输入（代码内置数据）：
  - `job_durations`：每个作业的加工工期（15 个整数）。
  - `setup_times`：15×15（实际含哑节点为 16×15）的换型时间矩阵，`setup_times[i][j]` 表示从作业 `i` 切换到作业 `j` 所需的准备时间（与顺序有关；`setup_times[0][j]` 表示作业 `j` 作为首个作业时从机器初始状态开始的换型时间）。
  - `release_dates`：作业最早可开始时间（0 表示随时可开始）。
  - `due_dates`：作业最晚必须结束的时间（`-1` 表示无交货期要求）。
  - `precedences`：额外先后约束，如作业 0、1 必须在作业 2 之前完成。
- 要求：确定所有作业的加工顺序和开始时间，机器同一时刻只能加工一个作业，且换型时间必须完整插入相邻作业之间，在满足释放时间、交货期与先后约束的前提下**最小化 makespan（最后一个作业的结束时间）**。

## 建模思路

- **决策变量**：
  - 每个作业的时间变量：`start`（`s_{job_id}`）、`end`（`e_{job_id}`），取值域为 `[release_date, due_date]`（无交货期时上界取 `horizon`）；区间变量 `interval`（`i_{job_id}`）由 `new_interval_var(start, duration, end)` 创建。
  - 顺序（电路）弧上的布尔字面量：`"j follows i"` 表示作业 `j` 紧跟在作业 `i` 之后加工，以及哑节点的入弧/出弧字面量。
  - `makespan`：总完工时间。
- **约束条件**：
  - 机器不重叠：`model.add_no_overlap(intervals)`，保证任意两个作业的加工区间不重叠。
  - 换型时间电路约束：`model.add_circuit(arcs)` 把"加工顺序"编码为覆盖所有节点的哈密顿回路——节点 `i+1` 代表作业 `i`，虚拟节点 `0` 表示回路起点/终点：
    - 若 `start_lit` 为真（作业 `i` 是第一个作业），强制 `starts[i] == max(release_dates[i], setup_times[0][i])`；
    - 若弧 `"j follows i"` 被选中，则 `starts[j] >= ends[i] + setup_times[i + 1][j]`（通过 `only_enforce_if(lit)` 实现"字面量 ⇔ 实际相邻"的关联）；当 `release_dates[j] == 0` 时，由于最小化 makespan，可把该不等式强化为等式 `starts[j] == ends[i] + setup_times[i+1][j]`。
  - 显式先后约束：`model.add(ends[before] <= starts[after])`。
- **预处理**（`_PREPROCESS` 开启时）：对每个作业计算"最小进入换型时间" `min_incoming_setup`（所有可能前驱换型时间与释放时间的最小值），把它转移进工期（`job_durations[job_id] += min_incoming_setup`），同时把相应换型时间和释放时间减去该值——等价变换但能收紧模型。
- **目标函数**：`model.add_max_equality(makespan, ends)` 定义 makespan 为所有作业结束时间的最大值，再 `model.minimize(makespan)` 最小化总完工时间。horizon（时间上界）由贪心估计得出：所有工期之和加上每个作业的最大可能换型时间。

## 运行方法

```bash
python3 single_machine_scheduling_with_setup_release_due_dates_sat.py
```

本示例定义了 3 个 absl flags：

| 参数 | 类型/默认值 | 含义 |
| --- | --- | --- |
| `--output_proto` | string，`""` | 将 cp_model proto 的文本形式写入该文件（为空则不写） |
| `--params` | string，`"num_search_workers:16,log_search_progress:true,max_time_in_seconds:45"` | SAT 求解器参数（16 线程、输出日志、限时 45 秒） |
| `--preprocess_times` | bool，`True` | 是否预处理换型时间与工期（注意：代码中该 flag 的注册名写作 `"--preprocess_times"`，即名称本身带连字符） |

默认行为：打印贪心 horizon 与每个作业的释放时间/工期/交货期，构建模型并求解；求解过程中打印每个新解（`SolutionPrinter` 回调）和目标值下界的改进（`best_bound_callback`）；结束后打印每个作业的开始与结束时间。

## 关键实现说明

- `SolutionPrinter(cp_model.CpSolverSolutionCallback)`：中间解回调类，`on_solution_callback()` 在每个新解出现时打印解序号、耗时 `wall_time` 与目标值 `objective_value`。
- `single_machine_scheduling()`：主流程——
  - 数据定义（`job_durations`、`setup_times`、`due_dates`、`release_dates`、`precedences`）。
  - 预处理：把最小进入换型时间并入工期（见上）。
  - 建模：`cp_model.CpModel()`；`new_int_var` / `new_interval_var` / `new_bool_var` 创建变量；`add_no_overlap`（机器不重叠）；`add_circuit`（加工顺序电路，换型时间以约束形式挂接在弧上）；`only_enforce_if`（条件约束关联弧字面量）；`add_max_equality` + `minimize`（目标）。
  - 可选导出 proto（`str(model)` 写文件）。
  - 求解：`solver.parameters.parse_text_format(parameters)` 应用 `--params`；`solver.best_bound_callback` 打印下界改进；`solver.solve(model, solution_printer)` 求解；最后用 `solver.value(...)` 打印各作业起止时间。
- `main(argv)`：absl 的 `app.run(main)` 入口，校验命令行参数后调用 `single_machine_scheduling()`。
