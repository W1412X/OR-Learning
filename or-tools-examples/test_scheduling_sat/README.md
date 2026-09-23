# test_scheduling_sat（测试调度/功率约束排程问题）

调度一组由操作员执行的测试，在电源功率上限约束下使总工期（makespan）最短。

## 问题描述

这是一个带资源（功率）约束的排程问题：

- 若干测试必须由操作员执行，每个测试有**时长**（`TestTime`）和**平均功率**（`AveragePower`）。
- 操作员从电源（power supply）取电，操作员与电源的对应关系是给定的（`Operator → Supply`）。
- 每个电源有最大功率输出（`MaxAllowedPower`）：任一时刻，该电源上正在运行的测试的功率之和不能超过其上限。

**输入**（代码内置的三张表，由 `build_data()` 用 pandas 读取）：
- 测试表：`Name`（名称）、`Operator`（操作员）、`TestTime`（时长）、`AveragePower`（平均功率）；
- 操作员表：`Operator`（操作员）→ `Supply`（所属电源）；
- 电源表：`Supply`（电源）→ `MaxAllowedPower`（最大功率）。

**要求**：确定每个测试的开始时间，使每个电源的瞬时功率始终不超上限，并**最小化总完工时间（makespan，最后一个测试的结束时间）**。

## 建模思路

模型构建在 `solve()` 函数中：

**决策变量**

- `start_{name}`：每个测试的开始时间，域 `[0, horizon - test_time]`（`horizon` = 所有测试时长之和，是一个安全的松弛上界）；
- `interval_{name}`：与开始时间绑定的**定长区间变量**（fixed-size interval）；
- `makespan`：总工期，域 `[0, horizon]`。

**约束条件**

1. **功率资源约束（累积约束）**：对每个电源 supply，`model.add_cumulative(intervals, demands, supply_to_max_power[supply])`——将该电源上所有测试的区间与其功率需求传入，要求任一时刻该电源上的瞬时功率之和不超过最大功率。
2. **makespan 下界**：对每个测试的结束时间 `start + test_time`，`model.add(makespan >= end)`。

**目标函数**

`model.minimize(makespan)`——最小化总完工时间。

## 运行方法

```bash
python3 test_scheduling_sat.py
```

代码中定义的全部 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--params` | `"num_search_workers:16,log_search_progress:true,max_time_in_seconds:45"` | CP-SAT 求解器参数（文本格式）：16 并行 worker、打印搜索日志、最长求解 45 秒。 |

默认行为：先用 pandas 构建并打印三张数据表（测试、操作员、电源），然后建模求解；若解为最优或可行，打印 `Makespan = ...` 以及每个测试的开始时间、时长、功率与所属电源。命令行传入多余参数会抛出 `app.UsageError`。

运行依赖：需要安装 `pandas`（`pip install pandas`）以及 `ortools`。

## 关键实现说明

- **代码结构**：
  - `build_data()：`用 `pd.read_table(io.StringIO(...))` 把内置的三段文本解析成三个 pandas DataFrame（测试、操作员、电源）；
  - `solve(tests_data, operator_data, supplies_data)`：解析数据、建模、求解并报告结果；
  - `main()`：打印数据表并调用 `solve`。
- **关键 API**：
  - `cp_model.CpModel()`：创建模型；
  - `model.new_int_var(0, horizon - test_time, f"start_{name}")`：创建测试开始时间变量；
  - `model.new_fixed_size_interval_var(start, test_time, f"interval_{name}")`：创建定长区间变量（时长固定），是调度问题的标准表达；
  - `model.add_cumulative(intervals, demands, capacity)`：累积资源约束，要求资源占用任一时刻不超过容量（本例容量为电源最大功率、需求为各测试功率）；
  - `model.add(makespan >= end)` 与 `model.minimize(makespan)`：最小化总工期；
  - `solver.parameters.parse_text_format(_PARAMS.value)`：按文本格式应用求解器参数。
- **技术要点**：
  - 通过"操作员→电源"映射把测试聚合到电源维度，每个电源一组 `add_cumulative`；
  - makespan 用一个整数变量加"≥ 所有结束时间"的约束建模，是调度问题最小化工期的惯用写法；
  - 该示例同时演示了 pandas 数据表与 CP-SAT 的衔接。
