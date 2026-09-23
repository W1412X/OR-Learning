# nqueens_sat

使用 CP-SAT 求解器对经典 N 皇后问题建模，并枚举出全部可行解。

## 问题描述

在国际象棋的 n×n 棋盘上放置 n 个皇后，要求任意两个皇后不能处于同一行、同一列或同一条对角线上。这是约束满足问题的经典入门示例。

- 输入：皇后数量 n（对应棋盘规格 n×n）。
- 要求：找出所有满足约束的摆放方案，逐个以文本棋盘的形式打印出来，最后输出求解统计信息（冲突数、分支数、耗时、解的数量）。

现实类比：类似在网格上安排互不干扰、互不冲突的设施或任务位置。

## 建模思路

- **决策变量**：`queens` 是长度为 n 的整数变量列表，变量名 `"x%i" % i`。数组下标 i 表示列，变量值表示该列皇后所在的行号，取值范围 `[0, n-1]`。由于每列恰好对应一个变量，"每列恰好一个皇后"由建模方式天然保证。
- **约束条件**：
  1. `model.add_all_different(queens)`：所有皇后行号两两不同 → 任意两个皇后不在同一行。
  2. 对角线约束：为每个皇后引入两个辅助整数变量
     - `q1 = queens[i] + i`（行 + 列，同一条对角线上的格子该值相同，变量名 `diag1_i`）；
     - `q2 = queens[i] - i`（行 − 列，另一方向对角线上的格子该值相同，变量名 `diag2_i`）。
     再分别对 `diag1`、`diag2` 施加 `add_all_different`，保证任意两个皇后不在同一条对角线上。
- **目标函数**：无。这是纯可行性（约束满足）问题，不涉及优化。
- **求解设置**：`solver.parameters.enumerate_all_solutions = True`，让求解器枚举全部可行解而不是只返回一个。

## 运行方法

```bash
python3 nqueens_sat.py --size=8
```

absl flag 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--size` | `8` | 皇后数量（棋盘规格 n×n） |

默认行为：不指定参数时求解 8 皇后问题。程序会枚举并打印每一个解（用 `Q` 表示皇后、`_` 表示空位的棋盘），最后输出统计信息：conflicts（冲突次数）、branches（分支数）、wall time（耗时）、solutions found（找到的解数）。

## 关键实现说明

- `cp_model.CpModel()`：创建 CP-SAT 约束模型；`model.new_int_var(lo, hi, name)` 创建整数决策变量。
- `model.add_all_different(...)`：全不同约束，是本模型的核心约束。
- `cp_model.CpSolver`：CP-SAT 求解器；`solver.parameters.enumerate_all_solutions` 控制是否枚举全部解。
- `NQueenSolutionPrinter`：继承 `cp_model.CpSolverSolutionCallback` 的解打印回调类。每找到一个解就触发 `on_solution_callback`，内部通过 `self.value(var)` 读取当前解中变量的取值，按行扫描棋盘打印 `Q`/`_`，并累计 `solution_count`。
- `solver.solve(model, solution_printer)`：带回调求解，每得到一个解就回调打印一次。
