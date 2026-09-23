# golomb8（Golomb 尺问题，经典 CP 求解器版）

用 or-tools 经典 constraint_solver（`pywrapcp`）求解 8 刻度 Golomb 尺问题：刻度两两间距互不相同的前提下，最小化尺长。

## 问题描述

现实情景：Golomb 尺源于雷达与无线电通信中的干扰测量设计——希望在尽可能短的"尺子"上获得最多的两两不同距离。具体地：在一把尺子上放置 `size = 8` 个刻度，要求**任意两个刻度之间的距离（差值）两两互不相同**，目标是最小化尺子的长度（最外侧两刻度的间距）。

- 输入：无需输入，刻度数量 `size = 8` 硬编码；
- 要求：输出搜索过程中枚举到的所有解的尺长及统计信息。

## 建模思路

- 决策变量：`marks[i] = solver.IntVar(0, var_max, "marks_%d" % i)`（i = 0..7），第 i 个刻度的位置；`var_max = size * size = 64` 作为位置上界。
- 约束条件：
  1. `solver.Add(marks[0] == 0)`：第一个刻度固定在位置 0；
  2. `solver.Add(solver.AllDifferent(diffs))`：`diffs` 收集所有 `marks[j] - marks[i]`（i < j）共 28 个差值，要求两两互不相同——这是 Golomb 尺的核心约束；
  3. `solver.Add(marks[size - 1] - marks[size - 2] > marks[1] - marks[0])`：对称性破除，最大刻度间隔严格大于最小刻度间隔；
  4. `solver.Add(marks[i + 1] > marks[i])`：刻度位置严格递增。
- 目标函数：`objective = solver.Minimize(marks[size - 1], 1)`——以步长 1 逐步最小化尺长（最后一个刻度的位置）。

## 运行方法

```bash
python3 golomb8.py
```

本示例没有自定义 absl flags（`main` 也不校验多余参数）。默认行为：使用经典 CP 求解器，以 `solver.Phase(marks, solver.CHOOSE_FIRST_UNBOUND, solver.ASSIGN_MIN_VALUE)` 的搜索策略（优先选择第一个未绑定的变量并从小到大赋值）进行搜索；`AllSolutionCollector` 收集所有枚举到的解，并逐个打印 `Solution #i: value = 尺长, failures = 失败次数, branches = 分支数, time = 耗时 ms`，最后打印整次求解的总统计 `Total run : failures = ..., branches = ..., time = ... ms`。

## 关键实现说明

- 代码结构：单个函数 `main(_)`（经 `app.run` 启动），包含数据定义、约束构建、搜索与解收集。
- 关键 API（注意：本例使用**旧版** or-tools constraint_solver，而非 CP-SAT）：
  - `pywrapcp.Solver("golomb ruler")`：创建经典 CP 求解器；
  - `solver.IntVar(lb, ub, name)`：定义整数变量（刻度位置）；
  - `solver.Add(constraint)`：添加约束；
  - `solver.AllDifferent(diffs)`：全局两两互异约束；
  - `solver.Minimize(var, step)`：构造目标管理器（优化变量与优化步长）；
  - `solver.Assignment()` + `solution.Add(var)`：定义需要在解收集器中记录的变量；
  - `solver.AllSolutionCollector(solution)`：收集搜索过程中所有解的收集器；
  - `solver.Phase(vars, CHOOSE_FIRST_UNBOUND, ASSIGN_MIN_VALUE)`：决策构建器，指定变量选择与取值分支策略；
  - `solver.Solve(decision_builder, [objective, collector])`：在给定搜索策略与监听器下执行搜索；
  - `collector.SolutionCount()` / `collector.Value(i, var)` / `collector.WallTime(i)` / `collector.Branches(i)` / `collector.Failures(i)`：读取每个解的取值与统计；
  - `solver.WallTime()` / `solver.Branches()` / `solver.Failures()`：整次求解的统计。
- 相关示例：同一问题的 CP-SAT 版本见 `golomb_sat`（模型更简洁，参数可调）。
- 代码中保留的 `# pylint: disable=g-explicit-bool-comparison` 说明：该告警对 `solver.Add(x == 0)` 这类约束属于误报，故显式禁用。
