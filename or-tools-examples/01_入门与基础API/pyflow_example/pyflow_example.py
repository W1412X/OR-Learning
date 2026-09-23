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

"""最大流（MaxFlow）与最小费用流（MinCostFlow）示例。"""

from typing import Sequence
from absl import app
from ortools.graph.python import max_flow
from ortools.graph.python import min_cost_flow


def max_flow_api():
    """最大流简单接口示例。"""
    print("MaxFlow on a simple network.")
    # ---- 输入数据：以平行数组形式描述网络中的 9 条弧 ----
    # tails[i] / heads[i]：第 i 条弧的起点与终点节点编号
    # capacities[i]：第 i 条弧的容量上限
    tails = [0, 0, 0, 0, 1, 2, 3, 3, 4]
    heads = [1, 2, 3, 4, 3, 4, 4, 5, 5]
    capacities = [5, 8, 5, 3, 4, 5, 6, 6, 4]
    # 预期的最大总流量，用于与求解结果对照
    expected_total_flow = 10
    # 创建最大流求解器（简单接口封装）
    smf = max_flow.SimpleMaxFlow()
    # 逐条添加带容量约束的弧：流量不得超过该容量
    for i in range(0, len(tails)):
        smf.add_arc_with_capacity(tails[i], heads[i], capacities[i])
    # 求解：从源点 0 到汇点 5 的最大流
    if smf.solve(0, 5) == smf.OPTIMAL:
        # optimal_flow() 返回最大总流量
        print("Total flow", smf.optimal_flow(), "/", expected_total_flow)
        # 遍历所有弧，打印每条弧上的实际流量与容量
        for i in range(smf.num_arcs()):
            print(
                "From source %d to target %d: %d / %d"
                % (smf.tail(i), smf.head(i), smf.flow(i), smf.capacity(i))
            )
        # 最小割：与最大流相等的"瓶颈"分割，打印割两侧的节点集合
        print("Source side min-cut:", smf.get_source_side_min_cut())
        print("Sink side min-cut:", smf.get_sink_side_min_cut())
    else:
        print("There was an issue with the max flow input.")


def min_cost_flow_api():
    """最小费用流简单接口示例。

    注意：本示例本质上是一个线性指派（linear sum assignment）问题，
    若专门求解指派问题，使用 LinearSumAssignment 类会更高效。
    """
    print("MinCostFlow on 4x4 matrix.")
    # ---- 输入数据：4 个工人（源节点 0~3）与 4 项任务（汇节点 4~7）----
    num_sources = 4
    num_targets = 4
    # costs[source][target]：工人 source 完成任务 target 的成本
    costs = [
        [90, 75, 75, 80],
        [35, 85, 55, 65],
        [125, 95, 90, 105],
        [45, 110, 95, 115],
    ]
    # 预期的最小总成本，用于与求解结果对照
    expected_cost = 275
    # 创建最小费用流求解器（简单接口封装）
    smcf = min_cost_flow.SimpleMinCostFlow()
    # 为每个"工人→任务"组合添加一条弧：
    # 容量为 1（一一匹配，每个工人最多做一项任务），单位成本取自成本矩阵
    for source in range(0, num_sources):
        for target in range(0, num_targets):
            smcf.add_arc_with_capacity_and_unit_cost(
                source, num_sources + target, 1, costs[source][target]
            )
    # 设置节点供需，构造流量守恒约束：
    # 工人节点供给 +1（恰好发出 1 单位流），任务节点供给 -1（恰好接收 1 单位流）
    for node in range(0, num_sources):
        smcf.set_node_supply(node, 1)
        smcf.set_node_supply(num_sources + node, -1)
    # 求解：在满足供需平衡的前提下最小化总费用
    status = smcf.solve()
    if status == smcf.OPTIMAL:
        # optimal_cost() 返回最小总成本（目标函数最优值）
        print("Total flow", smcf.optimal_cost(), "/", expected_cost)
        # 打印所有流量大于 0 的弧，即被选中的"工人→任务"分配方案
        for i in range(0, smcf.num_arcs()):
            if smcf.flow(i) > 0:
                print(
                    "From source %d to target %d: cost %d"
                    % (smcf.tail(i), smcf.head(i) - num_sources, smcf.unit_cost(i))
                )
    else:
        print("There was an issue with the min cost flow input.")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    max_flow_api()
    min_cost_flow_api()


if __name__ == "__main__":
    app.run(main)
