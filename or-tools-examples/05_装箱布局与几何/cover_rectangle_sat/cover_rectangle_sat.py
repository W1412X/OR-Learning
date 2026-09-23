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

"""用最少数量、两两不重叠的正方形恰好铺满一个 60x50 的矩形。"""

from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


def cover_rectangle(num_squares: int) -> bool:
    """尝试用给定数量的正方形铺满矩形。"""
    # 矩形尺寸：宽 60、高 50
    size_x = 60
    size_y = 50

    model = cp_model.CpModel()

    areas = []
    sizes = []
    x_intervals = []
    y_intervals = []
    x_starts = []
    y_starts = []

    # 为 NoOverlap2D 约束创建区间变量，并创建边长/面积变量
    for i in range(num_squares):
        # 决策变量：第 i 个正方形的边长（正方形，x/y 方向等宽）
        size = model.new_int_var(1, size_y, "size_%i" % i)
        # 决策变量：x 方向的起点与终点坐标
        start_x = model.new_int_var(0, size_x, "sx_%i" % i)
        end_x = model.new_int_var(0, size_x, "ex_%i" % i)
        # 决策变量：y 方向的起点与终点坐标
        start_y = model.new_int_var(0, size_y, "sy_%i" % i)
        end_y = model.new_int_var(0, size_y, "ey_%i" % i)

        # 用 x、y 两个方向的区间变量表示这个正方形
        interval_x = model.new_interval_var(start_x, size, end_x, "ix_%i" % i)
        interval_y = model.new_interval_var(start_y, size, end_y, "iy_%i" % i)

        # 决策变量：正方形面积；约束其等于边长的平方
        area = model.new_int_var(1, size_y * size_y, "area_%i" % i)
        model.add_multiplication_equality(area, [size, size])

        areas.append(area)
        x_intervals.append(interval_x)
        y_intervals.append(interval_y)
        sizes.append(size)
        x_starts.append(start_x)
        y_starts.append(start_y)

    # 主约束：所有正方形两两不重叠
    model.add_no_overlap_2d(x_intervals, y_intervals)

    # 冗余约束：任意竖直/水平线上的总占用不超过矩形边长，加速传播
    model.add_cumulative(x_intervals, sizes, size_y)
    model.add_cumulative(y_intervals, sizes, size_x)

    # 约束：所有正方形面积之和等于矩形面积（配合不重叠即恰好完全覆盖）
    model.add(sum(areas) == size_x * size_y)

    # 对称性破除 1：边长按非降序排列
    for i in range(num_squares - 1):
        model.add(sizes[i] <= sizes[i + 1])

        # 定义 same：当且仅当 sizes[i] == sizes[i + 1] 时为真
        same = model.new_bool_var("")
        model.add(sizes[i] == sizes[i + 1]).only_enforce_if(same)
        model.add(sizes[i] < sizes[i + 1]).only_enforce_if(~same)

        # 边长相同时，再按 x 起点打破平局
        model.add(x_starts[i] <= x_starts[i + 1]).only_enforce_if(same)

    # 对称性破除 2：第一个正方形限制在左下"四分之一象限"内
    model.add(x_starts[0] < (size_x + 1) // 2)
    model.add(y_starts[0] < (size_y + 1) // 2)

    # 创建求解器并求解
    solver = cp_model.CpSolver()
    # 使用 8 个并行 worker
    solver.parameters.num_workers = 8
    # 每个子问题最多求解 10 秒
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.solve(model)
    print("%s found in %0.2fs" % (solver.status_name(status), solver.wall_time))

    # 打印解
    solution_found = status == cp_model.OPTIMAL or status == cp_model.FEASIBLE
    if solution_found:
        # 初始化 60x50 的空白网格
        display = [[" " for _ in range(size_x)] for _ in range(size_y)]
        for i in range(num_squares):
            # 读取每个正方形的起点与边长
            sol_x = solver.value(x_starts[i])
            sol_y = solver.value(y_starts[i])
            sol_s = solver.value(sizes[i])
            # 用单个十六进制字符标记该正方形
            char = format(i, "01x")
            for j in range(sol_s):
                for k in range(sol_s):
                    if display[sol_y + j][sol_x + k] != " ":
                        # 若两个正方形覆盖了同一格，打印错误
                        print(
                            "ERROR between %s and %s"
                            % (display[sol_y + j][sol_x + k], char)
                        )
                    display[sol_y + j][sol_x + k] = char

        # 逐行打印覆盖图
        for line in range(size_y):
            print(" ".join(display[line]))
    return solution_found


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    # 正方形数量从 1 递增尝试，第一个可行的数量就是最少数量
    for num_squares in range(1, 15):
        print("Trying with size =", num_squares)
        if cover_rectangle(num_squares):
            break


if __name__ == "__main__":
    app.run(main)
