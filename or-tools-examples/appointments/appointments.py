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

# [START program]（示例程序开始标记）
"""预约（安装工单）排程选择。

本模块最大化一支安装队伍能够完成的预约（安装工单）数量，
同时使各类型预约的占比尽量接近理想比例。
"""

# 注意：重载的 sum() 会与 pytype 冲突。

# [START import]（导入依赖）
from absl import app
from absl import flags
from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model

# [END import]（导入结束）

# absl 命令行参数定义：
#   load_min      默认 480：每个工人一天的最小工作负载（分钟）
#   load_max      默认 540：每个工人一天的最大工作负载（分钟）
#   commute_time  默认 30：每次预约之间需要的通勤时间（分钟）
#   num_workers   默认 98：可用的最大工人数（即选用的日程组合总数）
_LOAD_MIN = flags.DEFINE_integer("load_min", 480, "Minimum load in minutes.")
_LOAD_MAX = flags.DEFINE_integer("load_max", 540, "Maximum load in minutes.")
_COMMUTE_TIME = flags.DEFINE_integer("commute_time", 30, "Commute time in minutes.")
_NUM_WORKERS = flags.DEFINE_integer("num_workers", 98, "Maximum number of workers.")


class AllSolutionCollector(cp_model.CpSolverSolutionCallback):
    """把求解过程中出现的所有解都保存下来。"""

    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__collect = []

    def on_solution_callback(self) -> None:
        """收集一个新的组合。"""
        combination = [self.value(v) for v in self.__variables]
        self.__collect.append(combination)

    def combinations(self) -> list[list[int]]:
        """返回所有已收集的组合。"""
        return self.__collect


