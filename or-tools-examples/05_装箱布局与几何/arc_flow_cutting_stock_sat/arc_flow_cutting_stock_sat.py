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

"""下料问题（cutting stock）：用最少的原材料切出全部零件，目标是最小化浪费的空间。"""

import collections
import time

from absl import app
from absl import flags
import numpy as np

from ortools.linear_solver.python import model_builder as mb
from ortools.sat.python import cp_model


# absl 命令行参数定义：
#   output_proto  默认 ""：若非空，把 CP-SAT 模型 proto 导出到该文件
#   params        默认 "num_search_workers:8,log_search_progress:true,max_time_in_seconds:10"
#                 传给 CP-SAT 求解器的参数（文本格式）
#   solver        默认 "sat"：求解方式，"sat"（CP-SAT）或 "mip"（SCIP）
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:8,log_search_progress:true,max_time_in_seconds:10",
    "Sat solver parameters.",
)
_SOLVER = flags.DEFINE_string("solver", "sat", "Method used to solve: sat, mip.")


# 需要切出的零件长度清单（每个元素是一个零件的长度，可重复出现）。
DESIRED_LENGTHS = [
    2490,
    3980,
    2490,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    2456,
    2456,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    2490,
    3980,
    2490,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    2456,
    2456,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    2890,
    3980,
    2890,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    2856,
    2856,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    3290,
    3980,
    3290,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    3256,
    3256,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    3690,
    3980,
    3690,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    3656,
    3656,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    2790,
    3980,
    2790,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    2756,
    2756,
    3018,
    938,
    3018,
    938,
    943,
    3018,
    943,
    3018,
    2790,
    3980,
    2790,
    3980,
    2391,
    2391,
    2391,
    596,
    596,
    596,
    2756,
    2756,
    3018,
    938,
    3018,
    938,
    943,
]
# 可用原材料（卷材/板材）的候选容量（长度）。
POSSIBLE_CAPACITIES = [4000, 5000, 6000, 7000, 8000]

# 玩具规模的小算例（取消注释即可用小数据调试）：
# DESIRED_LENGTHS = [12, 12, 8, 8, 8]
# POSSIBLE_CAPACITIES = [10, 20]


def regroup_and_count(raw_input):
    """把相同的长度归并计数，返回多重集 [[size, count], ...]（按 size 升序）。"""
    grouped = collections.defaultdict(int)
    for i in raw_input:
        grouped[i] += 1
    output = []
    for size, count in grouped.items():
        output.append([size, count])
    output.sort(reverse=False)
    return output


def price_usage(usage, capacities):
    """给定用量 usage 与候选容量，返回选用"恰好装得下的最小容量"时的浪费量
    （= 容量 − 用量）的最小值。"""
    price = max(capacities)
    for capacity in capacities:
        if capacity < usage:
            continue
        price = min(capacity - usage, price)
    return price


def create_state_graph(items, max_capacity):
    """根据物品多重集与最大容量，用动态规划构造状态图（arc-flow 图）。"""
    states = []
    state_to_index = {}
    states.append(0)
    state_to_index[0] = 0
    transitions = []

    for item_index, size_and_count in enumerate(items):
        size, count = size_and_count
        num_states = len(states)
        for state_index in range(num_states):
            current_state = states[state_index]
            current_state_index = state_index

            for card in range(count):
                new_state = current_state + size * (card + 1)
                if new_state > max_capacity:
                    break
                if new_state in state_to_index:
                    new_state_index = state_to_index[new_state]
                else:
                    new_state_index = len(states)
                    states.append(new_state)
                    state_to_index[new_state] = new_state_index
                # 添加一条转移弧 [当前状态索引, 新状态索引, 物品编号, 件数 card]。
                transitions.append(
                    [current_state_index, new_state_index, item_index, card + 1]
                )

    return states, transitions


