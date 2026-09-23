# 线性规划 API 示例

用同一个线性规划问题演示 `pywraplp` 的两种 API 风格（自然语言 API 与 C++ 风格 API），并在 GLOP、GLPK、CLP、PDLP、XPRESS 等多个后端求解器上运行。

## 问题描述

一个抽象的**连续变量线性规划（LP）**练习题，业务上可理解为"三种产品的生产计划"：

- 有三种产品，产量分别为连续变量 \(x_1, x_2, x_3\)（非负，可取任意实数，不要求整数）。
- 每单位三种产品的利润分别为 10、6、4。
- 生产受三种资源限制（如原料、工时、设备能力）：
  - 资源 A：\(10x_1 + 4x_2 + 5x_3 \le 600\)
  - 资源 B：\(2x_1 + 2x_2 + 6x_3 \le 300\)
  - 总产量限制：\(x_1 + x_2 + x_3 \le 100\)

- **输入**：上述系数与右端项（硬编码在代码中）。
- **要求**：在满足全部约束的前提下最大化总利润 \(10x_1 + 6x_2 + 4x_3\)。

## 建模思路

同一个模型在代码里写了两种等价构造方式：

- **决策变量**：`x1`、`x2`、`x3`，均为 `[0, +infinity)` 上的连续变量（`solver.NumVar`）。
- **目标函数**：最大化 `10*x1 + 6*x2 + 4*x3`
  - 自然语言 API：`solver.Maximize(10 * x1 + 6 * x2 + 4 * x3)`
  - C++ 风格 API：`objective.SetCoefficient(...)` 逐个设置系数后调用 `objective.SetMaximization()`
- **约束条件**（两种 API 对应同一条约束）：
  - `c0`/`c1`/`c2`：
    - \(x_1 + x_2 + x_3 \le 100\)
    - \(10x_1 + 4x_2 + 5x_3 \le 600\)
    - \(2x_1 + 2x_2 + 6x_3 \le 300\)
  - 自然语言 API 用 `solver.Add(表达式 <= 上界, "名称")` 直接写数学式；
  - C++ 风格 API 用 `solver.Constraint(下界, 上界, "名称")` + `SetCoefficient` 逐项设置系数。
- 求解后还演示了高级用法：读取 `reduced_cost`（检验数）、`dual_value`（对偶值/影子价格）与 `ComputeConstraintActivities`（约束实际活跃值）。

## 运行方法

```bash
python3 linear_programming.py
```

- 本示例**没有定义任何 absl flags**，也没有使用 `absl.app`，默认行为是：
  1. 依次用 GLOP、GLPK_LP、CLP、PDLP、XPRESS_LP 五种求解器运行**自然语言 API** 版本；
  2. 再依次用同样五种求解器运行 **C++ 风格 API** 版本。
- 注意：GLPK、CLP、XPRESS、PDLP 是否可用取决于当前安装的 OR-Tools 构建版本；若某求解器不可用，`CreateSolver` 返回 None，对应函数会直接跳过。

## 关键实现说明

- **代码结构**：
  - `Announce(solver, api_type)`：打印当前运行的求解器与 API 风格标题。
  - `RunLinearExampleNaturalLanguageAPI(optimization_problem_type)`：用自然语言 API（`Maximize`/`Add`）建模并求解。
  - `RunLinearExampleCppStyleAPI(optimization_problem_type)`：用 C++ 风格 API（`Objective()`/`Constraint()` + `SetCoefficient`）建模并求解。
  - `SolveAndPrint(solver, variable_list, constraint_list, is_precise)`：执行求解并打印变量数、约束数、耗时、目标值、各变量取值、迭代次数、检验数与对偶值等信息；`is_precise` 为 True 时（非 PDLP 求解器）调用 `VerifySolution(1e-7, True)` 校验解的精度。
  - `main()`：按 5 种求解器 x 2 种 API 的组合共运行 10 次求解。
- **关键 API**：
  - `pywraplp.Solver.CreateSolver(name)`：按名称创建底层求解器（如 `"GLOP"`）。
  - `solver.NumVar(lb, ub, name)`：创建连续决策变量。
  - `solver.Maximize(expr)` / `solver.Add(constraint)`：自然语言式建模。
  - `solver.Objective()`、`SetCoefficient`、`SetMaximization`：显式设置目标。
  - `solver.Constraint(lb, ub, name)`、`SetCoefficient`：显式设置约束。
  - `solver.Solve()`：求解，返回状态（本例断言为 `pywraplp.Solver.OPTIMAL`）。
  - `solver.infinity()`：表示正无穷的常数。
  - 结果读取：`Objective().Value()`、`variable.solution_value()`、`variable.reduced_cost()`、`constraint.dual_value()`、`solver.ComputeConstraintActivities()`。
