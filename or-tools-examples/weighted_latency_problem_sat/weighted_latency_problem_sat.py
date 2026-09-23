#!/usr/bin/env python3
# Copyright 2010-2025 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""用 CP-SAT 求解器求解一个随机的加权延迟（Weighted Latency）问题。"""

import random
from typing import Sequence

from absl import app
from absl import flags

from ortools.sat.python import cp_model

# 要访问的节点数量
_NUM_NODES = flags.DEFINE_integer("num_nodes", 12, "Number of nodes to visit.")
# 节点所在网格的尺寸
_GRID_SIZE = flags.DEFINE_integer("grid_size", 20, "Size of the grid where nodes are.")
# 利润的取值范围（上限）
_PROFIT_RANGE = flags.DEFINE_integer("profit_range", 50, "Range of profit.")
# 随机种子
_SEED = flags.DEFINE_integer("seed", 0, "Random seed.")
# CP-SAT 求解器参数（文本格式）
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16, max_time_in_seconds:5",
    "Sat solver parameters.",
)
# 若非空，把模型 proto 输出到该文件
_PROTO_FILE = flags.DEFINE_string(
    "proto_file", "", "If not empty, output the proto to this file."
)


def build_model():
    """创建节点与利润数据。"""
    # 固定随机种子，保证结果可复现
    random.seed(_SEED.value)
    x = []
    y = []
    # 下标 0 为起点（仓库）坐标
    x.append(random.randint(0, _GRID_SIZE.value))
    y.append(random.randint(0, _GRID_SIZE.value))
    for _ in range(_NUM_NODES.value):
        # 其余节点坐标在 [0, grid_size] 内均匀随机生成
        x.append(random.randint(0, _GRID_SIZE.value))
        y.append(random.randint(0, _GRID_SIZE.value))

    profits = []
    # 起点利润为 0
    profits.append(0)
    for _ in range(_NUM_NODES.value):
        # 每个访问节点的利润在 [1, profit_range] 内随机取整
        profits.append(random.randint(1, _PROFIT_RANGE.value))
    # 将利润归一化为占比（作为加权延迟的权重）
    sum_of_profits = sum(profits)
    profits = [p / sum_of_profits for p in profits]

    return x, y, profits


def solve_with_cp_sat(x, y, profits) -> None:
    """用 CP-SAT 求解器求解该问题。"""
    model = cp_model.CpModel()

    # 由于使用曼哈顿距离，所有距离之和不会超过该上界。
    horizon = _GRID_SIZE.value * 2 * _NUM_NODES.value
    # times[i]：到达节点 i 的累计行驶时间（决策变量）
    times = [
        model.new_int_var(0, horizon, f"x_{i}") for i in range(_NUM_NODES.value + 1)
    ]

    # 节点 0 是起点。
    model.add(times[0] == 0)

    # 创建 circuit（回路）约束。
    arcs = []
    for i in range(_NUM_NODES.value + 1):
        for j in range(_NUM_NODES.value + 1):
            if i == j:
                continue
            # 节点之间使用曼哈顿距离。
            distance = abs(x[i] - x[j]) + abs(y[i] - y[j])
            # 布尔弧变量：为真表示路线包含弧 i -> j
            lit = model.new_bool_var(f"{i}_to_{j}")
            arcs.append((i, j, lit))

            # 添加节点间的时间递推约束。
            if i == 0:
                # 初始转移：从起点出发，到达时间即为这段距离
                model.add(times[j] == distance).only_enforce_if(lit)
            elif j != 0:
                # 中间转移：到达时间 = 前一节点到达时间 + 距离
                # （最后回到节点 0 的转移无需约束，回路到此结束）
                model.add(times[j] == times[i] + distance).only_enforce_if(lit)
    # 回路约束：每个节点恰一条入弧/出弧，构成单一哈密尔顿回路
    model.add_circuit(arcs)

    # 目标函数：最小化 各节点到达时间 x 利润权重 的加权和（加权延迟）
    model.minimize(cp_model.LinearExpr.weighted_sum(times, profits))

    if _PROTO_FILE.value:
        # 若指定了输出文件，则导出模型 proto
        model.export_to_file(_PROTO_FILE.value)

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        # 解析文本格式的求解器参数
        solver.parameters.parse_text_format(_PARAMS.value)
    # 打印求解日志
    solver.parameters.log_search_progress = True
    solver.solve(model)


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    x, y, profits = build_model()
    solve_with_cp_sat(x, y, profits)
    # TODO(user): Implement routing model.


if __name__ == "__main__":
    app.run(main)
