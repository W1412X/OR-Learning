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

"""把任务与工人分配到组中，最小化 sum(cost) / 工人数（人均成本）。"""

from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


class ObjectivePrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解。"""

    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0

    def on_solution_callback(self):
        print(
            "Solution %i, time = %f s, objective = %i"
            % (self.__solution_count, self.wall_time, self.objective_value)
        )
        self.__solution_count += 1


def tasks_and_workers_assignment_sat() -> None:
    """求解该分配问题。"""
    model = cp_model.CpModel()

    # CP-SAT 求解器只支持整数。
    # 每个任务的成本。
    task_cost = [24, 10, 7, 2, 11, 16, 1, 13, 9, 27]
    num_tasks = len(task_cost)
    num_workers = 3
    num_groups = 2
    all_workers = range(num_workers)
    all_groups = range(num_groups)
    all_tasks = range(num_tasks)

    # 变量

    ## x_ij = 1 表示工人 i 被分配到组 j。
    x = {}
    for i in all_workers:
        for j in all_groups:
            x[i, j] = model.new_bool_var("x[%i,%i]" % (i, j))

    ## y_kj = 1 表示任务 k 被分配到组 j。
    y = {}
    for k in all_tasks:
        for j in all_groups:
            y[k, j] = model.new_bool_var("x[%i,%i]" % (k, j))

    # 约束

    # 每个任务 k 恰好被分配到一个组。
    for k in all_tasks:
        model.add(sum(y[k, j] for j in all_groups) == 1)

    # 每个工人 i 恰好被分配到一个组。
    for i in all_workers:
        model.add(sum(x[i, j] for j in all_groups) == 1)

    # 各组的成本。
    sum_of_costs = sum(task_cost)
    averages = []
    num_workers_in_group = []
    scaled_sum_of_costs_in_group = []
    # 引入缩放因子以处理浮点平均数问题。
    scaling = 1000
    for j in all_groups:
        # n：组 j 的工人数（至少 1 人，保证除法有意义）。
        n = model.new_int_var(1, num_workers, "num_workers_in_group_%i" % j)
        model.add(n == sum(x[i, j] for i in all_workers))
        # c：组 j 的成本总和（乘以 scaling 保持整数）。
        c = model.new_int_var(0, sum_of_costs * scaling, "sum_of_costs_of_group_%i" % j)
        model.add(c == sum(y[k, j] * task_cost[k] * scaling for k in all_tasks))
        # a：组 j 的人均成本（c / n，整数除法约束）。
        a = model.new_int_var(0, sum_of_costs * scaling, "average_cost_of_group_%i" % j)
        model.add_division_equality(a, c, n)

        averages.append(a)
        num_workers_in_group.append(n)
        scaled_sum_of_costs_in_group.append(c)

    # 约束：所有工人都被分配（各组人数之和等于总人数）。
    model.add(sum(num_workers_in_group) == num_workers)

    # 目标函数。
    # obj：各组人均成本的最大值（min-max 目标）。
    obj = model.new_int_var(0, sum_of_costs * scaling, "obj")
    model.add_max_equality(obj, averages)
    model.minimize(obj)

    # 求解并打印解。
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60 * 60 * 2
    objective_printer = ObjectivePrinter()
    status = solver.solve(model, objective_printer)
    print(solver.response_stats())

    # 若达到最优，按组打印工人、任务与成本明细。
    if status == cp_model.OPTIMAL:
        for j in all_groups:
            print("Group %i" % j)
            for i in all_workers:
                if solver.boolean_value(x[i, j]):
                    print("  - worker %i" % i)
            for k in all_tasks:
                if solver.boolean_value(y[k, j]):
                    print("  - task %i with cost %i" % (k, task_cost[k]))
            print(
                "  - sum_of_costs = %i"
                % (solver.value(scaled_sum_of_costs_in_group[j]) // scaling)
            )
            print("  - average cost = %f" % (solver.value(averages[j]) * 1.0 / scaling))


tasks_and_workers_assignment_sat()


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    tasks_and_workers_assignment_sat()


if __name__ == "__main__":
    app.run(main)
