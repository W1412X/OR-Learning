# pell_equation_sat

使用 CP-SAT 求解数论中的佩尔方程 \(x^2 - c \cdot y^2 = 1\)。

## 问题描述

佩尔方程（Pell's equation）是数论中的经典不定方程：给定非平方数系数 c，求正整数 x、y 使得 \(x^2 - c \cdot y^2 = 1\)。它出现在连分数展开、逼近无理数 \(\sqrt{c}\) 等场景中。

- 输入：方程系数 c（flag `--coeff`），以及变量允许的最大取值上限（flag `--max_value`）。
- 要求：在上限范围内找到一组正整数解 `(x, y)`，打印结果，并校验其确实满足方程（若不满足则抛出异常）。

## 建模思路

- **决策变量**：
  - `x`、`y`：整数变量，取值范围均为 `[1, max_value]`（正整数解）。
  - 辅助变量 `x_square`、`y_square`：取值范围 `[1, max_value * max_value]`，分别表示 x² 与 y²。
- **约束条件**：
  1. `model.add_multiplication_equality(x_square, x, x)`：强制 `x_square == x * x`（非线性乘法约束）。
  2. `model.add_multiplication_equality(y_square, y, y)`：强制 `y_square == y * y`。
  3. `model.add(x_square - coeff * y_square == 1)`：佩尔方程本身，即 \(x^2 - c \cdot y^2 = 1\)。
- **决策策略**：`model.add_decision_strategy([x, y], cp_model.CHOOSE_MIN_DOMAIN_SIZE, cp_model.SELECT_MIN_VALUE)`——求解时优先选择剩余取值最少的变量，并从其最小值开始尝试，有助于快速找到最小解。
- **目标函数**：无，这是一个可行性问题（找到任意一组满足方程的解）。
- **求解器参数**（`solver.parameters`）：
  - `num_workers = 12`：并行搜索线程数；
  - `log_search_progress = True`：输出搜索进度日志；
  - `cp_model_presolve = True`：启用模型预求解化简；
  - `cp_model_probing_level = 0`：关闭探测（probing）。

## 运行方法

```bash
python3 pell_equation_sat.py --coeff=1 --max_value=5000000
```

absl flag 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--coeff` | `1` | 佩尔方程的系数 c |
| `--max_value` | `5000000` | 变量 x、y 允许的最大取值 |

默认行为：不指定参数时求解 \(x^2 - y^2 = 1\)（系数为 1）。求解成功且状态为 `OPTIMAL` 时打印 `x=... y=... coeff=...`；随后程序会重新验算 \(x^2 - c \cdot y^2\)，若结果不为 1 则抛出 `ValueError("Pell equation not satisfied.")`。求解过程中会输出详细的搜索日志（`log_search_progress=True`）。注意：多余的位置参数会导致 `UsageError`。

## 关键实现说明

- `cp_model.CpModel`：构建约束模型；`new_int_var` 创建整数变量。
- `model.add_multiplication_equality(product, a, b)`：乘积约束，用于表达平方项 \(x \cdot x\)，是处理非线性项的关键 API。
- `model.add(...)`：线性约束，直接写出方程 `x_square - coeff * y_square == 1`。
- `model.add_decision_strategy(...)`：自定义搜索决策策略（变量选择规则 + 取值选择规则）。
- `cp_model.CpSolver`：求解器，通过 `solver.parameters` 设置并行度、日志、预求解与探测等级。
- `solver.solve(model)` 返回状态码，与 `cp_model.OPTIMAL` 比较；`solver.value(var)` 读取解中变量的取值。
- `main` 使用 `Sequence[str]` 类型标注并检查命令行参数个数，多余的参数会触发 `app.UsageError`。