def solve_cutting_stock_with_arc_flow_and_sat(output_proto_file: str, params: str):
    """用 arc-flow（弧流）建模 + CP-SAT 求解下料问题。"""
    # 预处理：把零件长度归并计数，便于构造状态图。
    items = regroup_and_count(DESIRED_LENGTHS)
    print("Items:", items)
    num_items = len(DESIRED_LENGTHS)

    # 用动态规划构造状态图：状态 = 已装入当前原材料的长度；
    # 转移弧 = 在当前状态再装入若干同种零件。states/transitions 即图的规模。
    max_capacity = max(POSSIBLE_CAPACITIES)
    states, transitions = create_state_graph(items, max_capacity)

    print(
        "Dynamic programming has generated",
        len(states),
        "states and",
        len(transitions),
        "transitions",
    )

    # 变量容器：incoming_vars/outgoing_vars 按状态（节点）收集入弧/出弧流量变量，
    # incoming_sink_vars 收集进入汇点（"本根原材料切割完成"）的弧，
    # item_vars/item_coeffs 收集每种零件涉及的弧及系数（每条弧一次携带的件数），
    # transition_vars 收集全部弧流量变量。
    incoming_vars = collections.defaultdict(list)
    outgoing_vars = collections.defaultdict(list)
    incoming_sink_vars = []
    item_vars = collections.defaultdict(list)
    item_coeffs = collections.defaultdict(list)
    transition_vars = []

    model = cp_model.CpModel()

    objective_vars = []
    objective_coeffs = []

    # 决策变量：每条转移弧上的流量（= 使用该弧的原材料根数）。
    # 弧一次携带 card 件同种零件，其使用次数上界为 count // card
    # （受该零件总量限制）。
    for outgoing, incoming, item_index, card in transitions:
        count = items[item_index][1]
        max_count = count // card
        count_var = model.NewIntVar(
            0, max_count, "i%i_f%i_t%i_C%s" % (item_index, incoming, outgoing, card)
        )
        incoming_vars[incoming].append(count_var)
        outgoing_vars[outgoing].append(count_var)
        item_vars[item_index].append(count_var)
        item_coeffs[item_index].append(card)
        transition_vars.append(count_var)

    # 决策变量：每个非源状态引出一条"结束本根原材料"的弧（进入汇点），
    # 其流量表示有多少根原材料在该状态下切割完成；
    # 代价 price = 选用恰好容纳 state 的最小容量时的浪费量。
    for state_index, state in enumerate(states):
        if state_index == 0:
            continue
        exit_var = model.NewIntVar(0, num_items, "e%i" % state_index)
        outgoing_vars[state_index].append(exit_var)
        incoming_sink_vars.append(exit_var)
        price = price_usage(state, POSSIBLE_CAPACITIES)
        objective_vars.append(exit_var)
        objective_coeffs.append(price)

    # 约束（流守恒）：除源点外，每个状态的入弧流量之和等于出弧流量之和。
    for state_index in range(1, len(states)):
        model.Add(sum(incoming_vars[state_index]) == sum(outgoing_vars[state_index]))

    # 约束：从源点流出的总流量 = 进入汇点的总流量（= 使用的原材料根数）。
    model.Add(sum(outgoing_vars[0]) == sum(incoming_sink_vars))

    # 约束（需求覆盖）：每种零件在所有弧上被装载的总件数必须等于其需求量。
    for item_index, size_and_count in enumerate(items):
        num_arcs = len(item_vars[item_index])
        model.Add(
            sum(
                item_vars[item_index][i] * item_coeffs[item_index][i]
                for i in range(num_arcs)
            )
            == size_and_count[1]
        )

    # 目标函数：最小化所有"结束弧"的浪费量之和（即总浪费）。
    model.Minimize(
        sum(objective_vars[i] * objective_coeffs[i] for i in range(len(objective_vars)))
    )

    # 若指定了 output_proto，则把模型导出为 proto 文本文件。
    if output_proto_file:
        model.ExportToFile(output_proto_file)

    # 求解模型（参数由 --params 文本格式传入）。
    solver = cp_model.CpSolver()
    if params:
        solver.parameters.parse_text_format(params)
    solver.parameters.log_search_progress = True
    solver.Solve(model)


