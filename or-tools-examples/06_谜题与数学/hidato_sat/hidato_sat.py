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

"""使用 CP-SAT 求解器求解 Hidato 数字蛇填数谜题。"""

from typing import Union
from absl import app
from ortools.sat.colab import visualization
from ortools.sat.python import cp_model


def build_pairs(rows: int, cols: int) -> list[tuple[int, int]]:
    """为连续数字构建"接触对"集合。

    构建允许的位置对集合，使得两个连续数字在网格中相互接触
    （水平、垂直或对角线方向相邻，即八邻域）。

    返回：
      表示数字允许的连续位置的 (位置对) 列表。

    参数：
      rows: 网格的行数
      cols: 网格的列数
    """
    result = []
    # 枚举每个格子 (x, y) 及其八邻域偏移 (dx, dy)，
    # 把所有相互接触的格子对（一维化索引）加入结果列表。
    for x in range(rows):
        for y in range(cols):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if (
                        x + dx >= 0
                        and x + dx < rows
                        and y + dy >= 0
                        and y + dy < cols
                        and (dx != 0 or dy != 0)  # 排除格子自身
                    ):
                        result.append((x * cols + y, (x + dx) * cols + (y + dy)))
    return result


def print_solution(positions: list[int], rows: int, cols: int):
    """打印当前解。"""
    # 创建空盘面。
    board = []
    for _ in range(rows):
        board.append([0] * cols)
    # 用解的取值填充盘面：数字 k+1 位于 positions[k] 对应的格子。
    for k in range(rows * cols):
        position = positions[k]
        board[position // cols][position % cols] = k + 1
    # 打印盘面。
    print("Solution")
    print_matrix(board)


def print_matrix(game: list[list[int]]) -> None:
    """矩阵的美观打印。"""
    rows = len(game)
    cols = len(game[0])
    for i in range(rows):
        line = ""
        for j in range(cols):
            if game[i][j] == 0:
                line += "  ."  # 0 表示空格，用 "." 显示
            else:
                line += f"{game[i][j]:3}"
        print(line)


def build_puzzle(problem: int) -> Union[None, list[list[int]]]:
    """根据题目编号构建谜题。"""
    #
    # 各题盘中 0 表示尚未填入数字的空格。
    #
    #
    puzzle = None
    if problem == 1:
        # 简单题
        puzzle = [[6, 0, 9], [0, 2, 8], [1, 0, 0]]

    elif problem == 2:
        puzzle = [
            [0, 44, 41, 0, 0, 0, 0],
            [0, 43, 0, 28, 29, 0, 0],
            [0, 1, 0, 0, 0, 33, 0],
            [0, 2, 25, 4, 34, 0, 36],
            [49, 16, 0, 23, 0, 0, 0],
            [0, 19, 0, 0, 12, 7, 0],
            [0, 0, 0, 14, 0, 0, 0],
        ]

    elif problem == 3:
        # 取自书籍：
        # Gyora Bededek: 'Hidato: 2000 Pure Logic Puzzles'
        # Problem 1 (Practice 入门练习)
        puzzle = [
            [0, 0, 20, 0, 0],
            [0, 0, 0, 16, 18],
            [22, 0, 15, 0, 0],
            [23, 0, 1, 14, 11],
            [0, 25, 0, 0, 12],
        ]

    elif problem == 4:
        # problem 2 (Practice 入门练习)
        puzzle = [
            [0, 0, 0, 0, 14],
            [0, 18, 12, 0, 0],
            [0, 0, 17, 4, 5],
            [0, 0, 7, 0, 0],
            [9, 8, 25, 1, 0],
        ]

    elif problem == 5:
        # problem 3 (Beginner 初级)
        puzzle = [
            [0, 26, 0, 0, 0, 18],
            [0, 0, 27, 0, 0, 19],
            [31, 23, 0, 0, 14, 0],
            [0, 33, 8, 0, 15, 1],
            [0, 0, 0, 5, 0, 0],
            [35, 36, 0, 10, 0, 0],
        ]
    elif problem == 6:
        # Problem 15 (Intermediate 中级)
        puzzle = [
            [64, 0, 0, 0, 0, 0, 0, 0],
            [1, 63, 0, 59, 15, 57, 53, 0],
            [0, 4, 0, 14, 0, 0, 0, 0],
            [3, 0, 11, 0, 20, 19, 0, 50],
            [0, 0, 0, 0, 22, 0, 48, 40],
            [9, 0, 0, 32, 23, 0, 0, 41],
            [27, 0, 0, 0, 36, 0, 46, 0],
            [28, 30, 0, 35, 0, 0, 0, 0],
        ]
    return puzzle


def solve_hidato(puzzle: list[list[int]], index: int) -> None:
    """求解给定的 Hidato 谜题盘面。"""
    # 创建模型。
    model = cp_model.CpModel()

    r = len(puzzle)
    c = len(puzzle[0])
    if not visualization.RunFromIPython():
        print("")
        print(f"----- Solving problem {index} -----")
        print("")
        print(f"Initial game ({r} x {c})")
        print_matrix(puzzle)

    #
    # 声明变量。
    #
    # positions[i] 表示数字 i+1 所在格子的位置索引（0 到 r*c-1，按行一维化）。
    positions = [model.new_int_var(0, r * c - 1, f"p[{i}]") for i in range(r * c)]

    #
    # 约束。
    #
    # 所有数字必须占据互不相同的格子。
    model.add_all_different(positions)

    #
    # 填入已知线索。
    #
    # 若盘面 (i, j) 处已有数字 n，则数字 n 必须放在该格子上。
    for i in range(r):
        for j in range(c):
            if puzzle[i][j] > 0:
                model.add(positions[puzzle[i][j] - 1] == i * c + j)

    # 相邻两个数字在网格中必须相互接触。
    # 这里用允许赋值约束（表约束）来建模。
    close_tuples = build_pairs(r, c)
    for k in range(0, r * c - 1):
        # 限制 (positions[k], positions[k+1]) 的取值组合必须在接触对集合内。
        model.add_allowed_assignments([positions[k], positions[k + 1]], close_tuples)

    #
    # 求解与结果输出。
    #

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status == cp_model.OPTIMAL:
        if visualization.RunFromIPython():
            # 在 notebook 环境中用 SVG 图形化展示解：
            # 线索格子上色为浅绿色，填入数字上色为白色。
            output = visualization.SvgWrapper(10, r, 40.0)
            for i, var in enumerate(positions):
                val = solver.value(var)
                x = val % c
                y = val // c
                color = "white" if puzzle[y][x] == 0 else "lightgreen"
                output.AddRectangle(x, r - y - 1, 1, 1, color, "black", str(i + 1))

            output.AddTitle(f"Puzzle {index} solved in {solver.wall_time:.2f} s")
            output.Display()
        else:
            # 终端环境下打印文本盘面与求解统计。
            print_solution(
                [solver.value(x) for x in positions],
                r,
                c,
            )
            print(solver.response_stats())


def main(_):
    # 依次求解内置的 6 道题目（编号 1 到 6）。
    for pb in range(1, 7):
        solve_hidato(build_puzzle(pb), pb)


if __name__ == "__main__":
    app.run(main)
