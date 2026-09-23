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

"""本模型实现了一个数独求解器。"""

from ortools.sat.python import cp_model


def solve_sudoku() -> None:
    """用 CP-SAT 求解器求解数独问题。"""
    # 创建模型。
    model = cp_model.CpModel()

    # 宫的边长（3×3 小块）与行/列长度（9×9 棋盘）。
    cell_size = 3
    line_size = cell_size**2
    line = list(range(0, line_size))  # 行/列下标 0..8。
    cell = list(range(0, cell_size))  # 宫下标 0..2。

    # 内置的初始数独棋盘（0 表示空格，非 0 表示预填提示数）。
    initial_grid = [
        [0, 6, 0, 0, 5, 0, 0, 2, 0],
        [0, 0, 0, 3, 0, 0, 0, 9, 0],
        [7, 0, 0, 6, 0, 0, 0, 1, 0],
        [0, 0, 6, 0, 3, 0, 4, 0, 0],
        [0, 0, 4, 0, 7, 0, 1, 0, 0],
        [0, 0, 5, 0, 9, 0, 8, 0, 0],
        [0, 4, 0, 0, 0, 1, 0, 0, 6],
        [0, 3, 0, 0, 0, 8, 0, 0, 0],
        [0, 2, 0, 0, 4, 0, 0, 5, 0],
    ]

    # 决策变量：grid[(i, j)] 为第 i 行第 j 列格子的取值，域 [1, 9]。
    grid = {}
    for i in line:
        for j in line:
            grid[(i, j)] = model.new_int_var(1, line_size, "grid %i %i" % (i, j))

    # 约束：每一行的 9 个取值两两互异（AllDifferent on rows）。
    for i in line:
        model.add_all_different(grid[(i, j)] for j in line)

    # 约束：每一列的 9 个取值两两互异（AllDifferent on columns）。
    for j in line:
        model.add_all_different(grid[(i, j)] for i in line)

    # 约束：每个 3×3 宫内的 9 个取值两两互异（AllDifferent on cells）。
    for i in cell:
        for j in cell:
            one_cell = []
            for di in cell:
                for dj in cell:
                    # 收集宫 (i, j) 内的 9 个格子变量。
                    one_cell.append(grid[(i * cell_size + di, j * cell_size + dj)])

            model.add_all_different(one_cell)

    # 约束：固定初始提示数（初始棋盘中非 0 的格子取值不变）。
    for i in line:
        for j in line:
            if initial_grid[i][j]:
                model.add(grid[(i, j)] == initial_grid[i][j])

    # 求解并打印解。
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL:
        for i in line:
            print([int(solver.value(grid[(i, j)])) for j in line])


solve_sudoku()
