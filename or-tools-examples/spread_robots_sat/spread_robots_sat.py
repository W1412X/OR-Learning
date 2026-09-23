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

"""最大化方形空间内 n 个机器人之间两两距离的最小值。"""

import math
from typing import Sequence
from absl import app
from absl import flags
from ortools.sat.python import cp_model

# 需要摆放的机器人数量。
_NUM_ROBOTS = flags.DEFINE_integer("num_robots", 8, "Number of robots to place.")
# 机器人所在的方形房间的边长。
_ROOM_SIZE = flags.DEFINE_integer(
    "room_size", 20, "Size of the square room where robots are."
)
# CP-SAT 求解器参数（文本格式）。
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16, max_time_in_seconds:20",
    "Sat solver parameters.",
)


def spread_robots(num_robots: int, room_size: int, params: str) -> None:
    """优化机器人的摆放位置。"""
    model = cp_model.CpModel()

    # 为每个机器人创建坐标 (x, y) 变量。
    # x[i]、y[i]：第 i 个机器人的横/纵坐标，取值范围 [1, room_size]。
    x = [model.new_int_var(1, room_size, f"x_{i}") for i in range(num_robots)]
    y = [model.new_int_var(1, room_size, f"y_{i}") for i in range(num_robots)]

    # 问题的原始定义是最大化任意两个机器人之间的最小欧氏距离。
    # 不幸的是，欧氏距离使用了开方运算，而开方在整数变量上没有定义。
    # 为了绕开这一点，我们创建一个 min_square_distance（最小平方距离）
    # 变量，并保证它的值不超过任意两个机器人欧氏距离的平方。
    #
    # 这种编码方式精度较低。为了提高精度，我们将 min_square_distance
    # 变量的定义域乘以一个常数因子进行缩放，同时把两个机器人欧氏距离的
    # 平方也乘以相同的因子。
    #
    # 我们创建一个定义域为 [0..scaling * 最大欧氏距离平方] 的
    # scaled_min_square_distance 变量，使得对所有的机器人对 i 满足：
    #     scaled_min_square_distance <= scaling * (x_diff_sq[i] + y_diff_sq[i])
    scaling = 1000
    # 目标变量：缩放后的最小平方距离（所有机器人对的最小值）。
    scaled_min_square_distance = model.new_int_var(
        0, 2 * scaling * room_size**2, "scaled_min_square_distance"
    )

    # 构建中间变量，并收集每一维度上的平方距离。
    for i in range(num_robots - 1):
        for j in range(i + 1, num_robots):
            # 计算机器人 i 与机器人 j 在每个维度上的距离（差值）。
            x_diff = model.new_int_var(-room_size, room_size, f"x_diff{i}")
            y_diff = model.new_int_var(-room_size, room_size, f"y_diff{i}")
            model.add(x_diff == x[i] - x[j])
            model.add(y_diff == y[i] - y[j])

            # 计算上述差值的平方。
            x_diff_sq = model.new_int_var(0, room_size**2, f"x_diff_sq{i}")
            y_diff_sq = model.new_int_var(0, room_size**2, f"y_diff_sq{i}")
            model.add_multiplication_equality(x_diff_sq, x_diff, x_diff)
            model.add_multiplication_equality(y_diff_sq, y_diff, y_diff)

            # 我们只需要目标变量 <= 缩放后的平方距离即可：
            # 因为我们在最大化最小距离，这与最大化最小平方距离是等价的。
            model.add(scaled_min_square_distance <= scaling * (x_diff_sq + y_diff_sq))

    # 朴素的对对称性破除：规定第 0 个机器人的坐标不大于其他机器人。
    for i in range(1, num_robots):
        model.add(x[0] <= x[i])
        model.add(y[0] <= y[i])

    # 目标函数：最大化缩放后的最小平方距离。
    model.maximize(scaled_min_square_distance)

    # 创建求解器并求解模型。
    solver = cp_model.CpSolver()
    if params:
        solver.parameters.parse_text_format(params)
    solver.parameters.log_search_progress = True
    status = solver.solve(model)

    # 打印解。
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(
            f"Spread {num_robots} with a min pairwise distance of"
            f" {math.sqrt(solver.objective_value / scaling)}"
        )
        for i in range(num_robots):
            print(f"robot {i}: x={solver.value(x[i])} y={solver.value(y[i])}")
    else:
        print("No solution found.")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    spread_robots(_NUM_ROBOTS.value, _ROOM_SIZE.value, _PARAMS.value)


if __name__ == "__main__":
    app.run(main)
