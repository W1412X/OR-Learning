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

"""寻找最优的婚礼座位安排表。

来自
Meghan L. Bellows and J. D. Luc Peterson
"Finding an optimal seating chart for a wedding"
http://www.improbable.com/news/2012/Optimal-seating-chart.pdf
http://www.improbable.com/2012/02/12/finding-an-optimal-seating-chart-for-a-wedding

每年，数以百万计的新娘（更不用说她们的母亲、未来的婆婆，偶尔还有新郎）
都要为婚礼筹备过程中最令人头疼的任务之一而绞尽脑汁：座位安排表。
宾客的回执已经收到，宴会厅已经订好，菜单也选好了。你以为最难的部分
已经结束，但其实最大的麻烦才刚刚开始。为了让这一过程更轻松，我们
提出一个为座位安排问题建模的数学表述。求解该模型即可得到宾客在
各桌的最优安排。至少，它可以作为一个起点，并有望减少压力与争执。

改编自
https://github.com/google/or-tools/blob/master/examples/csharp/wedding_optimal_chart.cs
"""

import time
from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


class WeddingChartPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解。"""

    def __init__(self, seats, names, num_tables, num_guests):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__start_time = time.time()
        self.__seats = seats
        self.__names = names
        self.__num_tables = num_tables
        self.__num_guests = num_guests

    def on_solution_callback(self):
        """每找到一个新解时被调用：打印目标值与每桌宾客名单。"""
        current_time = time.time()
        objective = self.objective_value
        print(
            "Solution %i, time = %f s, objective = %i"
            % (self.__solution_count, current_time - self.__start_time, objective)
        )
        self.__solution_count += 1

        # 逐桌打印坐在该桌上的宾客
        for t in range(self.__num_tables):
            print("Table %d: " % t)
            for g in range(self.__num_guests):
                if self.value(self.__seats[(t, g)]):
                    print("  " + self.__names[g])

    def num_solutions(self) -> int:
        return self.__solution_count


def build_data():
    """构建数据模型。"""
    # 简单问题（来自论文）
    # num_tables = 2
    # table_capacity = 10
    # min_known_neighbors = 1

    # 稍难一点的问题（同样来自论文）
    num_tables = 5
    table_capacity = 4
    min_known_neighbors = 1

    # 关系矩阵：谁认识谁，以及关系的强弱
    connections = [
        [1, 50, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [50, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 50, 1, 1, 1, 1, 10, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 50, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 50, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 50, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1, 1, 50, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1, 50, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 10, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 50, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 50, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
    ]

    # 宾客名单。B：新娘方，G：新郎方
    names = [
        "Deb (B)",
        "John (B)",
        "Martha (B)",
        "Travis (B)",
        "Allan (B)",
        "Lois (B)",
        "Jayne (B)",
        "Brad (B)",
        "Abby (B)",
        "Mary Helen (G)",
        "Lee (G)",
        "Annika (G)",
        "Carl (G)",
        "Colin (G)",
        "Shirley (G)",
        "DeAnn (G)",
        "Lori (G)",
    ]
    return num_tables, table_capacity, min_known_neighbors, connections, names


def solve_with_discrete_model() -> None:
    """离散（布尔变量）建模方式。"""
    num_tables, table_capacity, min_known_neighbors, connections, names = build_data()

    num_guests = len(connections)

    all_tables = range(num_tables)
    all_guests = range(num_guests)

    # 创建 CP 模型。
    model = cp_model.CpModel()

    #
    # 决策变量
    #
    # seats[(t, g)]：宾客 g 是否坐在桌 t
    seats = {}
    for t in all_tables:
        for g in all_guests:
            seats[(t, g)] = model.new_bool_var("guest %i seats on table %i" % (g, t))

    # colocated[(g1, g2)]：宾客 g1 与 g2 是否同桌
    colocated = {}
    for g1 in range(num_guests - 1):
        for g2 in range(g1 + 1, num_guests):
            colocated[(g1, g2)] = model.new_bool_var(
                "guest %i seats with guest %i" % (g1, g2)
            )

    # same_table[(g1, g2, t)]：宾客 g1 与 g2 是否同在桌 t
    same_table = {}
    for g1 in range(num_guests - 1):
        for g2 in range(g1 + 1, num_guests):
            for t in all_tables:
                same_table[(g1, g2, t)] = model.new_bool_var(
                    "guest %i seats with guest %i on table %i" % (g1, g2, t)
                )

    # 目标函数：最大化所有同桌宾客对的关系强度之和
    model.maximize(
        sum(
            connections[g1][g2] * colocated[g1, g2]
            for g1 in range(num_guests - 1)
            for g2 in range(g1 + 1, num_guests)
            if connections[g1][g2] > 0
        )
    )

    #
    # 约束条件
    #

    # 每个人恰好坐一张桌子。
    for g in all_guests:
        model.add(sum(seats[(t, g)] for t in all_tables) == 1)

    # 每张桌子有最大容量限制。
    for t in all_tables:
        model.add(sum(seats[(t, g)] for g in all_guests) <= table_capacity)

    # 将 colocated 与 seats 关联起来
    for g1 in range(num_guests - 1):
        for g2 in range(g1 + 1, num_guests):
            for t in all_tables:
                # 关联 same_table 与 seats：
                # 若两人都在桌 t，则 same_table 必须为真
                model.add_bool_or(
                    [
                        ~seats[(t, g1)],
                        ~seats[(t, g2)],
                        same_table[(g1, g2, t)],
                    ]
                )
                # 反向蕴含：same_table 为真则两人都在桌 t
                model.add_implication(same_table[(g1, g2, t)], seats[(t, g1)])
                model.add_implication(same_table[(g1, g2, t)], seats[(t, g2)])

            # 关联 colocated 与 same_table：同桌 <=> 恰好同在某一张桌
            model.add(
                sum(same_table[(g1, g2, t)] for t in all_tables) == colocated[(g1, g2)]
            )

    # 最少认识邻居规则：每位宾客至少与 min_known_neighbors 位认识的人同桌。
    for g in all_guests:
        model.add(
            sum(
                same_table[(g, g2, t)]
                for g2 in range(g + 1, num_guests)
                for t in all_tables
                if connections[g][g2] > 0
            )
            + sum(
                same_table[(g1, g, t)]
                for g1 in range(g)
                for t in all_tables
                if connections[g1][g] > 0
            )
            >= min_known_neighbors
        )

    # 对称性破除：第一位宾客固定坐在第一张桌。
    model.add(seats[(0, 0)] == 1)

    ### 求解模型。
    solver = cp_model.CpSolver()
    solution_printer = WeddingChartPrinter(seats, names, num_tables, num_guests)
    solver.solve(model, solution_printer)

    print("Statistics")
    print("  - conflicts    : %i" % solver.num_conflicts)
    print("  - branches     : %i" % solver.num_branches)
    print("  - wall time    : %f s" % solver.wall_time)
    print("  - num solutions: %i" % solution_printer.num_solutions())


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    solve_with_discrete_model()


if __name__ == "__main__":
    app.run(main)
