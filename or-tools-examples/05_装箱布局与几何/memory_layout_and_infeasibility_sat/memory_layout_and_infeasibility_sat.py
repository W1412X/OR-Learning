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

"""求解内存分配问题，并返回解释不可行性的最小需求集合。"""

from collections.abc import Sequence
from typing import List

from absl import app
from absl import flags

from ortools.sat.python import cp_model


# flag：输出文件路径，非空时把 cp_model proto 写入该文件
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
# flag：SAT 求解器参数（文本格式），默认单工作线程、线性化级别 2
_PARAMS = flags.DEFINE_string(
    "params", "num_workers:1,linearization_level:2", "Sat solver parameters."
)


# 问题的输入数据。
# 每行形如 [start, end, demand, alignment]：
# start/end 为时间窗口，demand 为内存需求大小，alignment（对齐）未使用
DEMANDS = [
    [1578, 1583, 43008, 1],
    [1588, 1589, 11264, 1],
    [1590, 1595, 43008, 1],
    [1583, 1588, 47872, 1],
    [1589, 1590, 22848, 1],
    [1586, 1590, 22848, 1],
    [1591, 1594, 43008, 1],
]
# 内存总容量（y 方向缓冲区高度）
CAPACITY = 98304


def solve_hard_model(output_proto: str, params: str) -> bool:
    """求解硬分配模型（所有任务都必须放置）。"""
    print("Solving the hard assignment model")
    model = cp_model.CpModel()

    # 三个并行列表：时间区间、缓冲区起点变量、缓冲区区间
    x_intervals: List[cp_model.IntervalVar] = []
    y_starts: List[cp_model.IntVar] = []
    y_intervals: List[cp_model.IntervalVar] = []

    for start_time, end_time, demand, _ in DEMANDS:
        # x 方向：时间区间，起点固定为 start_time，长度为 end-start+1
        x_interval = model.new_fixed_size_interval_var(
            start_time, end_time - start_time + 1, ""
        )
        # y 方向决策变量：缓冲区起点，范围 [0, CAPACITY-demand]
        y_start = model.new_int_var(0, CAPACITY - demand, "")
        # y 方向：内存占用区间，起点为 y_start，长度为 demand
        y_interval = model.new_fixed_size_interval_var(y_start, demand, "")

        x_intervals.append(x_interval)
        y_starts.append(y_start)
        y_intervals.append(y_interval)

    # 核心约束：2D 无重叠——任何两个任务的 (时间, 内存) 矩形不得重叠
    model.add_no_overlap_2d(x_intervals, y_intervals)

    # 如有需要则导出模型
    if output_proto:
        model.export_to_file(output_proto)

    # 创建求解器并解析参数
    solver = cp_model.CpSolver()
    if params:
        solver.parameters.parse_text_format(params)
    status = solver.solve(model)
    # 打印求解统计信息
    print(solver.response_stats())

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        # 可行时打印每个任务缓冲区的起点
        for index, start_var in enumerate(y_starts):
            print(f"task {index} buffer starts at {solver.value(start_var)}")

    # 返回模型是否可行（False 表示不可行，将触发软模型分析）
    return status != cp_model.INFEASIBLE


def solve_soft_model_with_assumptions() -> None:
    """使用假设（assumptions）求解软模型。"""
    print("Solving the soft model using assumptions")

    model = cp_model.CpModel()

    # presence：任务是否被放置；可选区间由 presence 控制
    presences: List[cp_model.IntVar] = []
    x_intervals: List[cp_model.IntervalVar] = []
    y_starts: List[cp_model.IntVar] = []
    y_intervals: List[cp_model.IntervalVar] = []

    for start, end, demand, unused_alignment in DEMANDS:
        # 布尔变量：该任务是否被放置
        presence = model.new_bool_var("")
        # x 方向：可选时间区间（presence 为假时不占用）
        x_interval = model.new_optional_fixed_size_interval_var(
            start, end - start + 1, presence, ""
        )
        # y 方向：缓冲区起点变量
        y_start = model.new_int_var(0, CAPACITY - demand, "")
        # y 方向：可选内存占用区间
        y_interval = model.new_optional_fixed_size_interval_var(
            y_start, demand, presence, ""
        )

        presences.append(presence)
        x_intervals.append(x_interval)
        y_starts.append(y_start)
        y_intervals.append(y_interval)

    # 2D 无重叠约束（可选区间不参与冲突检查）
    model.add_no_overlap_2d(x_intervals, y_intervals)
    # 把所有任务都放置作为"假设"提出
    model.add_assumptions(presences)

    solver = cp_model.CpSolver()
    status = solver.solve(model)
    print(solver.response_stats())
    if status == cp_model.INFEASIBLE:
        # 该列表实际上包含足以解释不可行性的变量下标。
        # （MUS 风格分析：找出最小的冲突假设集合）
        infeasible_variable_indices = solver.sufficient_assumptions_for_infeasibility()
        infeasible_variable_indices_set = set(infeasible_variable_indices)

        for index, presence in enumerate(presences):
            # 打印哪些任务共同导致不可行
            if presence.index in infeasible_variable_indices_set:
                print(f"using task {index} is sufficient to explain infeasibility")


def solve_soft_model_with_maximization(params: str) -> None:
    """使用最大化目标求解软模型。"""
    print("Solving the soft model using minimization")

    model = cp_model.CpModel()

    # presence：任务是否被放置；可选区间由 presence 控制
    presences: List[cp_model.IntVar] = []
    x_intervals: List[cp_model.IntervalVar] = []
    y_starts: List[cp_model.IntVar] = []
    y_intervals: List[cp_model.IntervalVar] = []

    for start, end, demand, unused_alignment in DEMANDS:
        # 布尔变量：该任务是否被放置
        presence = model.new_bool_var("")
        # x 方向：可选时间区间
        x_interval = model.new_optional_fixed_size_interval_var(
            start, end - start + 1, presence, ""
        )
        # y 方向：缓冲区起点变量
        y_start = model.new_int_var(0, CAPACITY - demand, "")
        # y 方向：可选内存占用区间
        y_interval = model.new_optional_fixed_size_interval_var(
            y_start, demand, presence, ""
        )

        presences.append(presence)
        x_intervals.append(x_interval)
        y_starts.append(y_start)
        y_intervals.append(y_interval)

    # 2D 无重叠约束
    model.add_no_overlap_2d(x_intervals, y_intervals)

    # 目标函数：最大化成功放置的任务数
    model.maximize(sum(presences))

    solver = cp_model.CpSolver()
    if params:
        solver.parameters.parse_text_format(params)
    status = solver.solve(model)
    print(solver.response_stats())
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for index, presence in enumerate(presences):
            if not solver.boolean_value(presence):
                # presence 为假：该任务放不下
                print(f"task {index} does not fit")
            else:
                # 已放置：打印缓冲区起点
                print(f"task {index} buffer starts at {solver.value(y_starts[index])}")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    # 先求解硬模型；若不可行，再用两种软模型方法分析原因
    if not solve_hard_model(_OUTPUT_PROTO.value, _PARAMS.value):
        solve_soft_model_with_assumptions()
        solve_soft_model_with_maximization(_PARAMS.value)


if __name__ == "__main__":
    app.run(main)
