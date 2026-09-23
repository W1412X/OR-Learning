# knapsack_2d_sat（二维矩形背包/装箱问题）

用 CP-SAT 求解二维矩形背包问题：在一个固定大小的容器内摆放若干矩形物品，使所选物品总价值最大。代码演示了三种不同的建模方式。

## 问题描述

二维背包问题（2D Knapsack）：给定一个最大宽度 `max_width = 30`、最大高度 `max_height = 20` 的矩形容器，以及若干种矩形物品；每种物品有固定的宽、高、可用数量（available）与价值（value）。要求从这些物品中挑选若干个（同种物品最多选 available 个），在不重叠、不超出容器边界的前提下摆放进容器（允许旋转 90 度），使所选物品的总价值最大。

输入数据（`build_data` 中内联的表格，共 10 种物品 k1-k10）包含列：`item`（名称）、`width`（宽）、`height`（高）、`available`（可用数量）、`value`（价值）、`color`（颜色）。

- 输入：物品表 + 容器尺寸（宽 30、高 20）。
- 要求：输出被选物品的摆放方案（每个物品的 x/y 起点、宽高与价值），以 pandas DataFrame 形式打印。

本示例改编自 https://yetanothermathprogrammingconsultant.blogspot.com/2021/10/2d-knapsack-problem.html。

## 建模思路

三种可选建模方式由 flag `--model` 切换（把每种物品按 available 数量展开为一个个独立物品）：

1. `duplicate`（`solve_with_duplicate_items`）——复制法处理旋转：
   - 对每个物品额外复制一个"旋转 90 度"的副本（宽高互换），共 `2 * num_data_items` 个候选矩形。
   - 决策变量：`is_used[i]`（布尔，是否选用物品 i）、`x_starts/x_ends/y_starts/y_ends`（物品坐标，`[0, max_width]` / `[0, max_height]`）、`x_intervals/y_intervals`（区间变量，长度为 `item_widths[i] * is_used[i]`，即未选用时长度为 0）。
   - 约束：未使用的物品坐标固定在原点（`model.add(x_starts[i] == 0).only_enforce_if(~is_used[i])`）；同一物品的原版与旋转版至多选一个（`model.add(is_used[i] + is_used[i + num_data_items] <= 1)`）；二维互不重叠 `model.add_no_overlap_2d(x_intervals, y_intervals)`。
   - 目标：`model.maximize(cp_model.LinearExpr.weighted_sum(is_used, item_values))` 最大化总价值。

2. `optional`（`solve_with_duplicate_optional_items`）——可选区间法：
   - 同样复制旋转副本，但使用 `new_optional_fixed_size_interval_var` 创建"可选定长区间"（选中才存在），区间起点变量范围按物品尺寸收紧（`max_width - item_width`、`max_height - item_height`），天然保证不越界。
   - 其余约束与目标同上（旋转副本二选一、`add_no_overlap_2d`、最大化加权价值）。

3. `rotation`（`solve_with_rotations`，默认）——状态法处理旋转：
   - 每个物品只有一份，用三个布尔变量表示状态：`not_selected`（未选）、`no_rotation`（不旋转）、`rotated`（旋转 90 度），并 `model.add_exactly_one(...)` 三选一。
   - 物品的宽 `x_sizes[i]` 与高 `y_sizes[i]` 是取值于 `{0, w, h}` 的整数变量（`cp_model.Domain.FromValues`），由状态决定：未选时宽高与坐标全为 0；不旋转时 `(x_size, y_size) = (dim1, dim2)`；旋转时 `(x_size, y_size) = (dim2, dim1)`（用 `only_enforce_if` 条件约束绑定）。
   - `is_used[i] = ~not_selected`，约束 `model.add_no_overlap_2d(x_intervals, y_intervals)`，目标 `model.maximize(cp_model.LinearExpr.weighted_sum(is_used, item_values))`。

三种方式的核心思想一致：把"矩形摆放"转化为 x、y 两个维度上的区间不重叠问题（`add_no_overlap_2d`）。

## 运行方法

```bash
python3 knapsack_2d_sat.py
```

代码中定义了以下 absl flags：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--output_proto` | `""`（空） | 将 CP-SAT 模型 proto 写入指定的输出文件；为空则不写出。 |
| `--params` | `num_search_workers:16,log_search_progress:true,max_time_in_seconds:45` | SAT 求解器参数（以文本格式传给 `solver.parameters.parse_text_format`）：16 个并行 worker、打印搜索日志、限时 45 秒。 |
| `--model` | `rotation` | 选择建模方式：`duplicate`、`rotation` 或 `optional`。 |

示例：

```bash
# 默认使用 rotation 状态法建模
python3 knapsack_2d_sat.py
# 使用复制法建模，并把模型 proto 导出到文件
python3 knapsack_2d_sat.py --model=duplicate --output_proto=model.pbtxt
```

运行后先打印输入数据表与容器尺寸，求解成功（`OPTIMAL` 或 `FEASIBLE`）后打印被选物品的摆放方案 DataFrame（含 x_start、y_start、item_width、item_height、x_end、y_end、item_value）。

## 关键实现说明

- 代码结构：
  - `build_data()`：用内联文本 + `pd.read_table` 构建物品数据表，返回 `(data, max_height, max_width)`。
  - `solve_with_duplicate_items(data, max_height, max_width)`：复制法建模（普通区间变量 + 长度与 is_used 相乘实现"消失"）。
  - `solve_with_duplicate_optional_items(...)`：可选区间法建模（`new_optional_fixed_size_interval_var`）。
  - `solve_with_rotations(...)`：旋转状态法建模（三状态布尔变量 + 域受限的尺寸变量）。
  - `main(_)`：根据 `--model` flag 分发到对应求解函数。
- 关键 API：
  - `cp_model.CpModel()` / `cp_model.CpSolver()`：建模与求解；`solver.parameters.parse_text_format(_PARAMS.value)` 解析命令行传入的求解器参数。
  - `model.new_bool_var(name)`：创建 is_used / 状态布尔变量。
  - `model.new_int_var(lb, ub, name)`：创建坐标变量；`model.new_int_var_from_domain(cp_model.Domain.FromValues([...]), name)`：创建取值限于 {0, w, h} 的尺寸变量。
  - `model.new_interval_var(start, size, end, name)`：普通区间变量（duplicate 法中 size 为 `item_widths[i] * is_used[i]`，未选用时长度为 0）。
  - `model.new_optional_fixed_size_interval_var(start, size, presence, name)`：可选定长区间变量（optional 法）。
  - `model.add_no_overlap_2d(x_intervals, y_intervals)`：二维互不重叠约束——本问题的核心约束。
  - `model.add(...).only_enforce_if(lit)`：条件约束（未选用物品固定在原点、旋转状态决定宽高等）。
  - `model.add_exactly_one([...])`：三状态（未选/不旋转/旋转）恰好选一。
  - `cp_model.LinearExpr.weighted_sum(vars, weights)`：构造加权求和目标，`model.maximize(...)` 最大化总价值。
  - `str(model)`：把模型 proto 序列化成文本写出（`--output_proto`）。
  - numpy（`np.repeat` 按可用数量展开物品、`np.concatenate` 拼接旋转副本）与 pandas（数据表读取与结果展示）。
