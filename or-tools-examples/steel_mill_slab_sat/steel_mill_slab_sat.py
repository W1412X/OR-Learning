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

"""用 4 种不同的技术求解钢铁厂板坯（Steel Mill Slab）问题。"""

# 重载的 sum() 与 pytype 冲突。

import collections
import time

from absl import app
from absl import flags

from ortools.sat.python import cp_model

# 要求解的问题实例编号。
_PROBLEM = flags.DEFINE_integer("problem", 2, "Problem id to solve.")
# 是否打破等价订单之间的对称性。
_BREAK_SYMMETRIES = flags.DEFINE_boolean(
    "break_symmetries", True, "Break symmetries between equivalent orders."
)
# 求解方法：sat、sat_table、sat_column 三选一。
_SOLVER = flags.DEFINE_string(
    "solver", "sat_column", "Method used to solve: sat, sat_table, sat_column."
)
# CP-SAT 求解器参数（文本格式）。
_PARAMS = flags.DEFINE_string(
    "params",
    "max_time_in_seconds:20,num_workers:8,log_search_progress:true",
    "CP-SAT parameters.",
)


def build_problem(
    problem_id: int,
) -> tuple[int, list[int], int, list[tuple[int, int]]]:
    """构建问题数据。"""
    if problem_id == 0:
        # 板坯规格容量列表。
        capacities = [
            # fmt:off
        0, 12, 14, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30, 32, 35, 39, 42, 43, 44,
            # fmt:on
        ]
        num_colors = 88
        num_slabs = 111
        # 订单列表：(宽度 size, 颜色 color)。
        orders = [  # (size, color)
            # fmt:off
        (4, 1), (22, 2), (9, 3), (5, 4), (8, 5), (3, 6), (3, 4), (4, 7),
        (7, 4), (7, 8), (3, 6), (2, 6), (2, 4), (8, 9), (5, 10), (7, 11),
        (4, 7), (7, 11), (5, 10), (7, 11), (8, 9), (3, 1), (25, 12), (14, 13),
        (3, 6), (22, 14), (19, 15), (19, 15), (22, 16), (22, 17), (22, 18),
        (20, 19), (22, 20), (5, 21), (4, 22), (10, 23), (26, 24), (17, 25),
        (20, 26), (16, 27), (10, 28), (19, 29), (10, 30), (10, 31), (23, 32),
        (22, 33), (26, 34), (27, 35), (22, 36), (27, 37), (22, 38), (22, 39),
        (13, 40), (14, 41), (16, 27), (26, 34), (26, 42), (27, 35), (22, 36),
        (20, 43), (26, 24), (22, 44), (13, 45), (19, 46), (20, 47), (16, 48),
        (15, 49), (17, 50), (10, 28), (20, 51), (5, 52), (26, 24), (19, 53),
        (15, 54), (10, 55), (10, 56), (13, 57), (13, 58), (13, 59), (12, 60),
        (12, 61), (18, 62), (10, 63), (18, 64), (16, 65), (20, 66), (12, 67),
        (6, 68), (6, 68), (15, 69), (15, 70), (15, 70), (21, 71), (30, 72),
        (30, 73), (30, 74), (30, 75), (23, 76), (15, 77), (15, 78), (27, 79),
        (27, 80), (27, 81), (27, 82), (27, 83), (27, 84), (27, 79), (27, 85),
        (27, 86), (10, 87), (3, 88),
            # fmt:on
        ]
    elif problem_id == 1:
        capacities = [0, 17, 44]
        num_colors = 23
        num_slabs = 30
        orders = [  # (size, color)
            # fmt:off
        (4, 1), (22, 2), (9, 3), (5, 4), (8, 5), (3, 6), (3, 4), (4, 7), (7, 4),
        (7, 8), (3, 6), (2, 6), (2, 4), (8, 9), (5, 10), (7, 11), (4, 7), (7, 11),
        (5, 10), (7, 11), (8, 9), (3, 1), (25, 12), (14, 13), (3, 6), (22, 14),
        (19, 15), (19, 15), (22, 16), (22, 17), (22, 18), (20, 19), (22, 20),
        (5, 21), (4, 22), (10, 23),
            # fmt:on
        ]
    elif problem_id == 2:
        capacities = [0, 17, 44]
        num_colors = 15
        num_slabs = 20
        orders = [  # (size, color)
            # fmt:off
        (4, 1), (22, 2), (9, 3), (5, 4), (8, 5), (3, 6), (3, 4), (4, 7), (7, 4),
        (7, 8), (3, 6), (2, 6), (2, 4), (8, 9), (5, 10), (7, 11), (4, 7), (7, 11),
        (5, 10), (7, 11), (8, 9), (3, 1), (25, 12), (14, 13), (3, 6), (22, 14),
        (19, 15), (19, 15),
            # fmt:on
        ]

    else:  # problem_id == 3，默认的最小问题实例。
        capacities = [0, 17, 44]
        num_colors = 8
        num_slabs = 10
        orders = [  # (size, color)
            (4, 1),
            (22, 2),
            (9, 3),
            (5, 4),
            (8, 5),
            (3, 6),
            (3, 4),
            (4, 7),
            (7, 4),
            (7, 8),
            (3, 6),
        ]

    return (num_slabs, capacities, num_colors, orders)


class SteelMillSlabSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解。"""

    def __init__(self, orders, assign, load, loss) -> None:
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__orders = orders
        self.__assign = assign
        self.__load = load
        self.__loss = loss
        self.__solution_count = 0
        self.__all_orders = range(len(orders))
        self.__all_slabs = range(len(assign[0]))
        self.__start_time = time.time()

    def on_solution_callback(self) -> None:
        """每次发现新解时被调用。"""
        current_time = time.time()
        # 目标值 = 所有板坯浪费之和。
        objective = sum(self.value(l) for l in self.__loss)
        print(
            f"Solution {self.__solution_count}, time ="
            f" {current_time - self.__start_time} s, objective = {objective}"
        )
        self.__solution_count += 1
        # 收集每块板坯上的订单列表。
        orders_in_slab = [
            [o for o in self.__all_orders if self.value(self.__assign[o][s])]
            for s in self.__all_slabs
        ]
        # 打印每块非空板坯的装载、浪费与订单明细。
        for s in self.__all_slabs:
            if orders_in_slab[s]:
                line = (
                    f"  - slab {s}, load = {self.value(self.__load[s])}, loss ="
                    f" {self.value(self.__loss[s])}, orders = ["
                )
                for o in orders_in_slab[s]:
                    line += f"#{o}(w{self.__orders[o][0]}, c{self.__orders[o][1]})"
                line += "]"
                print(line)


def steel_mill_slab(problem_id: int, break_symmetries: bool) -> None:
    """求解钢铁厂板坯问题（方法一：直接建模）。"""
    ### 加载问题数据。
    num_slabs, capacities, num_colors, orders = build_problem(problem_id)

    num_orders = len(orders)
    num_capacities = len(capacities)
    all_slabs = range(num_slabs)
    all_colors = range(num_colors)
    all_orders = range(len(orders))
    print(
        f"Solving steel mill with {num_orders} orders, {num_slabs} slabs, and"
        f" {num_capacities - 1} capacities"
    )

    # 计算辅助数据。
    widths = [x[0] for x in orders]  # 每个订单的宽度。
    colors = [x[1] for x in orders]  # 每个订单的颜色。
    max_capacity = max(capacities)
    # loss_array[c]：装载量为 c 时选择最优规格容量的浪费。
    loss_array = [
        min(x for x in capacities if x >= c) - c for c in range(max_capacity + 1)
    ]
    max_loss = max(loss_array)
    # 每种颜色对应的订单列表。
    orders_per_color = [
        [o for o in all_orders if colors[o] == c + 1] for c in all_colors
    ]
    # 颜色组中只有一个订单的"唯一颜色订单"。
    unique_color_orders = [
        o for o in all_orders if len(orders_per_color[colors[o] - 1]) == 1
    ]

    ### 建立模型。

    # 创建模型与决策变量。
    model = cp_model.CpModel()
    # assign[o][s]：订单 o 是否分配到板坯 s（布尔决策变量）。
    assign = [
        [model.new_bool_var(f"assign_{o}_to_slab_{s}") for s in all_slabs]
        for o in all_orders
    ]
    # loads[s]：板坯 s 的装载量。
    loads = [model.new_int_var(0, max_capacity, f"load_of_slab_{s}") for s in all_slabs]
    # color_is_in_slab[s][c]：颜色 c 是否出现在板坯 s 上。
    color_is_in_slab = [
        [model.new_bool_var(f"color_{c + 1}_in_slab_{s}") for c in all_colors]
        for s in all_slabs
    ]

    # 约束：计算所有板坯的装载量（订单宽度之和）。
    for s in all_slabs:
        model.add(sum(assign[o][s] * widths[o] for o in all_orders) == loads[s])

    # 约束：每个订单恰好分配到一块板坯。
    for o in all_orders:
        model.add_exactly_one(assign[o])

    # 冗余约束（所有板坯装载量之和 == 所有订单宽度之和），可加速求解。
    model.add(sum(loads) == sum(widths))

    # 约束：把颜色出现变量与订单分配变量关联起来。
    for c in all_colors:
        for s in all_slabs:
            for o in orders_per_color[c]:
                model.add_implication(assign[o][s], color_is_in_slab[s][c])
                model.add_implication(~color_is_in_slab[s][c], ~assign[o][s])

    # 约束：每块板坯上最多出现 2 种颜色。
    for s in all_slabs:
        model.add(sum(color_is_in_slab[s]) <= 2)

    # 冗余约束：把上一约束投影到唯一颜色订单上。
    for s in all_slabs:
        model.add(sum(assign[o][s] for o in unique_color_orders) <= 2)

    # 对称性破除：板坯按装载量非升排列。
    for s in range(num_slabs - 1):
        model.add(loads[s] >= loads[s + 1])

    # 收集等价订单（颜色组与宽度都相同，可互换的订单对）。
    width_to_unique_color_order = {}
    ordered_equivalent_orders = []
    for c in all_colors:
        colored_orders = orders_per_color[c]
        if not colored_orders:
            continue
        if len(colored_orders) == 1:
            o = colored_orders[0]
            w = widths[o]
            if w not in width_to_unique_color_order:
                width_to_unique_color_order[w] = [o]
            else:
                width_to_unique_color_order[w].append(o)
        else:
            # 在同色订单内部按宽度分组。
            local_width_to_order = {}
            for o in colored_orders:
                w = widths[o]
                if w not in local_width_to_order:
                    local_width_to_order[w] = []
                local_width_to_order[w].append(o)
            for _, os in local_width_to_order.items():
                if len(os) > 1:
                    for p in range(len(os) - 1):
                        ordered_equivalent_orders.append((os[p], os[p + 1]))
    for _, os in width_to_unique_color_order.items():
        if len(os) > 1:
            for p in range(len(os) - 1):
                ordered_equivalent_orders.append((os[p], os[p + 1]))

    # 若存在需要破除的对称性，则创建位置变量。
    if break_symmetries and ordered_equivalent_orders:
        print(
            f"  - creating {len(ordered_equivalent_orders)} symmetry breaking"
            " constraints"
        )
        positions = {}
        for p in ordered_equivalent_orders:
            if p[0] not in positions:
                # positions[o]：订单 o 所在板坯的位置（通过 one-hot 映射）。
                positions[p[0]] = model.new_int_var(
                    0, num_slabs - 1, f"position_of_slab_{p[0]}"
                )
                model.add_map_domain(positions[p[0]], assign[p[0]])
            if p[1] not in positions:
                positions[p[1]] = model.new_int_var(
                    0, num_slabs - 1, f"position_of_slab_{p[1]}"
                )
                model.add_map_domain(positions[p[1]], assign[p[1]])
            # 最后添加对称性破除约束：等价订单按板坯位置排序。
            model.add(positions[p[0]] <= positions[p[1]])

    # 目标函数。
    obj = model.new_int_var(0, num_slabs * max_loss, "obj")
    # losses[s]：板坯 s 的浪费。
    losses = [model.new_int_var(0, max_loss, f"loss_{s}") for s in all_slabs]
    for s in all_slabs:
        # 元素约束：由装载量在浪费表 loss_array 中查得浪费值。
        model.add_element(loads[s], loss_array, losses[s])
    model.add(obj == sum(losses))
    # 最小化总浪费。
    model.minimize(obj)

    ### 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    objective_printer = cp_model.ObjectiveSolutionPrinter()
    status = solver.solve(model, objective_printer)

    ### 输出解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(
            f"Loss = {solver.objective_value}, time = {solver.wall_time} s,"
            f" {solver.num_conflicts} conflicts"
        )
    else:
        print("No solution")


def collect_valid_slabs_dp(
    capacities: list[int],
    colors: list[int],
    widths: list[int],
    loss_array: list[int],
) -> list[list[int]]:
    """用 DP 收集单块板坯的所有合法配置（assign, loss）列。"""
    start_time = time.time()

    max_capacity = max(capacities)

    # valid_assignment：一个可行配置（订单集合、装载量、颜色集合）。
    valid_assignment = collections.namedtuple("valid_assignment", "orders load colors")
    # 初始只有一个空配置。
    all_valid_assignments = [valid_assignment(orders=[], load=0, colors=[])]

    # 逐个订单扩展所有可行配置。
    for order_id, new_color in enumerate(colors):
        new_width = widths[order_id]
        new_assignments = []
        for assignment in all_valid_assignments:
            # 容量超限则跳过。
            if assignment.load + new_width > max_capacity:
                continue
            # 加入新订单，并维护颜色集合。
            new_colors = list(assignment.colors)
            if new_color not in new_colors:
                new_colors.append(new_color)
            # 颜色超过 2 种则不合法。
            if len(new_colors) > 2:
                continue
            new_assignment = valid_assignment(
                orders=assignment.orders + [order_id],
                load=assignment.load + new_width,
                colors=new_colors,
            )
            new_assignments.append(new_assignment)
        all_valid_assignments.extend(new_assignments)

    print(
        f"{len(all_valid_assignments)} assignments created in"
        f" {time.time() - start_time:2f} s"
    )
    # 把每个配置转成表约束所需的元组：0/1 订单向量 + 浪费 + 装载量。
    tuples = []
    for assignment in all_valid_assignments:
        solution = [0] * len(colors)
        for i in assignment.orders:
            solution[i] = 1
        solution.append(loss_array[assignment.load])
        solution.append(assignment.load)
        tuples.append(solution)

    return tuples


def steel_mill_slab_with_valid_slabs(problem_id: int, break_symmetries: bool) -> None:
    """求解钢铁厂板坯问题（方法二：表约束建模）。"""
    ### 加载问题数据。
    (num_slabs, capacities, num_colors, orders) = build_problem(problem_id)

    num_orders = len(orders)
    num_capacities = len(capacities)
    all_slabs = range(num_slabs)
    all_colors = range(num_colors)
    all_orders = range(len(orders))
    print(
        f"Solving steel mill with {num_orders} orders, {num_slabs} slabs, and"
        f" {num_capacities - 1} capacities"
    )

    # 计算辅助数据。
    widths = [x[0] for x in orders]  # 每个订单的宽度。
    colors = [x[1] for x in orders]  # 每个订单的颜色。
    max_capacity = max(capacities)
    # loss_array[c]：装载量为 c 时选择最优规格容量的浪费。
    loss_array = [
        min(x for x in capacities if x >= c) - c for c in range(max_capacity + 1)
    ]
    max_loss = max(loss_array)

    ### 建立模型。

    # 创建模型与决策变量。
    model = cp_model.CpModel()
    # assign[o][s]：订单 o 是否分配到板坯 s。
    assign = [
        [model.new_bool_var(r"assign_{o}_to_slab_{s}") for s in all_slabs]
        for o in all_orders
    ]
    # loads[s]：板坯 s 的装载量；losses[s]：板坯 s 的浪费。
    loads = [model.new_int_var(0, max_capacity, f"load_{s}") for s in all_slabs]
    losses = [model.new_int_var(0, max_loss, f"loss_{s}") for s in all_slabs]

    # 用 DP 枚举单块板坯的所有合法配置。
    unsorted_valid_slabs = collect_valid_slabs_dp(
        capacities, colors, widths, loss_array
    )
    # 按装载量/浪费降序排序并去重。
    valid_slabs = sorted(unsorted_valid_slabs, key=lambda c: 1000 * c[-1] + c[-2])

    # 表约束：每块板坯的 (订单分配, 浪费, 装载量) 必须是合法配置之一。
    for s in all_slabs:
        model.add_allowed_assignments(
            [assign[o][s] for o in all_orders] + [losses[s], loads[s]], valid_slabs
        )

    # 约束：每个订单恰好分配到一块板坯。
    for o in all_orders:
        model.add_exactly_one(assign[o])

    # 冗余约束（所有板坯装载量之和 == 所有订单宽度之和）。
    model.add(sum(loads) == sum(widths))

    # 对称性破除：板坯按装载量非升排列。
    for s in range(num_slabs - 1):
        model.add(loads[s] >= loads[s + 1])

    # 收集等价订单（颜色组与宽度都相同，可互换的订单对）。
    if break_symmetries:
        print("Breaking symmetries")
        width_to_unique_color_order = {}
        ordered_equivalent_orders = []
        orders_per_color = [
            [o for o in all_orders if colors[o] == c + 1] for c in all_colors
        ]
        for c in all_colors:
            colored_orders = orders_per_color[c]
            if not colored_orders:
                continue
            if len(colored_orders) == 1:
                o = colored_orders[0]
                w = widths[o]
                if w not in width_to_unique_color_order:
                    width_to_unique_color_order[w] = [o]
                else:
                    width_to_unique_color_order[w].append(o)
            else:
                # 在同色订单内部按宽度分组。
                local_width_to_order = {}
                for o in colored_orders:
                    w = widths[o]
                    if w not in local_width_to_order:
                        local_width_to_order[w] = []
                        local_width_to_order[w].append(o)
                for _, os in local_width_to_order.items():
                    if len(os) > 1:
                        for p in range(len(os) - 1):
                            ordered_equivalent_orders.append((os[p], os[p + 1]))
        for _, os in width_to_unique_color_order.items():
            if len(os) > 1:
                for p in range(len(os) - 1):
                    ordered_equivalent_orders.append((os[p], os[p + 1]))

        # 若存在需要破除的对称性，则创建位置变量。
        if ordered_equivalent_orders:
            print(
                f"  - creating {len(ordered_equivalent_orders)} symmetry breaking"
                " constraints"
            )
            positions = {}
            for p in ordered_equivalent_orders:
                if p[0] not in positions:
                    # positions[o]：订单 o 所在板坯的位置（one-hot 映射）。
                    positions[p[0]] = model.new_int_var(
                        0, num_slabs - 1, f"position_of_slab_{p[0]}"
                    )
                    model.add_map_domain(positions[p[0]], assign[p[0]])
                if p[1] not in positions:
                    positions[p[1]] = model.new_int_var(
                        0, num_slabs - 1, f"position_of_slab_{p[1]}"
                    )
                    model.add_map_domain(positions[p[1]], assign[p[1]])
                    # 最后添加对称性破除约束。
                model.add(positions[p[0]] <= positions[p[1]])

    # 目标函数：最小化总浪费。
    model.minimize(sum(losses))

    print("Model created")

    ### 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)

    solution_printer = SteelMillSlabSolutionPrinter(orders, assign, loads, losses)
    status = solver.solve(model, solution_printer)

    ### 输出解。
    if status == cp_model.OPTIMAL:
        print(
            f"Loss = {solver.objective_value}, time = {solver.wall_time:2f} s,"
            f" {solver.num_conflicts} conflicts"
        )
    else:
        print("No solution")


def steel_mill_slab_with_column_generation(problem_id: int) -> None:
    """求解钢铁厂板坯问题（方法三：列选择建模）。"""
    ### 加载问题数据。
    (num_slabs, capacities, _, orders) = build_problem(problem_id)

    num_orders = len(orders)
    num_capacities = len(capacities)
    all_orders = range(len(orders))
    print(
        f"Solving steel mill with {num_orders} orders, {num_slabs} slabs, and"
        f" {num_capacities - 1} capacities"
    )

    # 计算辅助数据。
    widths = [x[0] for x in orders]  # 每个订单的宽度。
    colors = [x[1] for x in orders]  # 每个订单的颜色。
    max_capacity = max(capacities)
    # loss_array[c]：装载量为 c 时选择最优规格容量的浪费。
    loss_array = [
        min(x for x in capacities if x >= c) - c for c in range(max_capacity + 1)
    ]

    ### 建立模型。

    # 枚举全部合法板坯（"列"）。
    unsorted_valid_slabs = collect_valid_slabs_dp(
        capacities, colors, widths, loss_array
    )

    # 按装载量/浪费降序排序并去重。
    valid_slabs = sorted(unsorted_valid_slabs, key=lambda c: 1000 * c[-1] + c[-2])
    all_valid_slabs = range(len(valid_slabs))

    # 创建模型与决策变量。
    model = cp_model.CpModel()
    # selected[i]：是否选择第 i 列（合法板坯配置）。
    selected = [model.new_bool_var(f"selected_{i}") for i in all_valid_slabs]

    # 集合划分约束：每个订单恰好被一个选中的列覆盖。
    for order_id in all_orders:
        model.add(
            sum(selected[i] for i, slab in enumerate(valid_slabs) if slab[order_id])
            == 1
        )

    # 冗余约束（所有选中列装载量之和 == 所有订单宽度之和）。
    model.add(
        sum(selected[i] * valid_slabs[i][-1] for i in all_valid_slabs) == sum(widths)
    )

    # 目标函数：最小化所有选中列的浪费之和。
    model.minimize(sum(selected[i] * valid_slabs[i][-2] for i in all_valid_slabs))

    print("Model created")

    ### 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    solution_printer = cp_model.ObjectiveSolutionPrinter()
    status = solver.solve(model, solution_printer)

    ### 输出解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(
            f"Loss = {solver.objective_value}, time = {solver.wall_time:2f} s,"
            f" {solver.num_conflicts} conflicts"
        )
    else:
        print("No solution")


def main(_):
    # 根据 --solver 参数选择求解方法。
    if _SOLVER.value == "sat":
        steel_mill_slab(_PROBLEM.value, _BREAK_SYMMETRIES.value)
    elif _SOLVER.value == "sat_table":
        steel_mill_slab_with_valid_slabs(_PROBLEM.value, _BREAK_SYMMETRIES.value)
    elif _SOLVER.value == "sat_column":
        steel_mill_slab_with_column_generation(_PROBLEM.value)
    else:
        print(f"Unknown model {_SOLVER.value}")


if __name__ == "__main__":
    app.run(main)