def enumerate_all_knapsacks_with_repetition(
    item_sizes: list[int], total_size_min: int, total_size_max: int
) -> list[list[int]]:
    """枚举总大小落在给定区间内的所有"可重复背包"组合。

    Args:
      item_sizes: 整数列表，item_sizes[i] 表示第 i 种物品的大小。
      total_size_min: 整数，总大小的下限。
      total_size_max: 整数，总大小的上限。

    Returns:
      所有总大小落在闭区间 [total_size_min, total_size_max] 内的背包组合列表。
      每个背包表示为列表 [#item0, #item1, ...]，其中 #itemK 是非负整数：
      第 K 种物品放入背包的个数。
    """
    model = cp_model.CpModel()
    # 决策变量：variables[i] 表示第 i 种物品被选中的个数，
    # 上界为 total_size_max // size（个数不可能超过总大小上限除以单件大小）。
    variables = [
        model.new_int_var(0, total_size_max // size, "") for size in item_sizes
    ]
    # 负载（总大小）= 各物品个数 × 单件大小的加权和。
    load = sum(variables[i] * size for i, size in enumerate(item_sizes))
    # 约束：总大小必须落在 [total_size_min, total_size_max] 区间内。
    model.add_linear_constraint(load, total_size_min, total_size_max)

    solver = cp_model.CpSolver()
    solution_collector = AllSolutionCollector(variables)
    # 求解器参数：开启"枚举全部解"模式。
    solver.parameters.enumerate_all_solutions = True
    # 求解模型，每个可行解都会回调 solution_collector。
    solver.solve(model, solution_collector)
    return solution_collector.combinations()


def aggregate_item_collections_optimally(
    item_collections: list[list[int]],
    max_num_collections: int,
    ideal_item_ratios: list[float],
) -> list[int]:
    """从物品组合中（可重复地）选出一组组合，使整体方案最优。

    给定 N 种物品的若干"组合"（每个组合中同一物品可出现多次）、一个给定的
    "理想物品构成比例"，以及可选组合的数量上限，本方法求出聚合这些组合的
    最优方式，以：
    - 最大化物品总数；
    - 同时让每种物品在整体选择中的占比尽可能接近其给定的理想比例。
    每种组合可以被选用多次。

    Args:
      item_collections: 组合列表。每个组合是整数列表 [#item0, ..., #itemN-1]，
        其中 #itemK 是该组合中物品 #K 出现的次数，N 为物品种类数。
      max_num_collections: 整数，可选用组合的数量上限（同一组合的多次选用
        也计入）。
      ideal_item_ratios: N 个浮点数、总和为 1.0：第 K 个元素是物品 #K 在
        整体选择中的理想占比。

    Returns:
      若存在最优解，返回每种组合被选用的次数列表
      （第 j 个元素对应 item_collections[j] 被选用的次数）；否则返回空列表。
    """
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        return []
    n = len(ideal_item_ratios)
    num_distinct_collections = len(item_collections)
    max_num_items_per_collection = 0
    for template in item_collections:
        max_num_items_per_collection = max(max_num_items_per_collection, sum(template))
    upper_bound = max_num_items_per_collection * max_num_collections

    # 决策变量：num_selections_of_collection[i]（整数变量）表示在最终方案中
    # 第 i 种组合被选用的次数。
    num_selections_of_collection = [
        solver.IntVar(0, max_num_collections, "s[%d]" % i)
        for i in range(num_distinct_collections)
    ]

    # 决策变量：num_overall_item[i] 表示所有被选组合合计后物品 #i 的总数量，
    # 通过下面的线性约束与 num_selections_of_collection 变量绑定。
    num_overall_item = [
        solver.IntVar(0, upper_bound, "num_overall_item[%d]" % i) for i in range(n)
    ]
    for i in range(n):
        ct = solver.Constraint(0.0, 0.0)
        ct.SetCoefficient(num_overall_item[i], -1)
        for j in range(num_distinct_collections):
            ct.SetCoefficient(num_selections_of_collection[j], item_collections[j][i])

    # 决策变量：num_all_items = 所有 num_overall_item 之和（即预约总数）。
    num_all_items = solver.IntVar(0, upper_bound, "num_all_items")
    solver.Add(solver.Sum(num_overall_item) == num_all_items)

    # 约束：选用的组合总数（即工人数量）固定为 max_num_collections。
    solver.Add(solver.Sum(num_selections_of_collection) == max_num_collections)

    # 目标辅助变量：deviation_vars[i] 表示物品 #i 的实际数量与"理想数量"
    # （= 理想占比 × 物品总数）的偏差（下面用两条不等式实现绝对值）。
    deviation_vars = [
        solver.NumVar(0, upper_bound, "deviation_vars[%d]" % i) for i in range(n)
    ]
    for i in range(n):
        # 约束：deviation_vars[i] >= |num_overall_item[i] - 理想数量|（两条不等式取大）。
        deviation = deviation_vars[i]
        solver.Add(
            deviation >= num_overall_item[i] - ideal_item_ratios[i] * num_all_items
        )
        solver.Add(
            deviation >= ideal_item_ratios[i] * num_all_items - num_overall_item[i]
        )

    # 目标函数：最大化（物品总数 − 所有偏差之和），
    # 即在工人数固定的前提下尽量多完成预约，并让各类型占比贴近理想值。
    solver.Maximize(num_all_items - solver.Sum(deviation_vars))

    # 调用 MIP 求解器（SCIP）求解。
    result_status = solver.Solve()

    if result_status == pywraplp.Solver.OPTIMAL:
        # 存在最优解：返回每种组合被选用的次数。
        return [int(v.solution_value()) for v in num_selections_of_collection]
    return []


def get_optimal_schedule(
    demand: list[tuple[float, str, int]],
) -> list[tuple[int, list[tuple[int, str]]]]:
    """为安装工单输入计算最优排程。

    Args:
      demand: "预约类型"列表。每个"预约类型"是三元组
        (理想占比百分比, 名称, 时长分钟)，其中理想占比是该类型预约在
        全部排定预约中的理想百分比（取值 [0..100.0]）。

    Returns:
      排程结果列表：每个元素为 (该日程模板被分配的工人数, 预约明细列表)，
      其中预约明细为 (该类型在此模板中的次数, 类型名称)。
    """
    # 阶段一：物品大小 = 预约时长 + 通勤时间，枚举一名工人一天内
    # 总负载落在 [load_min, load_max] 的所有预约组合（即"日程模板"）。
    combinations = enumerate_all_knapsacks_with_repetition(
        [a[2] + _COMMUTE_TIME.value for a in demand],
        _LOAD_MIN.value,
        _LOAD_MAX.value,
    )
    print(
        (
            "Found %d possible day schedules " % len(combinations)
            + "(i.e. combination of appointments filling up one worker's day)"
        )
    )

    # 阶段二：在选用的日程模板总数固定为 num_workers 的条件下选出最优组合，
    # 各类型的理想占比 = demand 中的百分比 / 100。
    selection = aggregate_item_collections_optimally(
        combinations, _NUM_WORKERS.value, [a[0] / 100.0 for a in demand]
    )
    output = []
    for i, s in enumerate(selection):
        if s != 0:
            output.append(
                (
                    s,
                    [
                        (combinations[i][t], d[1])
                        for t, d in enumerate(demand)
                        if combinations[i][t] != 0
                    ],
                )
            )

    return output


def main(_):
    # 输入数据：每种预约类型为三元组（理想占比百分比, 名称, 单次时长分钟）。
    demand = [(45.0, "Type1", 90), (30.0, "Type2", 120), (25.0, "Type3", 180)]
    print("*** input problem ***")
    print("Appointments: ")
    for a in demand:
        print("   %.2f%% of %s : %d min" % (a[0], a[1], a[2]))
    print("Commute time = %d" % _COMMUTE_TIME.value)
    print(
        "Acceptable duration of a work day = [%d..%d]"
        % (_LOAD_MIN.value, _LOAD_MAX.value)
    )
    print("%d workers" % _NUM_WORKERS.value)
    selection = get_optimal_schedule(demand)
    print()
    installed = 0
    installed_per_type = {}
    for a in demand:
        installed_per_type[a[1]] = 0

    # [START print_solution]（开始打印解）
    print("*** output solution ***")
    for template in selection:
        num_instances = template[0]
        print("%d schedules with " % num_instances)
        for t in template[1]:
            mult = t[0]
            print("   %d installation of type %s" % (mult, t[1]))
            installed += num_instances * mult
            installed_per_type[t[1]] += num_instances * mult

    print()
    print("%d installations planned" % installed)
    for a in demand:
        name = a[1]
        per_type = installed_per_type[name]
        if installed != 0:
            print(
                f"   {per_type} ({per_type * 100.0 / installed}%) installations of"
                f" type {name} planned"
            )
        else:
            print(f"   {per_type} installations of type {name} planned")
    # [END print_solution]（打印解结束）


if __name__ == "__main__":
    app.run(main)
# [END program]（示例程序结束标记）
