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

"""分组平衡问题：把物品分成大小相同的若干组。

每个物品有颜色和取值，希望每组取值之和尽量接近所有物品取值的平均值。
此外，如果某种颜色出现在某组中，那么该组必须至少包含 k 个该颜色的物品。
"""

from typing import Dict, Sequence

from absl import app

from ortools.sat.python import cp_model


# 定义解打印回调。
class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解（搜索过程中每找到一个解就打印一次）。"""

    def __init__(self, values, colors, all_groups, all_items, item_in_group):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__values = values
        self.__colors = colors
        self.__all_groups = all_groups
        self.__all_items = all_items
        self.__item_in_group = item_in_group

    def on_solution_callback(self):
        print(f"Solution {self.__solution_count}")
        self.__solution_count += 1

        print(f"  objective value = {self.objective_value}")
        groups = {}
        sums = {}
        for g in self.__all_groups:
            groups[g] = []
            sums[g] = 0
            for item in self.__all_items:
                if self.boolean_value(self.__item_in_group[(item, g)]):
                    groups[g].append(item)
                    sums[g] += self.__values[item]

        for g in self.__all_groups:
            group = groups[g]
            print(f"group {g}: sum = {sums[g]:0.2f} [", end="")
            for item in group:
                value = self.__values[item]
                color = self.__colors[item]
                print(f" ({item}, {value}, {color})", end="")
            print("]")


def main(argv: Sequence[str]) -> None:
    """求解分组平衡问题。"""

    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    # 数据：num_groups 组数、num_items 物品数、num_colors 颜色数、
    # min_items_of_same_color_per_group 为每组中同色物品的最少数量。
    num_groups = 10
    num_items = 100
    num_colors = 3
    min_items_of_same_color_per_group = 4

    all_groups = range(num_groups)
    all_items = range(num_items)
    all_colors = range(num_colors)

    # 每个物品的取值。
    values = [1 + i + (i * i // 200) for i in all_items]
    # 每个物品的颜色（简单取模生成）。
    colors = [i % num_colors for i in all_items]

    sum_of_values = sum(values)
    average_sum_per_group = sum_of_values // num_groups

    num_items_per_group = num_items // num_groups

    # 按颜色收集物品：items_per_color[c] 为颜色为 c 的物品编号列表。
    items_per_color: Dict[int, list[int]] = {}
    for color in all_colors:
        items_per_color[color] = []
        for i in all_items:
            if colors[i] == color:
                items_per_color[color].append(i)

    print(
        f"Model has {num_items} items, {num_groups} groups, and" f" {num_colors} colors"
    )
    print(f"  average sum per group = {average_sum_per_group}")

    # 建模。

    model = cp_model.CpModel()

    # 决策变量：item_in_group[(i, g)] 为 True 表示物品 i 被分到第 g 组。
    item_in_group = {}
    for i in all_items:
        for g in all_groups:
            item_in_group[(i, g)] = model.new_bool_var(f"item {i} in group {g}")

    # 约束：每组物品数相同（均为 num_items_per_group = num_items // num_groups）。
    for g in all_groups:
        model.add(sum(item_in_group[(i, g)] for i in all_items) == num_items_per_group)

    # 约束：每个物品恰好属于一个组。
    for i in all_items:
        model.add(sum(item_in_group[(i, g)] for g in all_groups) == 1)

    # 决策变量：e（epsilon）表示组内取值之和允许偏离平均值的幅度（全局统一）。
    e = model.new_int_var(0, 550, "epsilon")

    # 约束：每组的取值之和必须落在 [平均值 − e, 平均值 + e] 区间内。
    for g in all_groups:
        model.add(
            sum(item_in_group[(i, g)] * values[i] for i in all_items)
            <= average_sum_per_group + e
        )
        model.add(
            sum(item_in_group[(i, g)] * values[i] for i in all_items)
            >= average_sum_per_group - e
        )

    # 决策变量：color_in_group[(c, g)] 为 True 表示颜色 c 出现在第 g 组中。
    color_in_group = {}
    for g in all_groups:
        for c in all_colors:
            color_in_group[(c, g)] = model.new_bool_var(f"color {c} is in group {g}")

    # 约束（蕴含）：物品在组中 ⇒ 该物品的颜色也"在"该组中（add_implication）。
    for i in all_items:
        for g in all_groups:
            model.add_implication(item_in_group[(i, g)], color_in_group[(colors[i], g)])

    # 约束：若颜色 c 在组 g 中，则组 g 必须包含至少
    # min_items_of_same_color_per_group 个颜色 c 的物品（only_enforce_if 条件约束）。
    for c in all_colors:
        for g in all_groups:
            literal = color_in_group[(c, g)]
            model.add(
                sum(item_in_group[(i, g)] for i in items_per_color[c])
                >= min_items_of_same_color_per_group
            ).only_enforce_if(literal)

    # 推导：每组最多可能出现的颜色数。
    max_color = num_items_per_group // min_items_of_same_color_per_group

    # 冗余约束（不改变可行解集合，但能显著加快求解）：每组颜色数不超过 max_color。
    if max_color < num_colors:
        for g in all_groups:
            model.add(sum(color_in_group[(c, g)] for c in all_colors) <= max_color)

    # 目标函数：最小化 epsilon（让各组取值之和尽量贴近平均值）。
    model.minimize(e)

    solver = cp_model.CpSolver()
    # solver.parameters.log_search_progress = True  # 取消注释可查看求解日志。
    # 使用 16 个并行搜索线程。
    solver.parameters.num_workers = 16
    solution_printer = SolutionPrinter(
        values, colors, all_groups, all_items, item_in_group
    )
    # 求解模型；solution_printer 会在搜索过程中打印中间解。
    status = solver.solve(model, solution_printer)

    if status == cp_model.OPTIMAL:
        print(f"Optimal epsilon: {solver.objective_value}")
        print(solver.response_stats())
    else:
        print("No solution found")


if __name__ == "__main__":
    app.run(main)
