# cover_rectangle_sat（矩形覆盖问题）

用 CP-SAT 求出恰好铺满一个 60×50 矩形所需的最少不重叠正方形数量。

## 问题描述

现实情景：切割下料 / 铺砖问题。给定一块 60×50 的矩形板材（`size_x = 60`，`size_y = 50`），要求用若干个正方形把它完全覆盖：正方形边长不限（可各不相同）、两两不重叠、且必须完整落在矩形内。问题问的是：最少需要多少个正方形？

- 输入：矩形尺寸 60×50（硬编码在代码中）；
- 要求：找到能恰好覆盖矩形的最少正方形数量，并打印覆盖方案。

## 建模思路

本模型是一个**可行性问题**：对给定数量的正方形，判断是否存在一种摆法能恰好铺满矩形；外层由 `main` 从 1 个正方形开始逐一尝试，第一个可行解即为最少数量。

- 决策变量（每个正方形 i 一组）：
  - `size = model.new_int_var(1, size_y, "size_%i")`：正方形边长（正方形，x/y 方向等宽）；
  - `start_x`/`end_x`（0..60）与 `start_y`/`end_y`（0..50）：在 x、y 方向上的起点与终点坐标；
  - `interval_x = model.new_interval_var(start_x, size, end_x, ...)`、`interval_y` 同理：用二维区间对表示这个正方形；
  - `area = model.new_int_var(1, size_y * size_y, "area_%i")`，并用 `model.add_multiplication_equality(area, [size, size])` 强制面积等于边长的平方。
- 约束条件：
  1. 主约束 `model.add_no_overlap_2d(x_intervals, y_intervals)`：所有正方形两两不重叠；
  2. 冗余约束 `model.add_cumulative(x_intervals, sizes, size_y)` 与 `model.add_cumulative(y_intervals, sizes, size_x)`：任意一条竖直/水平线上的总占用不超过矩形对应边长，用于传播加速；
  3. 恰好覆盖：`model.add(sum(areas) == size_x * size_y)`——所有正方形面积之和等于 3000；配合"不重叠 + 在矩形内"即可推出"完全覆盖"；
  4. 对称性破除 1：边长按非降序排列 `model.add(sizes[i] <= sizes[i + 1])`；同时定义布尔变量 `same`（`sizes[i] == sizes[i+1]` 时为真），并在边长相等时进一步按 x 起点 `x_starts[i] <= x_starts[i+1]` 打破平局（`only_enforce_if` 条件约束）；
  5. 对称性破除 2：第一个正方形的起点限制在"四分之一象限"内：`model.add(x_starts[0] < (size_x + 1) // 2)`、`model.add(y_starts[0] < (size_y + 1) // 2)`。
- 目标函数：无显式目标（可行性判定）；求解器参数 `max_time_in_seconds = 10.0` 限制每个子问题 10 秒。

## 运行方法

```bash
python3 cover_rectangle_sat.py
```

本示例没有自定义 absl flags。`main` 中若传入多余的命令行参数会抛出 `Too many command-line arguments` 错误。

默认行为：`main` 令 `num_squares` 从 1 循环到 14，逐个调用 `cover_rectangle(num_squares)` 尝试覆盖；每个子问题设置 `num_workers = 8`（8 个并行 worker）、`max_time_in_seconds = 10.0`。一旦某个数量找到了可行覆盖，就打印 `%s found in %0.2fs`（状态名与耗时）、按行打印整个覆盖图（60×50 个字符，每个正方形用 `0`-`9`/`a`-`d` 的单个十六进制字符标记，若图形重叠会打印 ERROR），然后停止。

## 关键实现说明

- 代码结构：函数 `cover_rectangle(num_squares) -> bool`（对固定数量建模、求解、打印，返回是否找到解）+ `main`（从 1 到 14 递增尝试直到成功）。
- 关键 API：
  - `model.new_int_var(lb, ub, name)`：定义边长、坐标、面积等整数变量；
  - `model.new_interval_var(start, size, end, name)`：构造一维区间，两个方向区间合起来表示一个正方形；
  - `model.add_no_overlap_2d(x_intervals, y_intervals)`：二维互斥，保证正方形不重叠；
  - `model.add_cumulative(intervals, demands, capacity)`：一维容量约束，此处作为冗余约束加速传播；
  - `model.add_multiplication_equality(area, [size, size])`：表达面积 = 边长²；
  - `constraint.only_enforce_if(literal)`：条件约束（边长相同时才要求起点有序）；
  - `solver.parameters.num_workers` / `solver.parameters.max_time_in_seconds`：并行度与时间上限；
  - `solver.status_name(status)`、`solver.wall_time`、`solver.value(var)`：打印状态、耗时与解值。
- 输出细节：用 `format(i, "01x")` 把正方形编号格式化成单个十六进制字符，便于在 ASCII 网格中区分不同正方形。
