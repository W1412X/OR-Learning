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

"""求解一个简单的排班问题。"""

from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解。"""

    def __init__(
        self,
        num_vendors,
        num_hours,
        possible_schedules,
        selected_schedules,
        hours_stat,
        min_vendors,
    ):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__num_vendors = num_vendors
        self.__num_hours = num_hours
        self.__possible_schedules = possible_schedules
        self.__selected_schedules = selected_schedules
        self.__hours_stat = hours_stat
        self.__min_vendors = min_vendors

    def on_solution_callback(self):
        """每找到一个新解时被调用。"""
        self.__solution_count += 1
        print("Solution %i: ", self.__solution_count)
        print("  min vendors:", self.__min_vendors)
        # 打印每个商贩被选中的候选班次
        for i in range(self.__num_vendors):
            print(
                "  - vendor %i: " % i,
                self.__possible_schedules[self.value(self.__selected_schedules[i])],
            )
        print()

        # 打印每个时段的在岗人数统计
        for j in range(self.__num_hours):
            print("  - # workers on day%2i: " % j, end=" ")
            print(self.value(self.__hours_stat[j]), end=" ")
            print()
        print()

    def solution_count(self):
        """返回已找到的解的数量。"""
        return self.__solution_count


def vendor_scheduling_sat() -> None:
    """创建排班模型并求解。"""
    # 创建模型。
    model = cp_model.CpModel()

    #
    # 数据
    #
    num_vendors = 9  # 商贩数量
    num_hours = 10  # 需要排班的时段数量
    num_work_types = 1  # 工作类型数量

    # 每个时段的客流量（需要被覆盖的最低服务能力）
    traffic = [100, 500, 100, 200, 320, 300, 200, 220, 300, 120]
    # 单个商贩每个时段最多能服务的客流量
    max_traffic_per_vendor = 100

    # 候选班次表。最后两列含义为：
    #   班次索引、总工作小时数（按工作类型计）。
    # 索引对分支搜索有用。
    # 前 num_hours 列为各时段是否在岗（1 = 工作，0 = 休息）
    possible_schedules = [
        [1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 8],
        [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 4],
        [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 2, 5],
        [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 3, 4],
        [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 4, 3],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0],
    ]

    num_possible_schedules = len(possible_schedules)
    selected_schedules = []
    vendors_stat = []
    hours_stat = []

    # 辅助数据
    # 每个时段至少需要的商贩数 = 客流量 // 单个商贩的承载力
    min_vendors = [t // max_traffic_per_vendor for t in traffic]
    all_vendors = range(num_vendors)
    all_hours = range(num_hours)

    #
    # 声明变量
    #
    x = {}

    for v in all_vendors:
        tmp = []
        for h in all_hours:
            # 决策变量 x[v,h]：商贩 v 在时段 h 的工作类型（0 表示不在岗）
            x[v, h] = model.new_int_var(0, num_work_types, "x[%i,%i]" % (v, h))
            tmp.append(x[v, h])
        # 决策变量：商贩 v 被选中的候选班次索引
        selected_schedule = model.new_int_var(
            0, num_possible_schedules - 1, "s[%i]" % v
        )
        # 决策变量：商贩 v 的总工作小时数
        hours = model.new_int_var(0, num_hours, "h[%i]" % v)
        selected_schedules.append(selected_schedule)
        vendors_stat.append(hours)
        tmp.append(selected_schedule)
        tmp.append(hours)

        # 表约束：将 (x[v,0..9], s[v], h[v]) 限定为候选班次表中的某一行，
        # 保证"每小时是否在岗 / 所选班次索引 / 总工时"三者一致
        model.add_allowed_assignments(tmp, possible_schedules)

    #
    # 每个时段的统计变量与约束
    #
    for h in all_hours:
        # 统计变量：时段 h 的在岗人数
        workers = model.new_int_var(0, 1000, "workers[%i]" % h)
        model.add(workers == sum(x[v, h] for v in all_vendors))
        hours_stat.append(workers)
        # 覆盖约束：该时段的总服务能力必须不小于客流量
        model.add(workers * max_traffic_per_vendor >= traffic[h])

    #
    # 冗余约束：将 selected_schedules 按索引升序排列
    # （对称性破除，消除等价解、加速搜索）
    #
    for v in range(num_vendors - 1):
        model.add(selected_schedules[v] <= selected_schedules[v + 1])

    # 求解模型。
    solver = cp_model.CpSolver()
    # 枚举所有可行解
    solver.parameters.enumerate_all_solutions = True
    solution_printer = SolutionPrinter(
        num_vendors,
        num_hours,
        possible_schedules,
        selected_schedules,
        hours_stat,
        min_vendors,
    )
    status = solver.solve(model, solution_printer)
    print("Status = %s" % solver.status_name(status))

    print("Statistics")
    print("  - conflicts : %i" % solver.num_conflicts)
    print("  - branches  : %i" % solver.num_branches)
    print("  - wall time : %f s" % solver.wall_time)
    print("  - number of solutions found: %i" % solution_printer.solution_count())


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    vendor_scheduling_sat()


if __name__ == "__main__":
    app.run(main)
