# 迷宫逃脱（Maze Escape）

在 4x4x4 立体迷宫中寻找一条哈密顿路径：从起点出发、按顺序收集所有宝箱、走到终点，且每个方块恰好经过一次。

## 问题描述

一个 4x4x4 的立体网格迷宫（可想象为 4 层、每层 4x4 的立体仓库）。探险者需要：

1. 从 `start = (3, 3, 0)` 出发；
2. 依次按顺序访问 4 个宝箱 `boxes = [(0, 1, 0), (2, 0, 1), (1, 3, 1), (3, 1, 3)]`（即先拿宝箱 0，再拿宝箱 1……顺序不能乱）；
3. 最终到达 `end = (1, 0, 0)`；
4. **每个方块恰好经过一次**（共 64 个方块，即一条哈密顿路径）。

- **合法移动**：每步只能沿 6 个方向之一走一格：x+、x-、y+、y-、z+（向上）、z-（向下）。
- **输入**：网格尺寸（4）、宝箱坐标、起终点坐标（均硬编码）。
- **要求**：构造出这样一条路径，并输出按访问顺序排列的 64 个方块坐标。

## 建模思路

- **决策变量**：为每个格子 `(x, y, z)` 创建整型变量 `position_to_rank[(x, y, z)]`（`rank_{coord}`，取值 `0..63`），表示该格子在路径中被访问的次序（排名）。
- **顺序约束**：
  - `model.add(position_to_rank[start] == 0)`：起点排名为 0；
  - `model.add(position_to_rank[end] == counter - 1)`：终点排名为 63；
  - `model.add(position_to_rank[boxes[i]] < position_to_rank[boxes[i + 1]])`：宝箱必须按给定顺序被访问。
- **路径结构约束（核心）**：`model.add_circuit(arcs)` —— 圆（哈密顿回路）约束。对每个格子与其 6 个方向上的合法邻居，添加一条弧 `(before_index, after_index, move_literal)`，其中 `move_literal` 是新建的布尔变量，并用 `model.add(after_rank == before_rank + 1).only_enforce_if(move_literal)` 强制：走这条弧时，邻居的排名必须比当前格子大 1。这样"回路 + 排名连续"保证了路径不重复、不分叉地覆盖所有格子。
- **闭合回路**：约束要求的是"回路"而非"路径"，因此额外添加一条固定弧 `arcs.append((index_map[end], index_map[start], True))`（终点直达起点、恒为真），把哈密顿路径闭合为回路。
- **目标函数**：无（纯可行性问题）。

## 运行方法

```bash
python3 maze_escape_sat.py
```

支持以下 absl flags：

| flag | 默认值 | 含义 |
|---|---|---|
| `--output_proto` | `""`（空） | 输出文件路径；非空时把 cp_model proto 写入该文件（`model.export_to_file`）。默认不导出。 |
| `--params` | `"num_search_workers:8,log_search_progress:true"` | SAT 求解器参数（文本格式，经 `solver.parameters.parse_text_format` 解析）；本例设置 8 个搜索工作线程并开启搜索日志。 |

- 也可以为空：`--params=""` 时跳过参数解析，仅保留代码中强制开启的 `log_search_progress = True`。
- 求解到 OPTIMAL 后打印按排名排序的 64 个坐标，并标注 `[start]`、`[end]`、`[boxes i]`。

## 关键实现说明

- **代码结构**：
  - `add_neighbor(size, x, y, z, dx, dy, dz, model, index_map, position_to_rank, arcs)`：检查邻居 `(x+dx, y+dy, z+dz)` 是否越界，合法则创建移动布尔变量、添加排名递增条件约束，并把弧加入 `arcs` 列表。
  - `escape_the_maze(params, output_proto)`：主建模与求解函数——建立坐标↔索引映射（`index_map`/`reverse_map`）、创建排名变量、添加顺序约束与 circuit 约束、可选导出 proto、求解并按排名打印路径。
  - `main(argv)`：解析命令行并调用求解函数（`absl.app.run` 启动）。
- **关键 API**（`ortools.sat.python.cp_model`，即 CP-SAT）：
  - `cp_model.CpModel()` / `model.new_int_var(lb, ub, name)` / `model.new_bool_var(name)`：创建模型与整型/布尔变量。
  - `model.add(...)`：添加线性约束；`.only_enforce_if(literal)` 将约束变为条件约束（仅在文字为真时生效）。
  - `model.add_circuit(arcs)`：回路（哈密顿）约束，`arcs` 为 `(尾节点索引, 头节点索引, 字面量)` 三元组列表，被选中的弧构成经过每个节点恰好一次的回路。
  - `model.export_to_file(path)`：把模型 proto 导出为文本文件。
  - `cp_model.CpSolver()`、`solver.parameters.parse_text_format(params)`、`solver.solve(model)`：创建求解器、解析参数、求解。
  - `solver.value(var)`：读取解中变量的值。
