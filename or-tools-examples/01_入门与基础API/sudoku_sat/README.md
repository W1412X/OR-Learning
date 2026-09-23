# sudoku_sat（数独求解器）

用 CP-SAT 求解标准 9×9 数独：在满足行、列、宫（3×3 块）约束的前提下填充数字 1~9。

## 问题描述

数独是经典的约束满足问题：在 9×9 的棋盘上填入数字 1~9，要求：

- 每一行的 9 个数字互不相同；
- 每一列的 9 个数字互不相同；
- 每个 3×3 宫（子块）内的 9 个数字互不相同；
- 部分格子为给定的初始提示数，必须保留。

**输入**：代码内置的 `initial_grid` 9×9 初始棋盘（0 表示空格，非 0 表示预填数字）。

**要求**：求出满足全部数独规则的完整填法，并按行打印解。

## 建模思路

模型构建在 `solve_sudoku()` 函数中（`cell_size = 3`，`line_size = 9`）：

**决策变量**

- `grid[(i, j)]`：第 i 行第 j 列格子的取值，域 `[1, 9]` 的整数（`model.new_int_var(1, line_size, ...)`）。

**约束条件**

1. **行约束**：对每一行 i，`model.add_all_different(grid[(i, j)] for j in line)`——同一行所有格子的取值两两不同。
2. **列约束**：对每一列 j，`model.add_all_different(grid[(i, j)] for i in line)`——同一列所有格子的取值两两不同。
3. **宫（3×3 块）约束**：对每个宫 `(i, j)`（i、j ∈ 0..2），收集其 9 个格子 `grid[(i*3+di, j*3+dj)]` 并调用 `add_all_different`——同一宫内取值两两不同。
4. **初始提示数**：`model.add(grid[(i, j)] == initial_grid[i][j])`——把初始棋盘中非 0 的格子固定为给定值。

**目标函数**

无（数独是纯可行性/约束满足问题，不含优化目标），求解器只需找到一个满足全部约束的解。

## 运行方法

```bash
python3 sudoku_sat.py
```

代码中**没有定义任何 absl flags**。默认行为：直接求解内置在代码中的数独题目，若解为最优/可行（status == OPTIMAL），按行打印完整的 9×9 解矩阵（每行一个长度为 9 的数字列表）。

如需解其他题目，直接修改代码中的 `initial_grid` 即可（0 表示空格）。

## 关键实现说明

- **代码结构**：单文件单函数结构；`solve_sudoku()` 完成建模、求解与打印；文件末尾直接调用 `solve_sudoku()`（导入该模块时也会执行）。
- **关键 API**：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_int_var(1, 9, name)`：为每个格子创建取值 1~9 的整数变量，以字典 `grid[(i, j)]` 组织；
  - `model.add_all_different(vars)`：两两互异约束——数独三种规则的统一表达（行、列、宫各调用一次），是该模型的核心 API；
  - `model.add(expr)`：固定初始提示数；
  - `cp_model.CpSolver().solve(model)`：求解；`solver.value(var)` 读取解。
- **技术要点**：
  - 数独规则天然映射为 27 组 `add_all_different` 约束（9 行 + 9 列 + 9 宫），无需额外变量；
  - 用整数下标运算 `i * cell_size + di` 定位宫内格子，代码简洁；
  - 该示例是学习 CP-SAT"约束满足问题（无目标函数）"的入门范例。
