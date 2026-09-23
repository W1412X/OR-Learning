# qubo_sat（用 CP-SAT 求解 QUBO 问题）

本示例演示如何将 **QUBO（Quadratic Unconstrained Binary Optimization，二次无约束二值优化）** 问题转化为 CP-SAT 模型，并使用 OR-Tools 的 CP-SAT 求解器求最优解。

## 问题描述

QUBO 是量子计算与组合优化领域常见的标准问题形式：给定一个系数矩阵，在一组二值（0/1）变量上最小化一个**二次型目标函数**（没有显式约束）：
$$

 \min_{x \in \{0,1\}^n} \sum_{i,j} Q_{ij}\, x_i x_j 

$$
- 输入：代码中的 `RAW_DATA`，一个 75×76 的浮点系数矩阵（前 75 列为二次型 Q 矩阵，第 76 列即每行最后一个元素是一次项线性系数），矩阵元素同时包含正、负系数。
- 要求：为每个变量选取 0 或 1 的取值，使二次型目标函数最小。现实中这类模型常用于投资组合选择、图分割、电路设计等“选或不选”且“两两组合有收益/代价”的决策场景。

## 建模思路

代码把 QUBO 的二次型展开成布尔项之和：

- **决策变量**：`variables[i]`，即 75 个布尔变量 `x_i`（`model.new_bool_var("x_%i" % i)`），对应 QUBO 的每个二值决策。
- **二次项处理**：对每一对 `i < j`，先合并对称系数 `coeff = RAW_DATA[i][j] + RAW_DATA[j][i]`；若系数为 0 则跳过。由于 CP-SAT 目标只支持线性表达式，代码为每个非零二次项新建一个辅助布尔变量 `var` 来表示乘积项 `x_i AND x_j`，并用两条约束实现 AND 语义：
  - `model.add_bool_or([~x_i, ~x_j, var])`：若 `x_i` 与 `x_j` 同时为真，则 `var` 必须为真。
  - `model.add_implication(var, x_i)` 与 `model.add_implication(var, x_j)`：`var` 为真会强制 `x_i`、`x_j` 也为真。
  三条约束合起来即 `var ⇔ x_i AND x_j`，因此可以把 `x_i * x_j` 的贡献写成线性项 `coeff * var`。
- **一次项处理**：对每个变量 `i`，自作用系数 `self_coeff = RAW_DATA[i][i] + RAW_DATA[i][-1]`（对角项与矩阵最后一列的线性系数合并），非零时直接把 `variables[i]` 加入目标。
- **目标函数**：`model.minimize(sum(obj_vars[i] * obj_coeffs[i] ...))`，即最小化所有一次项与二次项的加权和（`obj_vars` / `obj_coeffs` 分别收集目标中的变量与系数）。

## 运行方法

```bash
python3 qubo_sat.py
```

本示例**没有定义任何 absl flags 命令行参数**。默认行为是：求解内置 `RAW_DATA` 矩阵定义的 QUBO 实例，并在控制台输出求解日志（因为 `log_search_progress=True`）。求解器参数在代码中硬编码：

- `num_search_workers = 16`：使用 16 个并行搜索线程。
- `log_search_progress = True`：打印求解进度日志。
- `max_time_in_seconds = 30`：最长求解 30 秒。

若传入多余的位置参数，程序会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

代码结构非常简洁，由数据与两个函数构成：

- `RAW_DATA: List[List[float]]`：模块级常量，75×76 的 QUBO 系数矩阵（最后一列是一次项系数，用 `# fmt: off/on` 保持原始排版）。
- `solve_qubo()`：建模与求解主函数。
  - `cp_model.CpModel()`：创建 CP-SAT 模型。
  - `model.new_bool_var()`：创建布尔决策变量和二次项辅助变量。
  - `model.add_bool_or()` / `model.add_implication()`：用布尔逻辑约束实现"与"门的编码，这是把二次目标线性化的关键技巧。
  - `model.minimize()`：设置线性化后的最小化目标。
  - `cp_model.CpSolver()`：创建求解器，通过 `solver.parameters` 设置并行线程数、日志与时间上限，然后 `solver.solve(model)` 求解。
- `main(argv)`：absl 的 `app.run(main)` 入口，校验命令行参数后调用 `solve_qubo()`。