def solve_cutting_stock_with_arc_flow_and_mip():
    """用 arc-flow（弧流）建模 + MIP（SCIP）求解下料问题。"""
    # 预处理：把零件长度归并计数，便于构造状态图。
    items = regroup_and_count(DESIRED_LENGTHS)
    print("Items:", items)
    num_items = len(DESIRED_LENGTHS)
    # 用动态规划构造状态图：状态 = 已装入当前原材料的长度；
    # 转移弧 = 在当前状态再装入若干同种零件。
    max_capacity = max(POSSIBLE_CAPACITIES)
    states, transitions = create_state_graph(items, max_capacity)

    print(
        "Dynamic programming has generated",
        len(states),
        "states and",
        len(transitions),
        "transitions",
    )

    incoming_vars = collections.defaultdict(list)
    outgoing_vars = collections.defaultdict(list)
    incoming_sink_vars = []
    item_vars = collections.defaultdict(list)
    item_coeffs = collections.defaultdict(list)

    # 用 model_builder（mb）API 构建 MIP 模型（求解器为 SCIP），并开始计时。
    start_time = time.time()
    model = mb.ModelBuilder()

    objective_vars = []
    objective_coeffs = []

    # 决策变量：每条转移弧上的流量（= 使用该弧的原材料根数；
    # 本 MIP 版直接用 count 作为上界）。
    var_index = 0
    for outgoing, incoming, item_index, card in transitions:
        count = items[item_index][1]
        count_var = model.new_int_var(
            0,
            count,
            "a%i_i%i_f%i_t%i_c%i" % (var_index, item_index, incoming, outgoing, card),
        )
        var_index += 1
        incoming_vars[incoming].append(count_var)
        outgoing_vars[outgoing].append(count_var)
        item_vars[item_index].append(count_var)
        item_coeffs[item_index].append(card)

    # 决策变量：每个非源状态引出的"结束弧"流量（= 在此状态完成的原材料根数）。
    for state_index, state in enumerate(states):
        if state_index == 0:
            continue
        exit_var = model.new_int_var(0, num_items, "e%i" % state_index)
        outgoing_vars[state_index].append(exit_var)
        incoming_sink_vars.append(exit_var)
        price = price_usage(state, POSSIBLE_CAPACITIES)
        objective_vars.append(exit_var)
        objective_coeffs.append(price)

    # 约束（流守恒）：除源点外，每个状态的入弧流量之和等于出弧流量之和。
    for state_index in range(1, len(states)):
        model.add(
            mb.LinearExpr.sum(incoming_vars[state_index])
            == mb.LinearExpr.sum(outgoing_vars[state_index])
        )

    # 约束：从源点流出的总流量 = 进入汇点的总流量（= 使用的原材料根数）。
    model.add(
        mb.LinearExpr.sum(outgoing_vars[0]) == mb.LinearExpr.sum(incoming_sink_vars)
    )

    # 约束（需求覆盖）：每种零件在所有弧上被装载的总件数必须等于其需求量。
    for item_index, size_and_count in enumerate(items):
        num_arcs = len(item_vars[item_index])
        model.add(
            mb.LinearExpr.sum(
                [
                    item_vars[item_index][i] * item_coeffs[item_index][i]
                    for i in range(num_arcs)
                ]
            )
            == size_and_count[1]
        )

    # 目标函数：最小化所有"结束弧"的浪费量之和（即总浪费）。
    model.minimize(np.dot(objective_vars, objective_coeffs))

    solver = mb.ModelSolver("scip")
    solver.enable_output(True)
    status = solver.solve(model)

    ### 输出求解结果。
    if status == mb.SolveStatus.OPTIMAL or status == mb.SolveStatus.FEASIBLE:
        print(
            "Objective value = %f found in %.2f s"
            % (solver.objective_value, time.time() - start_time)
        )
    else:
        print("No solution")


def main(_):
    """主函数。"""
    # 按 --solver 参数选择求解方式：sat → CP-SAT；mip → SCIP。
    if _SOLVER.value == "sat":
        solve_cutting_stock_with_arc_flow_and_sat(_OUTPUT_PROTO.value, _PARAMS.value)
    else:  # 'mip'
        solve_cutting_stock_with_arc_flow_and_mip()


if __name__ == "__main__":
    app.run(main)
