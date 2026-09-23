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

"""求解五格骨牌铺砌问题的示例。

给定 n 个互不相同的五格骨牌组成的子集，问题是用它们铺满一个
大小为 5 x n 的矩形。该问题被归约为精确覆盖问题，并编码为
线性布尔问题。

本问题来自游戏 Katamino：
http://boardgamegeek.com/boardgame/6931/katamino

本示例还融合了以下页面的建议：
https://web.ma.utexas.edu/users/smmg/archive/1997/radin.html
"""

from collections.abc import Sequence
from typing import Dict, List

from absl import app
from absl import flags

from ortools.sat.python import cp_model


# 命令行参数：传给 SAT 求解器的参数（文本格式，逗号分隔）。
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16,log_search_progress:false,max_time_in_seconds:45",
    "Sat solver parameters.",
)

# 命令行参数：要考虑的骨牌字母子集。
_PIECES = flags.DEFINE_string(
    "pieces", "FILNPTUVWXYZ", "The subset of pieces to consider."
)

# 命令行参数：盒子的高度。
_HEIGHT = flags.DEFINE_integer("height", 5, "The height of the box.")


def is_one(mask: List[List[int]], x: int, y: int, orientation: int) -> bool:
    """若指定朝向的骨牌在位置 [i][j] 处为 1（实格），则返回 True。

    orientation 的 3 个比特位分别表示：转置、沿 x 轴对称、
    沿 y 轴对称。

    Args:
      mask: 骨牌的形状矩阵。
      x: 位置。
      y: 位置。
      orientation: 0 到 7 之间的整数。
    """
    # 比特 0：转置（交换 x、y）。
    if orientation & 1:
        tmp: int = x
        x = y
        y = tmp
    # 比特 1：沿 x 轴方向镜像。
    if orientation & 2:
        x = len(mask[0]) - 1 - x
    # 比特 2：沿 y 轴方向镜像。
    if orientation & 4:
        y = len(mask) - 1 - y
    return mask[y][x] == 1


def get_height(mask: List[List[int]], orientation: int) -> int:
    """返回骨牌在指定朝向下的高度（转置时行列互换）。"""
    if orientation & 1:
        return len(mask[0])
    return len(mask)


def get_width(mask: List[List[int]], orientation: int) -> int:
    """返回骨牌在指定朝向下的宽度（转置时行列互换）。"""
    if orientation & 1:
        return len(mask)
    return len(mask[0])


def orientation_is_redundant(mask: List[List[int]], orientation: int) -> bool:
    """检查当前旋转后的形状是否与之前某个朝向完全相同（对称去重）。"""
    size_i: int = get_width(mask, orientation)
    size_j: int = get_height(mask, orientation)
    for o in range(orientation):
        # 宽高不同则形状必然不同，直接跳过。
        if size_i != get_width(mask, o):
            continue
        if size_j != get_height(mask, o):
            continue

        is_the_same: bool = True
        # 逐格比较两个朝向的形状是否一致。
        for k in range(size_i):
            if not is_the_same:
                break
            for l in range(size_j):
                if not is_the_same:
                    break
                if is_one(mask, k, l, orientation) != is_one(mask, k, l, o):
                    is_the_same = False
        if is_the_same:
            return True
    return False


