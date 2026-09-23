# 最大化有效布尔组合数量

用 CP-SAT 求解器从若干张候选卡中选择固定数量，使"被完整选中的预定义组合"的数量最大化。

## 问题描述

一个抽象的**组合选择最大化**问题，可理解为卡牌收集/优惠券集齐类场景：

- 有 4 张候选卡，用布尔变量 `card1`、`card2`、`card3`、`card4` 表示"是否选中该卡"。
- 预定义了 4 个有价值的组合（每张卡可以出现在多个组合中）：
  - 组合 1 = {card1, card2}
  - 组合 2 = {card1, card3}
  - 组合 3 = {card2, card4}
  - 组合 4 = {card1, card3, card4}
- 背包/牌库大小 `deck_size = 3`：恰好选中 3 张卡。
- **输入**：候选卡列表、组合定义、`deck_size`（均硬编码）。
- **要求**：在恰好选 3 张卡的前提下，最大化"组合内所有卡都被选中"的组合数量。

## 建模思路

- **决策变量**：
  - `cards = [card1, card2, card3, card4]`：4 个布尔变量（`model.new_bool_var`），表示每张卡是否被选中。
  - `is_valid`：每个组合对应一个布尔变量，表示该组合是否"有效"（组合中的所有卡都被选中）。
- **约束条件**：
  - 牌库大小约束：`model.add(sum(cards) == deck_size)`，即恰好选中 3 张卡。
  - 组合有效性的双向链接（对每个组合）：
    - `model.add_bool_and(is_valid).only_enforce_if(combination)`：组合中所有卡为真 ⟹ `is_valid` 为真；
    - 对组合中的每个文字 `model.add_implication(is_valid, literal)`：`is_valid` 为真 ⟹ 组合中每张卡为真。
    - 两者合起来保证 `is_valid` ⟺ 组合内所有卡均被选中。
- **目标函数**：`model.maximize(sum(valid_combos))`——最大化有效组合的数量。

本例中最优解会选中 card1、card3、card4，使组合 2 和组合 4 同时有效（共 2 个）。

## 运行方法

```bash
python3 maximize_combinations_sat.py
```

- 本示例**没有定义任何 absl flags**，默认行为是：构建上述模型，开启求解日志（`solver.parameters.log_search_progress = True`），求解并打印被选中的卡（`chosen cards: [...]`）。
- 若传入多余的位置参数会抛出 `app.UsageError("Too many command-line arguments.")`。
- 注意 `log_search_progress` 是 CP-SAT 求解器参数（控制是否向标准错误输出打印搜索日志），不是命令行 flag。

## 关键实现说明

- **代码结构**：单文件脚本，包含主函数 `maximize_combinations_sat()` 与 `main(argv)` 入口（`absl.app.run` 启动）。
- **关键 API**（均来自 `ortools.sat.python.cp_model`，即 CP-SAT）：
  - `cp_model.CpModel()`：创建 CP-SAT 模型。
  - `model.new_bool_var(name)`：创建布尔决策变量。
  - `model.add(...)`：添加线性约束（此处为变量之和等于 `deck_size`）。
  - `model.add_bool_and(literals)`：布尔"与"约束（要求所有文字为真）；配合 `.only_enforce_if(literals)` 实现条件约束（前提条件满足时才生效）。
  - `model.add_implication(a, b)`：布尔蕴含 a ⟹ b。
  - `model.maximize(expr)`：设置最大化目标。
  - `cp_model.CpSolver()`：创建求解器；`solver.parameters.log_search_progress = True` 开启搜索日志；`solver.solve(model)` 执行求解并返回状态（本例检查 `cp_model.OPTIMAL`）。
  - `solver.boolean_value(var)`：读取布尔变量在解中的真假值；`card.name` 读取变量名。
