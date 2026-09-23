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

"""这是 Golomb 尺（Golomb ruler）问题。

该模型的目标是在最小的空间内获得最多的两两不同的距离
（对应雷达干扰测量的抽象），即著名的 Golomb 尺问题。

思路是在一把尺子上放置刻度，使得任意两个刻度之间的
距离（差值）两两互不相同。目标是最小化尺子的长度。
"""

from absl import app
from ortools.constraint_solver import pywrapcp

# 禁用以下告警，因为它对 solver.Add(x == 0) 这类约束属于误报。
# pylint: disable=g-explicit-bool-comparison


def main(_) -> None:
    # 创建求解器。
    solver = pywrapcp.Solver("golomb ruler")

    # 数据：刻度数量；位置上界取 size 的平方
    size = 8
    var_max = size * size
    all_vars = list(range(0, size))

    # 决策变量：第 i 个刻度的位置
    marks = [solver.IntVar(0, var_max, "marks_%d" % i) for i in all_vars]

    # 目标函数：以步长 1 最小化尺长（最后一个刻度的位置）
    objective = solver.Minimize(marks[size - 1], 1)

    # 约束：第一个刻度固定在位置 0
    solver.Add(marks[0] == 0)

    # 构建所有刻度对的差值列表（展开写法以避免 pylint 告警）。
    diffs = []
    for i in range(size - 1):
        for j in range(i + 1, size):
            diffs.append(marks[j] - marks[i])
    # 约束：所有刻度间距两两互不相同（Golomb 尺的核心约束）
    solver.Add(solver.AllDifferent(diffs))

    # 对称性破除：最大刻度间隔必须大于最小刻度间隔
    solver.Add(marks[size - 1] - marks[size - 2] > marks[1] - marks[0])
    # 约束：刻度位置严格递增
    for i in range(size - 2):
        solver.Add(marks[i + 1] > marks[i])

    # 定义需要在解收集器中记录的变量（尺长）。
    solution = solver.Assignment()
    solution.Add(marks[size - 1])
    # 解收集器：收集搜索过程中的所有解
    collector = solver.AllSolutionCollector(solution)

    # 搜索策略：优先选择第一个未绑定的变量，并从小到大赋值。
    solver.Solve(
        solver.Phase(marks, solver.CHOOSE_FIRST_UNBOUND, solver.ASSIGN_MIN_VALUE),
        [objective, collector],
    )
    # 逐个打印收集到的解及其统计信息
    for i in range(0, collector.SolutionCount()):
        obj_value = collector.Value(i, marks[size - 1])
        time = collector.WallTime(i)
        branches = collector.Branches(i)
        failures = collector.Failures(i)
        print(
            "Solution #%i: value = %i, failures = %i, branches = %i,time = %i ms"
            % (i, obj_value, failures, branches, time)
        )
    # 打印整次求解的总统计
    time = solver.WallTime()
    branches = solver.Branches()
    failures = solver.Failures()
    print(
        (
            "Total run : failures = %i, branches = %i, time = %i ms"
            % (failures, branches, time)
        )
    )


if __name__ == "__main__":
    app.run(main)
