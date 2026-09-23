# pentominoes_sat

使用 CP-SAT 求解五格骨牌（Pentomino）铺砌问题，将其建模为精确覆盖问题。

## 问题描述

五格骨牌是由 5 个单位方格组成的拼板，共有 12 种形状（F、I、L、N、P、T、U、V、W、X、Y、Z）。给定其中 n 种互不相同的骨牌，要求把它们**不重叠、不越界**地铺满一个面积为 `5 × n` 的矩形。

- 输入：
  - `--pieces`：参与拼砌的骨牌字母集合（默认 `FILNPTUVWXYZ`，即全部 12 种）；
  - `--height`：盒子的高度（默认 5），宽度由总面积自动推导为 `5 * n / height`。
- 要求：输出一种可行的铺法——按行打印盒子，每个格子用覆盖它的骨牌字母表示。
- 校验：若骨牌字母不存在、高度无法整除总面积 `5n`，或盒子尺寸与骨牌不兼容（高度或宽度小于 3），程序会打印提示并退出。

该问题源自实体拼板游戏 Katamino（http://boardgamegeek.com/boardgame/6931/katamino）。

## 建模思路

本示例把铺砌问题归约为**精确覆盖（exact cover）问题**，编码为线性布尔模型：

- **决策变量**：对每种骨牌的每个**非冗余朝向**（0~7 共 8 个朝向，由转置、沿 x 轴镜像、沿 y 轴镜像三个比特位组合而成；与已有朝向完全相同的冗余朝向会被 `orientation_is_redundant` 跳过）及其每个可行左上角摆放位置 `(i, j)`，创建一个布尔变量 `v = model.new_bool_var(name)`（变量名即骨牌字母，如 `"F"`）。`v = 1` 表示"该骨牌以该朝向摆放在该位置"。
  - 二维列表 `position_to_variables[j][i]` 记录：覆盖格子 `(行 j, 列 i)` 的所有摆放变量。
- **约束条件**（均为 `add_exactly_one`，对应精确覆盖的两面）：
  1. 每块骨牌的所有合法摆放变量中**恰好选一个**：`model.add_exactly_one(all_position_variables)`——每块骨牌必须被摆放且只能摆放一次；
  2. 盒子的每个格子被**恰好一块**骨牌覆盖：对 `position_to_variables` 中每个格子的变量列表施加 `model.add_exactly_one`——格子既不能空着，也不能被两块骨牌重叠覆盖。
- **目标函数**：无，纯可行性问题。
- **求解设置**：`solver.parameters.parse_text_format(_PARAMS.value)` 解析 `--params` 传入的求解器参数（默认含 `num_search_workers:16`、`max_time_in_seconds:45` 等）。

## 运行方法

```bash
python3 pentominoes_sat.py --pieces=FILNPTUVWXYZ --height=5
```

absl flag 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--params` | `num_search_workers:16,log_search_progress:false,max_time_in_seconds:45` | 传给 SAT 求解器的参数（文本格式，逗号分隔） |
| `--pieces` | `FILNPTUVWXYZ` | 参与拼砌的骨牌字母子集 |
| `--height` | `5` | 盒子的高度；宽度 = 5 × 骨牌数 ÷ 高度 |

默认行为：用全部 12 种骨牌铺满 `5 × 12` 的盒子。求解结束后打印求解状态与耗时；若状态为 `OPTIMAL`，按行打印铺法，每格显示覆盖它的骨牌字母。不接受多余的位置参数（否则触发 `UsageError`）。

## 关键实现说明

- `cp_model.CpModel` / `model.new_bool_var`：创建布尔决策变量；`model.add_exactly_one(...)`：恰好选一约束，是精确覆盖编码的核心 API。
- `is_one(mask, x, y, orientation)`：判断骨牌形状矩阵 `mask`（`mask[height][width]`，1 表示实格）在指定朝向（比特 0：转置；比特 1：沿 x 轴镜像；比特 2：沿 y 轴镜像）下位置 `(x, y)` 是否为实格。
- `get_height` / `get_width`：返回骨牌在指定朝向下的高度/宽度（转置时行列互换）。
- `orientation_is_redundant(mask, orientation)`：判断某朝向是否与编号更小的某个朝向完全相同（对称去重），减少冗余变量。
- `generate_and_solve_problem(pieces)`：构建精确覆盖模型并求解；打印阶段用 `solver.BooleanValue(v)` 读取布尔变量取值，输出每个格子所属骨牌的变量名（即字母）。
- `main`：定义 12 种骨牌的形状字典，按 `--pieces` 筛选并做合法性校验（字母存在、高度整除总面积、尺寸兼容），随后调用 `generate_and_solve_problem`。
