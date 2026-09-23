# cryptarithm_sat（字谜算术：SEND+MORE=MONEY）

用 CP-SAT 求解经典的字谜算术（cryptarithm）问题：SEND + MORE = MONEY，即给每个字母分配一个 0~9 的数字，使等式成立。

## 问题描述

现实情景：数字趣题。用英文单词写成一个加法竖式 SEND + MORE = MONEY，其中每个字母代表一个不同的十进制数字（S、E、N、D、M、O、R、Y 共 8 个字母对应 8 个不同数字）。要求满足竖式加法的进位规则：最高位的 S 与 M 是各数的前导数字，不能为 0。求一种（或全部）可行的字母-数字分配方案。

- 输入：无需输入，等式与约束均硬编码在模型中；
- 要求：输出每个字母（s、e、n、d、m、o、r、y）所对应的数字。

## 建模思路

按"竖式加法逐列进位"的方式建模。

- 决策变量：
  - 8 个字母的数字变量：`s = model.new_int_var(1, 9, "s")`（前导数字，取值 1~9）、`e`、`n`、`d`、`m = model.new_int_var(1, 9, "m")`（前导数字）、`o`、`r`、`y`（取值 0~9）；
  - 4 个进位布尔变量：`c0 = model.new_bool_var("c0")`、`c1`、`c2`、`c3`，分别表示从右往左第 1~4 列相加后是否向高位进 1。
- 约束条件：
  1. 互异约束：`model.add_all_different(s, e, n, d, m, o, r, y)`——8 个字母取值两两不同；
  2. 逐列加法（模拟竖式，从右往左）：
     - 第 0 列（个位）：`model.add(c0 == m)`—— MONEY 的最高位 M 只能由 MORE 的最高位 S 与进位共同产生，即 M 等于本列的进位；
     - 第 1 列：`model.add(c1 + s + m == o + 10 * c0)`；
     - 第 2 列：`model.add(c2 + e + o == n + 10 * c1)`；
     - 第 3 列：`model.add(c3 + n + r == e + 10 * c2)`；
     - 第 4 列（末位）：`model.add(d + e == y + 10 * c3)`。
- 目标函数：无（约束满足问题），只要求找到满足全部约束的一个解。

## 运行方法

```bash
python3 cryptarithm_sat.py
```

本示例没有自定义 absl flags（`main` 也不校验多余参数）。默认行为：直接对模型求解一次，当状态为 `cp_model.OPTIMAL` 时打印 `Optimal solution found!`，随后逐行打印每个字母的取值（`s:`、`e:`、`n:`、`d:`、`m:`、`o:`、`r:`、`y:`）。唯一已知解为 9567 + 1085 = 10652。

## 关键实现说明

- 代码结构：单个函数 `send_more_money()`，按"创建变量 → 加约束 → 求解 → 打印"组织；`main` 直接调用它。
- 关键 API：
  - `cp_model.CpModel()`：创建 CP-SAT 模型；
  - `model.new_int_var(lb, ub, name)`：定义字母的数字变量（前导数字下界为 1，其余为 0）；
  - `model.new_bool_var(name)`：定义进位布尔变量；
  - `model.add_all_different(*vars)`：全局互异约束，保证字母取值两两不同；
  - `model.add(...)`：逐列线性等式约束（进位变量作为 0/1 系数直接参与等式）；
  - `cp_model.CpSolver().solve(model)`：求解并返回状态码；
  - `solver.value(var)`：读取每个字母的最终取值。
- 建模技巧：进位用布尔变量而不是 0/1 整数变量，即可直接出现在 `c1 + s + m == o + 10 * c0` 这类线性表达式中，简洁且利于传播。
