# integer_programming（整数规划入门示例）

用 OR-Tools 线性求解器封装（pywraplp）演示两种风格 API 的整数规划用法。

## 问题描述

这是一个教学性质的入门示例：求解一个非常简单的整数线性规划（ILP）问题，用同一个模型分别演示 OR-Tools 线性求解器（`pywraplp`）的两种 API 风格，并依次在多个后端求解器（GLPK、SCIP、SAT、XPRESS）上运行对比。

具体问题为：

- 输入：决策变量 x1、x2（非负整数）；目标系数与约束系数直接写死在代码里。
- 要求：在满足约束 `3*x1 + 2*x2 >= 17` 的前提下，最小化目标 `x1 + 2*x2`。

## 建模思路

- 决策变量：`x1 = solver.IntVar(0.0, infinity, "x1")` 与 `x2 = solver.IntVar(0.0, infinity, "x2")`——两个非负整数变量。
- 约束条件：`3 * x1 + 2 * x2 >= 17`。
  - 自然语言风格 API：`solver.Add(3 * x1 + 2 * x2 >= 17)`。
  - C++ 风格 API：`ct = solver.Constraint(17, infinity)` 后调用 `ct.SetCoefficient(x1, 3)`、`ct.SetCoefficient(x2, 2)`。
- 目标函数：最小化 `x1 + 2 * x2`。
  - 自然语言风格 API：`solver.Minimize(x1 + 2 * x2)`。
  - C++ 风格 API：`objective = solver.Objective()` 后调用 `objective.SetCoefficient(x1, 1)`、`objective.SetCoefficient(x2, 2)`（默认最小化方向）。

## 运行方法

```bash
python3 integer_programming.py
```

本示例没有定义任何 absl flags，也没有使用 `absl.app`。默认行为是：先用"自然语言风格 API"依次在 GLPK、SCIP、SAT、XPRESS 四个求解器上求解同一模型（CBC 因 ASAN 问题被注释掉），再用"C++ 风格 API"重复同样的流程；每次求解都打印变量数、约束数、求解耗时（毫秒）、最优目标值、各变量取值以及分支定界节点数。

注意：运行本示例需要本地已安装并编译了对应的后端求解器；若某个求解器不可用，`pywraplp.Solver.CreateSolver` 会返回 None，对应示例将被跳过（直接 return，不报错）。

## 关键实现说明

- 代码结构：
  - `Announce(solver, api_type)`：打印示例标题横幅。
  - `RunIntegerExampleNaturalLanguageAPI(optimization_problem_type)`：用自然语言风格 API（`IntVar`、`Minimize`、`Add`）建模并求解。
  - `RunIntegerExampleCppStyleAPI(optimization_problem_type)`：用 C++ 风格 API（`Objective().SetCoefficient`、`Constraint(min, max).SetCoefficient`）建模并求解。
  - `SolveAndPrint(solver, variable_list)`：执行 `solver.Solve()`，断言状态为最优（`pywraplp.Solver.OPTIMAL`）并校验解（`solver.VerifySolution(1e-7, True)`），打印目标值、变量取值、耗时与 `solver.nodes()`（分支定界节点数）。
  - `RunAllIntegerExampleNaturalLanguageAPI` / `RunAllIntegerExampleCppStyleAPI`：分别遍历多个求解器调用上述两个函数。
  - `main`：依次执行两种 API 风格的全部示例。
- 关键 API：
  - `pywraplp.Solver.CreateSolver(name)`：按名称创建线性求解器封装（"GLPK"/"SCIP"/"SAT"/"XPRESS" 等）。
  - `solver.IntVar(lb, ub, name)`：创建整数变量；`solver.infinity()` 表示无穷大上下界。
  - `solver.Minimize(expr)` / `solver.Add(constraint)`：自然语言风格的目标与约束定义。
  - `solver.Objective().SetCoefficient(var, coef)` / `solver.Constraint(lb, ub).SetCoefficient(var, coef)`：C++ 风格的目标与约束定义。
  - `solver.Solve()`、`solver.Objective().Value()`、`variable.solution_value()`、`solver.wall_time()`、`solver.nodes()`：求解并读取结果。
  - `solver.VerifySolution(tolerance, log_errors)`：校验解的合法性（对 GLOP 以外的求解器强烈建议开启）。
