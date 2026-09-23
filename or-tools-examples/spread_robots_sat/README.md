# spread_robots_sat（机器人疏散摆放问题）

在方形房间内摆放 n 个机器人，最大化任意两个机器人之间最小两两欧氏距离（使机器人尽可能相互分散）。

## 问题描述

这是一个空间布局/设施分散问题：在一个 `room_size × room_size` 的方形房间中放置 `num_robots` 个机器人，要求任意两个机器人之间的欧氏距离越远越好，即**最大化所有机器人两两距离中的最小值**（max-min 分散问题）。该目标对应机器人在空间中尽可能均匀疏散的布置方案，可用于基站布局、传感器布点、座位安排等场景。

**输入**：机器人数量（`num_robots`，默认 8）、方形房间的边长（`room_size`，默认 20）。

**要求**：为每个机器人选择整数坐标 (x, y)，使最小两两距离最大；输出最优距离及各机器人坐标。

## 建模思路

模型构建在 `spread_robots()` 函数中：

**决策变量**
- `x[i]`、`y[i]`（i = 0..num_robots-1）：第 i 个机器人的横/纵坐标，域 `[1, room_size]` 的整数。
- `scaled_min_square_distance`：缩放后的"最小平方距离"，域 `[0, 2 * scaling * room_size^2]`（`scaling = 1000`），即模型要最大化的目标变量。

**约束条件**
1. 对任意机器人对 (i, j)（i < j）：
   - `x_diff == x[i] - x[j]`、`y_diff == y[i] - y[j]`：计算两机器人在每个维度上的差值；
   - `add_multiplication_equality(x_diff_sq, x_diff, x_diff)` 与 `add_multiplication_equality(y_diff_sq, y_diff, y_diff)`：计算差值的平方；
   - `scaled_min_square_distance <= scaling * (x_diff_sq + y_diff_sq)`：目标变量不超过缩放后的两机器人平方距离。由于是最大化目标，只需用 ≤ 约束（最大化最小平方距离等价于最大化最小欧氏距离）。
2. 简单的对称性破除：`x[0] <= x[i]` 且 `y[0] <= y[i]`（对所有 i ≥ 1）。

**欧氏距离的处理技巧**：目标本应是两两欧氏距离的最小值，但欧氏距离含开方运算，无法直接在整数变量上定义。代码改用"最小平方距离"作为替代目标（单调等价），并通过乘以常数 `scaling = 1000` 放大域来提高整数近似的精度；最后输出时用 `math.sqrt(objective / scaling)` 换算回真实距离。

**目标函数**

最大化：`model.maximize(scaled_min_square_distance)`，即最大化所有机器人两两平方距离的最小值。

## 运行方法

```bash
python3 spread_robots_sat.py
```

代码中定义的全部 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--num_robots` | `8` | 需要摆放的机器人数量。 |
| `--room_size` | `20` | 机器人所在的方形房间的边长。 |
| `--params` | `"num_search_workers:16, max_time_in_seconds:20"` | CP-SAT 求解器参数（文本格式）。 |

默认行为：在 20×20 的房间中摆放 8 个机器人，以 16 个并行 worker、最长 20 秒求解，并开启搜索日志（`log_search_progress = True`）。求解结束后打印最小两两距离以及每个机器人的 (x, y) 坐标；若未找到解则打印 "No solution found."。

## 关键实现说明

- **代码结构**：单文件单函数结构，`spread_robots(num_robots, room_size, params)` 负责建模、求解与输出；`main()` 解析命令行参数并调用。
- **关键 API**：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_int_var(lb, ub, name)`：创建整数变量（坐标、差值、平方差、目标变量）；
  - `model.add(expr)`：添加线性约束（差值定义、距离约束、对称性破除）;
  - `model.add_multiplication_equality(var, a, b)`：添加乘法约束 `var == a * b`，用于计算差值的平方；
  - `model.maximize(obj)`：设定最大化目标；
  - `solver.parameters.parse_text_format(params)`：以文本格式解析求解器参数（对应 `--params`）；
  - `solver.solve(model)` / `solver.value(var)` / `solver.objective_value`：求解并读取解。
- **技术要点**：
  - 用"平方距离 + 缩放因子"绕开整数模型无法表达开方运算的限制；
  - 通过简单的坐标偏序（`x[0] <= x[i], y[0] <= y[i]`）实现朴素对称性破除，缩小搜索空间。
