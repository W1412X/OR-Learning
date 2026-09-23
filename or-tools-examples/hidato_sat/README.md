# hidato_sat（Hidato 数字蛇谜题）

用 CP-SAT 约束求解器求解 Hidato 数字蛇填数谜题。

## 问题描述

Hidato（希达托/数字蛇）是一种经典的填数谜题：给定一个 N x M 的网格，其中部分格子预先填好了一些数字（称为"线索"），要求把 1 到 N*M 的所有连续整数填入网格，使得任意两个相邻的整数（如 k 与 k+1）在网格中所处的格子相互"接触"——即水平、垂直或对角线方向相邻（八邻域）。

- 输入：一个二维网格，0 表示尚未填数的空格，正整数表示已知的线索数字。代码中 `build_puzzle(problem)` 内置了 6 道不同规模与难度的题目（3x3 简单题到 8x8 中级题，部分取自 Gyora Bededek 的《Hidato: 2000 Pure Logic Puzzles》）。
- 要求：为每个数字 1..N*M 找到它在网格中的位置，满足上述"相邻数字格子接触"的规则，并与所有已知线索一致。

## 建模思路

代码采用"数字 → 位置"的反向建模方式：

- 决策变量：`positions[i]`（`p[i]`）为整数变量，表示数字 i+1 在一维化网格中的位置索引，取值范围 `[0, r*c - 1]`（`r`、`c` 为网格行数与列数，位置索引 = 行 * 列数 + 列）。
- 约束条件：
  - `model.add_all_different(positions)`：所有数字必须占据互不相同的格子。
  - 填入线索：若 `puzzle[i][j] > 0`，则添加 `positions[puzzle[i][j] - 1] == i * c + j`，即已知数字必须落在其给定格子上。
  - 相邻接触：先用 `build_pairs(rows, cols)` 枚举网格中所有相互接触的格子对（八邻域，dx/dy ∈ {-1, 0, 1} 且非自身），得到允许的位置组合表 `close_tuples`；然后对每个 k 添加 `model.add_allowed_assignments([positions[k], positions[k + 1]], close_tuples)`，强制相邻两个数字所在格子必须接触。
- 目标函数：无（可行性问题，找到任一满足全部约束的填法即可）。

## 运行方法

```bash
python3 hidato_sat.py
```

本示例没有定义任何 absl flags，默认行为是：依次求解 `build_puzzle` 内置的 6 道题目（problem 1 到 6），在终端打印每道题的初始盘面与完整解盘面，并输出求解统计信息 `solver.response_stats()`。若在 IPython/Jupyter 环境中运行（`visualization.RunFromIPython()` 为真），则改用 SVG 图形化展示解（线索格子为浅绿色，填入数字为白色）。

## 关键实现说明

- 代码结构：
  - `build_pairs(rows, cols)`：枚举并返回网格中所有相互接触（八邻域）的格子位置对，用于构造允许赋值表。
  - `build_puzzle(problem)`：根据编号返回 6 道内置题目的二维列表（0 表示空格）。
  - `print_matrix(game)` / `print_solution(positions, rows, cols)`：把解还原成二维盘面并美观打印（空格显示为 `.`）。
  - `solve_hidato(puzzle, index)`：建模并求解单个谜题。
  - `main`：循环 problem 1..6 依次求解。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：创建 CP-SAT 模型与求解器，`solver.solve(model)` 执行求解，状态为 `cp_model.OPTIMAL` 表示找到解。
  - `model.new_int_var(lb, ub, name)`：创建整数变量 `positions`。
  - `model.add_all_different(...)`：全不同约束，保证数字与格子一一对应。
  - `model.add_allowed_assignments([vars], tuples)`：表约束（table constraint），限定相邻数字的位置组合必须属于接触对集合，这是本题的核心建模技巧。
  - `solver.value(var)`：读取变量在解中的取值；`solver.wall_time`、`solver.response_stats()` 输出求解耗时与统计。
  - `ortools.sat.colab.visualization`：`RunFromIPython()` 判断运行环境；`SvgWrapper`/`AddRectangle`/`Display` 在 notebook 中绘制解的彩色盘面。
