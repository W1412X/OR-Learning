# weighted_latency_problem_sat（加权延迟问题）

用 CP-SAT 求解随机生成的加权延迟（Weighted Latency）问题：从起点出发访问所有节点，使"各节点利润 x 到达该节点的累计行驶时间"之总和最小。

## 问题描述

加权延迟问题是"最小化和"类路径问题的统称（TSP 是其利润全为 1 的特例）：一位服务者从仓库出发，需要遍历所有客户节点。每个客户带有一定"利润/权重"（可理解为货物价值或需求重要度），越晚到达权重大的客户，代价越高。目标是确定一条访问全部节点的路线，使 \(\sum_i w_i \cdot t_i\) 最小，其中 \(t_i\) 是到达节点 i 的累计行驶时间、\(w_i\) 是该节点的利润权重——直觉上应优先拜访高权重客户。

本示例的数据由 `build_model()` 随机生成：

- 共 `num_nodes + 1` 个节点：下标 0 为起点（仓库，利润固定为 0），其余节点坐标在 `[0, grid_size]` 的网格内均匀随机生成；
- 每个访问节点有 `[1, profit_range]` 内随机整数利润，最后按利润总和归一化（`profits = [p / sum_of_profits for p in profits]`）；
- 两点间距离为**曼哈顿距离** `|x[i]-x[j]| + |y[i]-y[j]|`。

要求输出最优的访问回路及最小化的加权延迟总和（求解日志中体现）。

## 建模思路

- **决策变量**：
  - `times[i]`：整数变量（域 `0..horizon`），表示到达节点 i 的累计行驶时间；其中 `horizon = grid_size * 2 * num_nodes`，由曼哈顿距离的性质可知这是总行驶距离（从而也是任一到达时间）的上界；
  - 对每对有序节点 (i, j)（i≠j）创建布尔弧变量 `lit`（命名如 `f"{i}_to_{j}"`），表示路线中包含弧 i→j。
- **约束条件**：
  - `model.add(times[0] == 0)`：节点 0 是起点，出发时刻为 0；
  - 时间传递约束（与弧变量绑定，`only_enforce_if(lit)`）：
    - 若选中弧 0→j（初始转移）：`model.add(times[j] == distance).only_enforce_if(lit)`，即到达 j 的时间就是这段距离；
    - 若选中弧 i→j 且 j≠0（中间转移）：`model.add(times[j] == times[i] + distance).only_enforce_if(lit)`，累计时间递推；至于进入终点 j=0 的最后一段转移则无需约束（回路到此结束，不再有后续节点）；
  - `model.add_circuit(arcs)`：回路约束，每个节点恰一条入弧/出弧且构成单一哈密尔顿回路。
- **目标函数**：`model.minimize(cp_model.LinearExpr.weighted_sum(times, profits))`——最小化所有节点到达时间与利润权重的加权和（加权延迟）。
- 模型导出：若 `--proto_file` 非空，调用 `model.export_to_file(...)` 将模型 proto 写入指定文件。

## 运行方法

```bash
python3 weighted_latency_problem_sat.py
```

代码定义了以下 absl flags（均可在命令行覆盖，例如 `python3 weighted_latency_problem_sat.py --num_nodes=20 --seed=3`）：

| flag | 默认值 | 含义 |
| --- | --- | --- |
| `num_nodes` | `12` | 要访问的节点数量 |
| `grid_size` | `20` | 节点所在网格的尺寸 |
| `profit_range` | `50` | 利润的取值范围（上限） |
| `seed` | `0` | 随机种子 |
| `params` | `"num_search_workers:16, max_time_in_seconds:5"` | CP-SAT 求解器参数（文本格式） |
| `proto_file` | `""` | 若非空，把模型 proto 输出到该文件 |

默认行为：以默认随机种子生成 13 个节点（1 个起点 + 12 个访问节点）与归一化利润，构建模型后用 `parse_text_format` 应用 `params` 参数、打开 `log_search_progress` 日志并求解（最多 5 秒、16 线程），在日志中展示最优目标值。

若传入多余的位置参数，会抛出 `app.UsageError("Too many command-line arguments.")`。

> 环境说明：本示例针对 or-tools 9.15 编写，使用了 `solver.parameters.parse_text_format` 等 API。在较旧版本（如 9.11）上运行会报 `AttributeError: parse_text_format`，请升级 ortools 至 9.15+ 后再运行。

## 关键实现说明

- 函数 `build_model()`：用 `random.seed(_SEED.value)` 固定随机性，生成坐标列表 `x`、`y`（下标 0 为起点），生成利润 `profits`（`profits[0] = 0`）并归一化，返回 `x, y, profits`。
- 函数 `solve_with_cp_sat(x, y, profits)`：主流程——
  - 创建 `cp_model.CpModel()` 与 `times` 变量数组，固定 `times[0] = 0`；
  - 双重循环枚举弧：计算曼哈顿距离、创建布尔弧变量并加入 `arcs`，同时按上述规则用 `only_enforce_if` 添加时间递推约束；
  - `model.add_circuit(arcs)` 添加回路约束；
  - `cp_model.LinearExpr.weighted_sum(times, profits)` 构造加权目标并 `model.minimize(...)`；
  - 可选 `model.export_to_file(_PROTO_FILE.value)` 导出模型 proto；
  - 创建 `cp_model.CpSolver()`，`solver.parameters.parse_text_format(_PARAMS.value)` 解析参数字符串，`log_search_progress = True`，然后 `solver.solve(model)`。
- 关键 API：`CpModel.new_int_var`、`CpModel.new_bool_var`、`CpModel.add`、`LinearConstraint.only_enforce_if`、`CpModel.add_circuit`、`CpModel.minimize`、`cp_model.LinearExpr.weighted_sum`、`CpModel.export_to_file`、`CpSolver.parameters.parse_text_format`。
- 代码中留有 `# TODO(user): Implement routing model.`，提示可改用 routing 库建模。

依赖：`random`、`absl.app`、`absl.flags`、`ortools.sat.python.cp_model`。
