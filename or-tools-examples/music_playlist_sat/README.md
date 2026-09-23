# 音乐播放列表（Music Playlist）

用 CP-SAT 的回路约束构造一张"均衡"的播放列表：总时长接近目标、覆盖所有流派、相邻歌曲流派不同，并最小化流派转换成本与时长偏差之和。

## 问题描述

为电台/派对制作一张时长约 1 小时的播放列表：

- **曲库**：50 首歌（硬编码），每首歌有名称、时长（秒）、流派（Pop/Techno/Disco/Rock）。
- **流派转换成本**：从一个流派切到另一个流派有正成本（如 Rock→Pop 为 3、Disco→Techno 为 9，矩阵对称性由 `genre_transition_costs` 给出），成本越高越不希望发生这种衔接。
- **要求**：
  1. 播放列表总时长尽可能接近目标时长 `target_duration = 3600` 秒（1 小时）；
  2. 每首歌在列表中最多出现一次；
  3. 曲库中所有出现过的流派在列表中至少出现一首；
  4. 相邻两首歌的流派必须不同；
  5. 在此基础上最小化总的流派转换成本与时长偏差。

## 建模思路

- **图建模**：把播放列表建模为回路约束图——每个节点是一首歌，每条弧表示"歌曲 j 紧跟在歌曲 i 之后"；引入**哑节点** `dummy_node = num_tunes`（编号 50）代表播放列表的开始与结束。
- **决策变量**：`literals[(i, j)]` 为布尔变量，为真表示歌曲 j 紧跟在歌曲 i 之后（由内部函数 `AddArc(i, j)` 创建）。弧分三类：
  - 哑节点 → 任意歌曲（任何歌都可以是第一首）、任意歌曲 → 哑节点（任何歌都可以是最后一首）；
  - **不同流派**的歌曲之间的弧（`possible_successors` 中根本不创建同流派歌曲之间的弧，从而用"减少变量"的方式编码了相邻流派不同的约束，无需额外约束）；
  - 自弧 `(i, i)`：自弧被选中表示歌曲 i 不在播放列表中。
- **约束条件**：
  - `model.add_circuit(arcs)`：所有被选中的弧构成一个回路（哑节点路径进出的哈密顿式回路）；
  - 流派覆盖：`is_active[i] = literals[(i, i)].Not()` 表示歌曲 i 被选中；对每个流派 `model.add(sum(is_active[i] for i in t) >= 1)`——每个流派至少一首歌被选。
- **目标函数**（两部分合并）：
  - 转换成本：整型变量 `total_transition_cost` 等于所有非自弧 `(i, j)` 的 `cost * literals[(i, j)]` 之和（上界为 `(num_tunes-1) * max_transition_cost`）；
  - 时长偏差：整型变量 `total_duration` 等于所有活跃歌曲时长之和；`deviation` 变量通过 `model.add_abs_equality(deviation, total_duration - target_duration)` 取绝对偏差；
  - `model.minimize(total_transition_cost + deviation)`：两项之和最小化（也可加权，如 `10 * total_transition_cost + deviation`，代码注释中有说明）。

## 运行方法

```bash
python3 music_playlist_sat.py
```

- 本示例**没有定义任何 absl flags**，默认行为是：构建上述模型，设置 30 秒求解时限（`solver.parameters.max_time_in_seconds = 30.0`，求解器参数而非命令行 flag），求解后打印总转换成本、播放列表时长、与目标的偏差秒数以及完整歌曲序列。
- 若传入多余的位置参数会抛出 `app.UsageError("Too many command-line arguments.")`。

## 关键实现说明

- **代码结构**：单文件脚本，主体为 `Solve()`（数据 → 模型 → 求解 → 打印，内部用注释分节），入口为 `main(argv)`（`absl.app.run` 启动）。
- **关键 API**（`ortools.sat.python.cp_model`，即 CP-SAT）：
  - `cp_model.CpModel()` / `model.new_bool_var(name)` / `model.new_int_var(lb, ub, name)`：创建模型与布尔/整型变量。
  - `model.add_circuit(arcs)`：回路约束——`arcs` 为 `(尾节点, 头节点, 字面量)` 三元组，被选中弧构成经过每个节点恰一次的回路；自弧机制允许节点"跳过"。
  - `literal.Not()`：取布尔变量的否定文字（自弧的否定即"歌曲活跃"）。
  - `model.add(...)`：添加线性约束（流派覆盖、成本与时长定义）。
  - `model.add_abs_equality(target, expr)`：绝对值等式约束（用于时长偏差）。
  - `model.minimize(expr)`：设置最小化目标。
  - `cp_model.CpSolver()`、`solver.parameters.max_time_in_seconds`、`solver.solve(model)`：创建求解器、设置时限、求解；状态可为 `OPTIMAL` 或 `FEASIBLE`。
  - `solver.value(var)`：读取解中变量的值，用于打印成本、时长与重建播放序列（从哑节点出发沿被选中弧游走）。