def generate_and_solve_problem(pieces: Dict[str, List[List[int]]]) -> None:
    """求解五格骨牌铺砌问题。"""
    box_height = _HEIGHT.value
    # 盒子宽度由总面积（每块骨牌 5 格）除以高度得到。
    box_width = 5 * len(pieces) // box_height
    print(f"Box has dimension {box_height} * {box_width}")

    model = cp_model.CpModel()
    # position_to_variables[j][i]：覆盖格子（行 j, 列 i）的所有"摆放变量"。
    position_to_variables: List[List[List[cp_model.IntVar]]] = [
        [[] for _ in range(box_width)] for _ in range(box_height)
    ]

    for name, mask in pieces.items():
        # 收集该骨牌所有合法摆放（朝向 + 位置）的布尔变量。
        all_position_variables = []
        for orientation in range(8):
            # 跳过与已有朝向重复的冗余朝向（对称去重）。
            if orientation_is_redundant(mask, orientation):
                continue
            piece_width = get_width(mask, orientation)
            piece_height = get_height(mask, orientation)
            # 枚举骨牌左上角在盒子中的所有可行位置。
            for i in range(box_width - piece_width + 1):
                for j in range(box_height - piece_height + 1):
                    # 决策变量 v：该骨牌以该朝向摆放在该位置（变量名即骨牌字母）。
                    v = model.new_bool_var(name)
                    all_position_variables.append(v)
                    # 把 v 登记到它覆盖的每个格子上。
                    for k in range(piece_width):
                        for l in range(piece_height):
                            if is_one(mask, k, l, orientation):
                                position_to_variables[j + l][i + k].append(v)

        # 约束 1：每块骨牌必须恰好选择一种摆放方式。
        model.add_exactly_one(all_position_variables)

    # 约束 2（精确覆盖）：盒子的每个格子必须恰好被一块骨牌覆盖
    # （既不能空着，也不能重叠）。
    for one_column in position_to_variables:
        for all_pieces_in_one_position in one_column:
            model.add_exactly_one(all_pieces_in_one_position)

    # 求解模型。
    solver = cp_model.CpSolver()
    # 解析命令行传入的求解器参数（如线程数、时限等）。
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    status = solver.solve(model)

    print(
        f"Problem {_PIECES.value} box {box_height}*{box_width} solved in"
        f" {solver.wall_time}s with status {solver.status_name(status)}"
    )

    # 打印解：逐行扫描格子，输出覆盖该格子的骨牌字母。
    if status == cp_model.OPTIMAL:
        for y in range(box_height):
            line = ""
            for x in range(box_width):
                for v in position_to_variables[y][x]:
                    if solver.BooleanValue(v):
                        line += v.name
                        break
            print(line)


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    # 骨牌形状用矩阵存储，格式为 mask[height][width]，1 表示实格。
    pieces: Dict[str, List[List[int]]] = {
        "F": [[0, 1, 1], [1, 1, 0], [0, 1, 0]],
        "I": [[1, 1, 1, 1, 1]],
        "L": [[1, 1, 1, 1], [1, 0, 0, 0]],
        "N": [[1, 1, 1, 0], [0, 0, 1, 1]],
        "P": [[1, 1, 1], [1, 1, 0]],
        "T": [[1, 1, 1], [0, 1, 0], [0, 1, 0]],
        "U": [[1, 0, 1], [1, 1, 1]],
        "V": [[1, 0, 0], [1, 0, 0], [1, 1, 1]],
        "W": [[1, 0, 0], [1, 1, 0], [0, 1, 1]],
        "X": [[0, 1, 0], [1, 1, 1], [0, 1, 0]],
        "Y": [[1, 1, 1, 1], [0, 1, 0, 0]],
        "Z": [[1, 1, 0], [0, 1, 0], [0, 1, 1]],
    }
    # 按命令行参数筛选骨牌，并校验字母是否有效。
    selected_pieces: Dict[str, List[List[int]]] = {}
    for p in _PIECES.value:
        if p not in pieces:
            print(f"Piece {p} not found in the list of pieces")
            return
        selected_pieces[p] = pieces[p]
    # 校验：高度必须整除总面积（5 * 骨牌数）。
    if (len(selected_pieces) * 5) % _HEIGHT.value != 0:
        print(
            f"The height {_HEIGHT.value} does not divide the total area"
            f" {5 * len(selected_pieces)}"
        )
        return
    # 校验：盒子的高度和宽度都必须放得下骨牌（不小于 3）。
    if _HEIGHT.value < 3 or 5 * len(selected_pieces) // _HEIGHT.value < 3:
        print(f"The height {_HEIGHT.value} is not compatible with the pieces.")
        return

    generate_and_solve_problem(selected_pieces)


if __name__ == "__main__":
    app.run(main)
