# golomb_sat（Golomb 尺问题，CP-SAT 版）

用 CP-SAT 求解 `order` 阶 Golomb 尺问题：在刻度两两间距互不相同的约束下，最小化尺子的总长度。

## 问题描述

现实情景：Golomb 尺源于雷达/无线电天线的干扰测量设计——原文描述为"以最小的空间最大化雷达干扰"。抽象后的问题是：在一把尺子上放置 `order` 个刻度，使得**任意两个刻度之间的距离两两互不相同**，并让尺子尽可能短（最小化最右刻度位置，即尺长）。参考：https://en.wikipedia.org/wiki/Golomb_ruler

- 输入：尺的阶数 `order`（刻度数量，默认 8），由 absl flag 指定；
- 要求：输出最优的刻度布置与所有间距。

## 建模思路

- 决策变量：
  - `marks = [model.new_int_var(0, var_max, f"marks_{i}") ...]`：第 i 个刻度的位置，上界 `var_max = order * order`；
  - `diff`（`model.new_int_var(0, var_max, f"diff [{j},{i}]")`）：每对刻度 (i, j)（i < j）的间距，用 `model.add(diff == marks[j] - marks[i])` 定义后收集进 `diffs`。
- 约束条件：
  1. 起点：`model.add(marks[0] == 0)`——第一个刻度固定在 0；
  2. 严格递增：`model.add(marks[i + 1] > marks[i])`（i 取 0..order-3）；
  3. 核心约束：`model.add_all_different(diffs)`——所有 `order*(order-1)/2` 个刻度间距两两互不相同；
  4. 对称性破除：当 `order > 2` 时，`model.add(marks[order - 1] - marks[order - 2] > marks[1] - marks[0])`——最大刻度间隔严格大于最小间隔，消除镜像对称解。
- 目标函数：`model.minimize(marks[order - 1])`，最小化尺长（最后一个刻度的位置）。

## 运行方法

```bash
python3 golomb_sat.py
```

代码中定义了两个 absl flags：

| flag | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `--order` | 整数 | `8` | 尺的阶数（刻度数量） |
| `--params` | 字符串 | `"num_search_workers:16,log_search_progress:true,max_time_in_seconds:45"` | CP-SAT 求解器参数，`键:值` 逗号分隔（16 个并行 worker、打印搜索日志、限时 45 秒） |

示例：

```bash
# 求 10 阶 Golomb 尺，使用 8 线程、限时 120 秒
python3 golomb_sat.py --order=10 --params="num_search_workers:8,max_time_in_seconds:120"
```

默认行为：先打印 `Golomb ruler(order=8)`；求解过程中 `ObjectiveSolutionPrinter` 会在每次目标值改进时打印当前解与边界；求解结束后（OPTIMAL/FEASIBLE）逐行打印 `mark[i]: 位置`、排序后的所有间距 `intervals: [...]`，最后打印 `solver.response_stats()` 统计。

## 关键实现说明

- 代码结构：flags 定义（模块级）+ 函数 `solve_golomb_ruler(order, params)`（建模、求解、打印）+ `main`（读取 flag 并调用）。
- 关键 API：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_int_var(lb, ub, name)`：定义刻度位置与间距变量；
  - `model.add(...)`：添加起点、递增、间距定义与对称性破除约束；
  - `model.add_all_different(diffs)`：全局互异约束（Golomb 尺的核心）；
  - `model.minimize(marks[order - 1])`：设置最小化目标；
  - `solver.parameters.parse_text_format(params)`：从 `键:值` 文本解析并应用求解器参数（对应 `--params` flag）；
  - `cp_model.ObjectiveSolutionPrinter()`：内置解回调，每次目标值改进时打印解；
  - `solver.solve(model, solution_printer)`：求解并挂载回调；
  - `solver.value(var)` / `solver.response_stats()`：读取解值与统计摘要。
- 与 `golomb8` 的关系：本文件是同一问题的 CP-SAT 实现（差异变量建模为显式 `IntVar`，参数可通过 flags 调整）；`golomb8` 则使用旧版 `pywrapcp` 经典求解器。
