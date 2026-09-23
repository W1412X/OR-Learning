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

"""求解带有"工人组合"约束的指派问题。"""

from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


def solve_assignment():
    """求解带组合约束的指派问题。"""
    # 数据：cost[i][j] 为工人 i 承担任务 j 的成本；sizes[j] 为任务的工作量；
    # total_size_max 为每个工人可承担的最大总工作量。
    cost = [
        [90, 76, 75, 70, 50, 74],
        [35, 85, 55, 65, 48, 101],
        [125, 95, 90, 105, 59, 120],
        [45, 110, 95, 115, 104, 83],
        [60, 105, 80, 75, 59, 62],
        [45, 65, 110, 95, 47, 31],
        [38, 51, 107, 41, 69, 99],
        [47, 85, 57, 71, 92, 77],
        [39, 63, 97, 49, 118, 56],
        [47, 101, 71, 60, 88, 109],
        [17, 39, 103, 64, 61, 92],
        [101, 45, 83, 59, 92, 27],
    ]

    # 组合约束数据：对第 0~3 号工人这"一组"，works 取值组合必须取自下列
    # 允许列表之一（每行是一种允许的 0/1 模式，1 表示该工人被选中）。
    group1 = [
        [0, 0, 1, 1],  # 工人 2, 3
        [0, 1, 0, 1],  # 工人 1, 3
        [0, 1, 1, 0],  # 工人 1, 2
        [1, 1, 0, 0],  # 工人 0, 1
        [1, 0, 1, 0],  # 工人 0, 2
    ]

    group2 = [
        [0, 0, 1, 1],  # 工人 6, 7
        [0, 1, 0, 1],  # 工人 5, 7
        [0, 1, 1, 0],  # 工人 5, 6
        [1, 1, 0, 0],  # 工人 4, 5
        [1, 0, 0, 1],  # 工人 4, 7
    ]

    group3 = [
        [0, 0, 1, 1],  # 工人 10, 11
        [0, 1, 0, 1],  # 工人 9, 11
        [0, 1, 1, 0],  # 工人 9, 10
        [1, 0, 1, 0],  # 工人 8, 10
        [1, 0, 0, 1],  # 工人 8, 11
    ]

    # 任务工作量列表（本例 num_tasks = 6，只使用前 6 个元素）。
    sizes = [10, 7, 3, 12, 15, 4, 11, 5]
    total_size_max = 15
    num_workers = len(cost)
    num_tasks = len(cost[1])
    all_workers = range(num_workers)
    all_tasks = range(num_tasks)

    # 建模。

    model = cp_model.CpModel()
    # 决策变量：selected[i][j] 为 True 表示工人 i 承担任务 j；
    # works[i] 为 True 表示工人 i 参与工作（承担了至少一个任务）。
    selected = [
        [model.new_bool_var(f"x[{i},{j}]") for j in all_tasks] for i in all_workers
    ]
    works = [model.new_bool_var(f"works[{i}]") for i in all_workers]

    # 约束条件

    # 约束（变量关联）：works[i] == max(selected[i])，即工人 i 承担任一任务
    # 则 works[i] 为真（add_max_equality）。
    for i in range(num_workers):
        model.add_max_equality(works[i], selected[i])

    # 约束（任务覆盖）：每个任务至少由一名工人承担。
    for j in all_tasks:
        model.add(sum(selected[i][j] for i in all_workers) >= 1)

    # 约束（工作量上限）：每个工人承担任务的工作量之和不超过 total_size_max。
    for i in all_workers:
        model.add(sum(sizes[j] * selected[i][j] for j in all_tasks) <= total_size_max)

    # 约束（组合约束）：每组 4 名工人的 works 取值组合必须是允许列表之一
    # （add_allowed_assignments；注意各列表中每种模式都恰好选中 2 名工人）。
    model.add_allowed_assignments([works[0], works[1], works[2], works[3]], group1)
    model.add_allowed_assignments([works[4], works[5], works[6], works[7]], group2)
    model.add_allowed_assignments([works[8], works[9], works[10], works[11]], group3)

    # 目标函数：最小化被选中指派的总成本。
    model.minimize(
        sum(selected[i][j] * cost[i][j] for j in all_tasks for i in all_workers)
    )

    # 求解并输出解。
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status == cp_model.OPTIMAL:
        print(f"Total cost = {solver.objective_value}")
        print()
        for i in all_workers:
            for j in all_tasks:
                if solver.boolean_value(selected[i][j]):
                    print(f"Worker {i} assigned to task {j} with Cost = {cost[i][j]}")

        print()

    print(solver.response_stats())


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    solve_assignment()


if __name__ == "__main__":
    app.run(main)
