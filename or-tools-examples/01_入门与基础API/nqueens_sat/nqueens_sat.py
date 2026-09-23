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

"""N 皇后问题的 CP-SAT 模型。"""

import time

from absl import app
from absl import flags

from ortools.sat.python import cp_model

# 命令行参数：皇后数量，默认为 8（即 8x8 棋盘）。
_SIZE = flags.DEFINE_integer("size", 8, "Number of queens.")


class NQueenSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解的回调类：每找到一个解就输出一次棋盘。"""

    def __init__(self, queens: list[cp_model.IntVar]):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._queens = queens
        self._solution_count = 0
        self._start_time = time.time()

    @property
    def solution_count(self) -> int:
        return self._solution_count

    def on_solution_callback(self) -> None:
        current_time = time.time()
        print(
            f"Solution{self._solution_count}, time ="
            f" {current_time - self._start_time} s"
        )
        self._solution_count += 1

        all_queens = range(len(self._queens))
        for i in all_queens:
            for j in all_queens:
                if self.value(self._queens[j]) == i:
                    # 第 j 列、第 i 行的位置上有一个皇后。
                    print("Q", end=" ")
                else:
                    print("_", end=" ")
            print()
        print()


def main(_):
    board_size = _SIZE.value

    ### 创建求解模型。
    model = cp_model.CpModel()

    ### 创建决策变量。
    # 数组下标是列号，变量的值是该列皇后所在的行号。
    # 这样建模天然保证"每列恰好一个皇后"。
    queens = [
        model.new_int_var(0, board_size - 1, "x%i" % i) for i in range(board_size)
    ]

    ### 创建约束条件。

    # 由于每个皇后的列号（数组下标）互不相同，列与列之间天然不会冲突，
    # 因此只需对行号添加"两两不同"（all different）约束即可保证不同行。
    model.add_all_different(queens)

    # 任意两个皇后不能位于同一条对角线上。
    # 同一条对角线上的格子满足：行+列 为常数（或 行-列 为常数），
    # 因此为每个皇后构造这两个辅助变量，再分别施加全不同约束。
    diag1 = []
    diag2 = []
    for i in range(board_size):
        q1 = model.new_int_var(0, 2 * board_size, "diag1_%i" % i)
        q2 = model.new_int_var(-board_size, board_size, "diag2_%i" % i)
        diag1.append(q1)
        diag2.append(q2)
        # q1 = 行号 + 列号；q2 = 行号 - 列号。
        model.add(q1 == queens[i] + i)
        model.add(q2 == queens[i] - i)
    # 两两不同 => 任意两个皇后不同处一条对角线。
    model.add_all_different(diag1)
    model.add_all_different(diag2)

    ### 求解模型。
    solver = cp_model.CpSolver()
    solution_printer = NQueenSolutionPrinter(queens)
    # 枚举全部可行解（而不是只求出一个解）。
    solver.parameters.enumerate_all_solutions = True
    # 求解：每找到一个解就触发一次 solution_printer 回调。
    solver.solve(model, solution_printer)

    print()
    print("Statistics")
    print("  - conflicts       : %i" % solver.num_conflicts)
    print("  - branches        : %i" % solver.num_branches)
    print("  - wall time       : %f s" % solver.wall_time)
    print("  - solutions found : %i" % solution_printer.solution_count)


if __name__ == "__main__":
    app.run(main)
