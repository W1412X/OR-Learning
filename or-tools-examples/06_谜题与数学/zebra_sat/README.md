# zebra_sat（斑马谜题）

用 CP-SAT 求解 Lewis Carroll 发明的经典逻辑推理谜题"斑马问题"（Zebra Puzzle），回答：谁养斑马？谁喝水？

## 问题描述

斑马问题是爱因斯坦谜题的变体，由 Lewis Carroll 提出。场景如下：

有五栋颜色各异的房子排成一排，每栋房子里住着一位不同国籍的人，每人养一种宠物、喝一种饮料、抽一种香烟。已知 14 条线索：

1. 英国人住在红房子里；
2. 西班牙人养狗；
3. 绿房子里喝咖啡；
4. 乌克兰人喝茶；
5. 绿房子紧挨在象牙色房子的右边；
6. 抽 Old Gold 香烟的人养蜗牛；
7. 黄房子里抽 Kools 香烟；
8. 中间的房子喝牛奶；
9. 挪威人住在第一栋房子；
10. 抽 Chesterfields 香烟的人住在养狐狸的人隔壁；
11. 抽 Kools 香烟的房子隔壁是养马的房子；
12. 抽 Lucky Strike 香烟的人喝橙汁；
13. 日本人抽 Parliaments 香烟；
14. 挪威人住在蓝房子隔壁。

问题：**谁养斑马？谁喝水？**

输入即上述线索；输出为推理结果（喝水的房主与斑马主人的国籍）。

## 建模思路

- **决策变量**：5 个类别 x 5 个取值，全部为整数变量（域 1~5，代表房子的位置编号）：
  - 颜色：`red, green, yellow, blue, ivory`；
  - 国籍：`englishman, spaniard, japanese, ukrainian, norwegian`；
  - 宠物：`dog, snails, fox, zebra, horse`；
  - 饮料：`tea, coffee, water, milk, fruit_juice`；
  - 香烟：`old_gold, kools, chesterfields, lucky_strike, parliaments`。
  变量取值即"该属性所在房子的编号"。
- **约束条件**：
  - 5 组 `model.add_all_different(...)`：每个类别内部的 5 个属性占据 5 栋互不相同的房子；
  - 确定性线索（等式约束）：
    - `englishman == red`（英国人住红房子）
    - `spaniard == dog`（西班牙人养狗）
    - `coffee == green`（绿房子喝咖啡）
    - `ukrainian == tea`（乌克兰人喝茶）
    - `green == ivory + 1`（绿房子在象牙色房子右边一栋）
    - `old_gold == snails`（Old Gold 吸烟者养蜗牛）
    - `kools == yellow`（黄房子抽 Kools）
    - `milk == 3`（中间房子喝牛奶）
    - `norwegian == 1`（挪威人住第一栋房子）
    - `lucky_strike == fruit_juice`（Lucky Strike 吸烟者喝橙汁）
    - `japanese == parliaments`（日本人抽 Parliaments）
  - "隔壁"线索（绝对值约束，借助辅助差值变量实现）：
    - `diff_fox_chesterfields == fox - chesterfields` 且 `model.add_abs_equality(1, diff_fox_chesterfields)`：fox 与 chesterfields 相差 1；
    - `diff_horse_kools == horse - kools` 且 `abs == 1`：horse 与 kools 相差 1；
    - `diff_norwegian_blue == norwegian - blue` 且 `abs == 1`：norwegian 与 blue 相差 1。
- **目标函数**：无。这是纯可行性（满足性）问题，求解器找到第一个可行解即为谜底。

## 运行方法

```bash
python3 zebra_sat.py
```

本示例没有定义任何 absl flags，也没有 `main()` 函数与 `absl.app`——模块被导入/执行时直接调用 `solve_zebra()`。默认行为：建模并求解谜题，输出两行结论，形如：

```
The norwegian drinks water.
The japanese owns the zebra.
```

（具体答案以实际求解结果为准。）若无解则打印 "No solutions to the zebra problem, this is unusual!"。

## 关键实现说明

- 函数 `solve_zebra()`（模块加载时直接调用，函数上方有 `# pylint: disable=too-many-statements`）：
  - 创建 `cp_model.CpModel()`；
  - 用 `model.new_int_var(1, 5, "名字")` 声明 25 个整数变量（变量名会用于结果输出，如 `water_drinker.name`）；
  - 用 `model.add_all_different(...)` 声明 5 组互斥约束；
  - 用 `model.add(...)` 添加 11 条确定性等式线索；
  - 用辅助差值变量（域 -4..4）+ `model.add_abs_equality(1, diff)` 编码 3 条"隔壁"线索；
  - 创建 `cp_model.CpSolver()` 并 `solver.solve(model)` 求解；
  - 若 `status == cp_model.OPTIMAL`，用列表推导在 `people = [englishman, spaniard, japanese, ukrainian, norwegian]` 中找出取值等于 `solver.value(water)` / `solver.value(zebra)` 的人，打印其 `.name`；否则打印无解提示。
- 关键 API：`CpModel.new_int_var`、`CpModel.add_all_different`、`CpModel.add`、`CpModel.add_abs_equality`、`CpSolver.solve`、`CpSolver.value`、`cp_model.OPTIMAL`。

依赖：`ortools.sat.python.cp_model`。
