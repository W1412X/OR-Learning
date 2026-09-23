# steel_mill_slab_sat（钢铁厂板坯调度问题）

用 CP-SAT 以三种不同建模技术求解钢铁厂板坯生产问题：把订单分配到板坯上，最小化板坯容量浪费。

## 问题描述

钢铁厂板坯（Slab）问题是经典的列生成/装箱类问题：

- 钢厂要轧制一批订单，每个订单 `(size, color)` 有一个宽度/重量 `size` 和一个颜色 `color`。
- 板坯有若干种规格容量（`capacities`，例如 `[0, 17, 44]`）。每块板坯装载的订单总宽度不能超过其容量。
- 一块板坯上**最多只能轧制 2 种颜色**（换色成本高）。
- 每个订单必须恰好分配到一块板坯上。
- 板坯的"浪费（loss）"= 所选规格容量 − 实际装载量（装载量 c 的浪费为 `loss_array[c]`，即不小于 c 的最小规格容量减 c）。

**输入**：板坯容量列表、颜色数量、板坯数量、订单列表（内置 4 个不同规模的实例，problem 0~3）。

**要求**：将所有订单分配到板坯，使总浪费最小。

本示例用 **3 种技术**求解同一问题：`sat`（直接建模）、`sat_table`（用表约束列举全部有效板坯）、`sat_column`（先枚举所有"列"（有效板坯配置）再做集合划分）。

## 建模思路

三种方法共同的数据准备（`build_problem` 与辅助计算）：
- `widths[o]`、`colors[o]`：订单的宽度与颜色；
- `loss_array[c]`：装载量为 c 时的浪费（`min(容量 >= c) - c`）；
- `orders_per_color[c]`：每种颜色的订单列表；`unique_color_orders`：唯一颜色的订单。

### 方法一：`sat` —— 直接建模（`steel_mill_slab`）

**决策变量**
- `assign[o][s]`：布尔变量，订单 o 是否分配到板坯 s；
- `loads[s]`：板坯 s 的装载量，域 `[0, max_capacity]`；
- `color_is_in_slab[s][c]`：布尔变量，颜色 c 是否出现在板坯 s 上；
- `losses[s]`：板坯 s 的浪费，域 `[0, max_loss]`；
- `obj`：总浪费；`positions[p]`：等价订单 p 所在板坯位置（对称性破除用）。

**约束条件**
1. 板坯装载量：`sum(assign[o][s] * widths[o]) == loads[s]`；
2. 每个订单恰好分到一块板坯：`add_exactly_one(assign[o])`；
3. 冗余约束：`sum(loads) == sum(widths)`（加速求解）；
4. 颜色与订单关联：`add_implication(assign[o][s], color_is_in_slab[s][c])`（及其逆蕴涵）；
5. 每块板坯最多 2 种颜色：`sum(color_is_in_slab[s]) <= 2`；以及投影到唯一颜色订单的冗余约束 `sum(assign[o][s] for o in unique_color_orders) <= 2`；
6. 对称性破除：`loads[s] >= loads[s+1]`（板坯按装载量非升排列）；
7. 等价订单对称性破除（`break_symmetries` 开启时）：对宽度相同、颜色组相同的"等价订单"对，用 `add_map_domain` 创建 `positions` 变量并要求 `positions[p[0]] <= positions[p[1]]`；
8. 浪费关联：`add_element(loads[s], loss_array, losses[s])`。

**目标函数**：`model.minimize(obj)`，其中 `obj == sum(losses)`。

### 方法二：`sat_table` —— 表约束建模（`steel_mill_slab_with_valid_slabs`）

- `collect_valid_slabs_dp()` 用动态规划枚举单块板坯所有可行配置（订单集合满足容量与最多 2 色约束），生成 (assign 向量, loss, load) 元组列表；
- 对每块板坯用 `model.add_allowed_assignments([assign...] + [losses, loads], valid_slabs)` 一次性把"订单分配 + 浪费 + 装载量"限制在合法配置表内；
- 再叠加每订单恰好一块板坯、装载量守恒、对称性破除等约束；目标为 `minimize(sum(losses))`。

### 方法三：`sat_column` —— 列选择建模（`steel_mill_slab_with_column_generation`）

- 同样先枚举全部有效板坯"列" `valid_slabs`；
- 决策变量只有 `selected[i]`：是否选择第 i 列；
- 集合划分约束：每个订单被恰好一个选中列覆盖 `== 1`；
- 冗余约束：选中列装载量之和等于总宽度；
- 目标函数：`minimize(sum(selected[i] * valid_slabs[i][-2]))`（最小化所选列的浪费之和）。

## 运行方法

```bash
python3 steel_mill_slab_sat.py
```

代码中定义的全部 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--problem` | `2` | 要求解的问题实例编号（0~3，规模递减；3 是最小的默认问题）。 |
| `--break_symmetries` | `True` | 是否打破等价订单之间的对称性。 |
| `--solver` | `"sat_column"` | 求解方法：`sat`、`sat_table`、`sat_column` 三选一。 |
| `--params` | `"max_time_in_seconds:20,num_workers:8,log_search_progress:true"` | CP-SAT 求解器参数（文本格式）。 |

默认行为：以 `sat_column`（列选择）方法求解 problem 2 实例（28 个订单、20 块板坯），最长 20 秒、8 个 worker 并行并打印搜索日志。求解过程中通过解回调打印中间解的目标值，结束时打印总浪费、用时与冲突数；未找到解则打印 "No solution"。

## 关键实现说明

- **代码结构**：
  - `build_problem(problem_id)`：内置 4 个实例（0：111 块板坯/88 色；1：30 板坯/23 色；2：20 板坯/15 色；3：10 板坯/8 色）；
  - `SteelMillSlabSolutionPrinter(cp_model.CpSolverSolutionCallback)`：解回调类，打印每个中间解的板坯装载、浪费与订单分配明细；
  - `steel_mill_slab()`：方法一直接建模；
  - `collect_valid_slabs_dp()`：DP 枚举单块板坯的全部合法 (订单集合, load, colors) 配置并转成表元组；
  - `steel_mill_slab_with_valid_slabs()`：方法二表约束建模；
  - `steel_mill_slab_with_column_generation()`：方法三列选择建模；
  - `main()`：根据 `--solver` 分发。
- **关键 API**：
  - `model.new_bool_var()` / `model.new_int_var()`：创建布尔/整数变量；
  - `model.add_exactly_one(vars)`：恰好一个为真约束（订单唯一分配）；
  - `model.add_implication(a, b)`：布尔蕴涵（订单分配 ⇒ 颜色出现）；
  - `model.add_element(var, array, target)`：元素约束（由装载量查浪费表）；
  - `model.add_allowed_assignments(vars, tuples)`：表约束（限制变量取值为合法组合）；
  - `model.add_map_domain(pos, bool_vars)`：把整型位置变量与 one-hot 布尔数组互相对应（对称性破除）；
  - `solver.solve(model, callback)`：带解回调求解；`solver.parameters.parse_text_format(params)`：解析求解器参数。
- **技术要点**：
  - 冗余约束（装载量守恒、唯一颜色订单上界）与对称性破除（装载量排序、等价订单位置排序）显著加速求解；
  - 三种方法对比展示了"直接建模 → 表约束 → 列枚举"的建模演进思路。
