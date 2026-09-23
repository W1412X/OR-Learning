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

"""在 4x4 矩阵上测试线性求和指派问题。

示例取自：
http://www.ee.oulu.fi/~mpa/matreng/eem1_2-1.htm
并对 kCost[0][1] 做了修改，使最优解唯一。
"""

from typing import Sequence
from absl import app
from ortools.graph.python import linear_sum_assignment


def run_assignment_on_4x4_matrix():
    """在 4x4 矩阵上测试线性求和指派问题。"""
    # 源（左节点）数量：4 个（可理解为 4 名工人）
    num_sources = 4
    # 目标（右节点）数量：4 个（可理解为 4 项任务）
    num_targets = 4
    # 4x4 成本矩阵：cost[i][j] 表示源 i 指派给目标 j 的成本
    cost = [
        [90, 76, 75, 80],
        [35, 85, 55, 65],
        [125, 95, 90, 105],
        [45, 110, 95, 115],
    ]
    # 预先计算的已知最优总成本：0->3, 1->2, 2->1, 3->0，用于验证求解结果
    expected_cost = cost[0][3] + cost[1][2] + cost[2][1] + cost[3][0]

    # 创建线性求和指派（最小权完美匹配）求解器
    assignment = linear_sum_assignment.SimpleLinearSumAssignment()
    # 为每一对（源, 目标）添加一条带成本的弧，共 4*4=16 条
    for source in range(0, num_sources):
        for target in range(0, num_targets):
            assignment.add_arc_with_cost(source, target, cost[source][target])

    # 求解：在所有完美匹配中寻找总成本最小的一个
    solve_status = assignment.solve()
    if solve_status == assignment.OPTIMAL:
        # 找到最优完美匹配，打印总成本与逐条指派结果
        print("Successful solve.")
        print("Total cost", assignment.optimal_cost(), "/", expected_cost)
        for i in range(0, assignment.num_nodes()):
            # right_mate(i) 返回左节点 i 匹配到的右节点；assignment_cost(i) 返回该弧的成本
            print(
                "Left node %d assigned to right node %d with cost %d."
                % (i, assignment.right_mate(i), assignment.assignment_cost(i))
            )
    elif solve_status == assignment.INFEASIBLE:
        # 不存在任何完美匹配（可行指派）
        print("No perfect matching exists.")
    elif solve_status == assignment.POSSIBLE_OVERFLOW:
        # 某些输入成本过大，可能导致整数溢出
        print("Some input costs are too large and may cause an integer overflow.")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    run_assignment_on_4x4_matrix()


if __name__ == "__main__":
    app.run(main)
