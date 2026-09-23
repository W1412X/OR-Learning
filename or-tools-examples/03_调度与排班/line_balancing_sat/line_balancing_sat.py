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

"""单装配线平衡问题的读取与求解器。

来自 https://assembly-line-balancing.de/salbp/：

简单装配线平衡问题（SALBP）是装配线平衡研究中的基础优化问题。给定一组
任务，每个任务有确定性的任务时间；任务之间由先后关系部分排序，构成一张
如下所示的先后关系图。

本程序读取 .alb 文件：
    https://assembly-line-balancing.de/wp-content/uploads/2017/01/format-ALB.pdf

并求解对应的装配线平衡问题。
"""

import collections
import re
from typing import Dict, Sequence

from absl import app
from absl import flags


from ortools.sat.python import cp_model

# flag：要解析并求解的输入文件（.alb 格式）。
_INPUT = flags.DEFINE_string("input", "", "Input file to parse and solve.")
# flag：SAT 求解器参数（文本格式）。
_PARAMS = flags.DEFINE_string("params", "", "Sat solver parameters.")
# flag：把 CP-SAT 模型 proto 写入指定的输出文件。
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
# flag：选择使用的模型（boolean / scheduling / greedy）。
_MODEL = flags.DEFINE_string(
    "model", "boolean", "Model used: boolean, scheduling, greedy"
)


class SectionInfo:
    """保存输入文件每个分节（section）的问题信息。"""

    def __init__(self):
        self.value = None  # 该节的单个数值（如任务数、节拍时间）。
        self.index_map = {}  # 该节的键值映射（如任务编号 -> 任务时间）。
        self.set_of_pairs = set()  # 该节的成对关系集合（如先后关系对）。

    def __str__(self):
        if self.index_map:
            return f"SectionInfo(index_map={self.index_map})"
        elif self.set_of_pairs:
            return f"SectionInfo(set_of_pairs={self.set_of_pairs})"
        elif self.value is not None:
            return f"SectionInfo(value={self.value})"
        else:
            return "SectionInfo()"


def read_problem(filename: str) -> Dict[str, SectionInfo]:
    """读取 .alb 文件并返回问题数据。"""

    current_info = SectionInfo()

    problem: Dict[str, SectionInfo] = {}
    with open(filename, "r") as input_file:
        print(f"Reading problem from '{filename}'")

        # 逐行解析：节名 <...>、单个数字、两个数字的键值对、逗号分隔的先后关系对。
        for line in input_file:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            match_section_def = re.fullmatch(r"<([\w\s]+)>", stripped_line)
            if match_section_def:
                # 遇到新的节定义：创建新的 SectionInfo。
                section_name = match_section_def.group(1)
                if section_name == "end":
                    continue

                current_info = SectionInfo()
                problem[section_name] = current_info
                continue

            match_single_number = re.fullmatch(r"^([0-9]+)$", stripped_line)
            if match_single_number:
                # 单个数字：写入当前节的 value。
                current_info.value = int(match_single_number.group(1))
                continue

            match_key_value = re.fullmatch(r"^([0-9]+)\s+([0-9]+)$", stripped_line)
            if match_key_value:
                # 键值对（如 任务编号 任务时间）：写入当前节的 index_map。
                key = int(match_key_value.group(1))
                value = int(match_key_value.group(2))
                current_info.index_map[key] = value
                continue

            match_pair = re.fullmatch(r"^([0-9]+),([0-9]+)$", stripped_line)
            if match_pair:
                # 逗号分隔的对（如 先后关系）：写入当前节的 set_of_pairs。
                left = int(match_pair.group(1))
                right = int(match_pair.group(2))
                current_info.set_of_pairs.add((left, right))
                continue

            # 无法识别的行。
            print(f"Unrecognized line '{stripped_line}'")

    return problem


def print_stats(problem: Dict[str, SectionInfo]) -> None:
    # 打印问题各节的内容统计。
    print("Problem Statistics")
    for key, value in problem.items():
        print(f"  - {key}: {value}")


def solve_problem_greedily(problem: Dict[str, SectionInfo]) -> Dict[int, int]:
    """计算一个贪心解。"""
    print("Solving using a Greedy heuristics")

    # 任务数量（.alb 数据中任务编号从 1 开始）。
    num_tasks = problem["number of tasks"].value
    if num_tasks is None:
        return {}
    all_tasks = range(1, num_tasks + 1)  # 数据中的任务编号从 1 开始。
    precedences = problem["precedence relations"].set_of_pairs
    durations = problem["task times"].index_map
    cycle_time = problem["cycle time"].value

    # weights[t]：任务 t 尚未满足的先决条件数量；successors[t]：任务 t 的后继列表。
    weights = collections.defaultdict(int)
    successors = collections.defaultdict(list)

    # 候选任务集合：初始为所有任务，之后逐步移除/加入。
    candidates = set(all_tasks)

    for before, after in precedences:
        weights[after] += 1
        successors[before].append(after)
        if after in candidates:
            candidates.remove(after)

    # 贪心分配：任务编号 -> 工位编号。
    assignment: Dict[int, int] = {}
    current_pod = 0  # 当前工位编号。
    residual_capacity = cycle_time  # 当前工位的剩余容量。

    while len(assignment) < num_tasks:
        if not candidates:
            print("error empty")
            break

        # 在候选任务中挑选"放入当前工位后剩余容量最小且不超载"的任务。
        best = -1
        best_slack = cycle_time
        best_duration = 0

        for c in candidates:
            duration = durations[c]
            slack = residual_capacity - duration
            if slack < best_slack and slack >= 0:
                best_slack = slack
                best = c
                best_duration = duration

        # 当前工位装不下任何候选任务：开启新工位。
        if best == -1:
            current_pod += 1
            residual_capacity = cycle_time
            continue

        # 把选中的任务放入当前工位。
        candidates.remove(best)
        assignment[best] = current_pod
        residual_capacity -= best_duration

        # 释放该任务的后继任务（前驱计数归零后成为新的候选）。
        for succ in successors[best]:
            weights[succ] -= 1
            if weights[succ] == 0:
                candidates.add(succ)
                del weights[succ]

    print(f"  greedy solution uses {current_pod + 1} pods.")

    return assignment


def solve_problem_with_boolean_model(
    problem: Dict[str, SectionInfo], hint: Dict[int, int]
) -> None:
    """用布尔模型求解给定问题。"""

    print("Solving using the Boolean model")
    # 问题数据。
    num_tasks = problem["number of tasks"].value
    if num_tasks is None:
        return
    all_tasks = range(1, num_tasks + 1)  # 问题中的任务编号从 1 开始。
    durations = problem["task times"].index_map
    precedences = problem["precedence relations"].set_of_pairs
    cycle_time = problem["cycle time"].value

    # 工位数量上限：取贪心解的工位数，无提示时为 num_tasks - 1。
    num_pods = max(p for _, p in hint.items()) + 1 if hint else num_tasks - 1
    all_pods = range(num_pods)

    model = cp_model.CpModel()

    # assign[t, p] 表示任务 t 是否安排在工位 p 上。
    assign = {}
    # possible[t, p] 表示任务 t 是否可能安排在工位 p（或更晚的工位）上。
    possible = {}

    # 创建变量。
    for t in all_tasks:
        for p in all_pods:
            assign[t, p] = model.new_bool_var(f"assign_{t}_{p}")
            possible[t, p] = model.new_bool_var(f"possible_{t}_{p}")

    # active[p] 表示工位 p 是否被使用。
    active = [model.new_bool_var(f"active_{p}") for p in all_pods]

    # 每个任务必须且只能安排在一个工位上。
    for t in all_tasks:
        model.add_exactly_one([assign[t, p] for p in all_pods])

    # 分配到同一工位的任务总时长不能超过节拍时间。
    for p in all_pods:
        model.add(sum(assign[t, p] * durations[t] for t in all_tasks) <= cycle_time)

    # 维护 possible 变量的单调性：
    #   在工位 p 可行 -> 在工位 p 之后的任何工位也可行。
    for t in all_tasks:
        for p in range(num_pods - 1):
            model.add_implication(possible[t, p], possible[t, p + 1])

    # 联动 possible 与 assign 变量。
    for t in all_tasks:
        for p in all_pods:
            model.add_implication(assign[t, p], possible[t, p])
            if p > 1:
                model.add_implication(assign[t, p], ~possible[t, p - 1])

    # 先后关系：前序任务在工位 p 时，后序任务不能安排在工位 p 之前。
    for before, after in precedences:
        for p in range(1, num_pods):
            model.add_implication(assign[before, p], ~possible[after, p - 1])

    # 联动 active 与 assign 变量：工位被使用当且仅当有任务分配到该工位。
    for p in all_pods:
        all_assign_vars = [assign[t, p] for t in all_tasks]
        for a in all_assign_vars:
            model.add_implication(a, active[p])
        model.add_bool_or(all_assign_vars + [~active[p]])

    # 强制工位连续使用。这一点对获得好的目标下界至关重要，
    # 尽管它会让可行性判定更难。
    for p in range(1, num_pods):
        model.add_implication(~active[p - 1], ~active[p])
        for t in all_tasks:
            model.add_implication(~active[p], possible[t, p - 1])

    # 目标函数：最小化使用的工位数量。
    model.minimize(sum(active))

    # 把贪心解作为搜索提示加入模型。
    for t in all_tasks:
        model.add_hint(assign[t, hint[t]], 1)

    if _OUTPUT_PROTO.value:
        print(f"Writing proto to {_OUTPUT_PROTO.value}")
        model.export_to_file(_OUTPUT_PROTO.value)

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    solver.parameters.log_search_progress = True
    solver.solve(model)


def solve_problem_with_scheduling_model(
    problem: Dict[str, SectionInfo], hint: Dict[int, int]
) -> None:
    """用累积（cumulative）调度模型求解给定问题。"""

    print("Solving using the scheduling model")
    # 问题数据。
    num_tasks = problem["number of tasks"].value
    if num_tasks is None:
        return
    all_tasks = range(1, num_tasks + 1)  # 数据中的任务编号从 1 开始。
    durations = problem["task times"].index_map
    precedences = problem["precedence relations"].set_of_pairs
    cycle_time = problem["cycle time"].value

    # 工位数量上限：取贪心解的工位数，无提示时为 num_tasks。
    num_pods = max(p for _, p in hint.items()) + 1 if hint else num_tasks

    model = cp_model.CpModel()

    # pods[t] 表示任务 t 在哪个工位上执行。
    pods = {}
    for t in all_tasks:
        pods[t] = model.new_int_var(0, num_pods - 1, f"pod_{t}")

    # 创建变量：把"任务所在的工位"建模为区间（起点 = 工位编号，长度为 1）。
    intervals = []
    demands = []
    for t in all_tasks:
        interval = model.new_fixed_size_interval_var(pods[t], 1, "")
        intervals.append(interval)
        demands.append(durations[t])

    # 添加一个终止区间作为目标：它的起点即实际使用的工位数。
    obj_var = model.new_int_var(1, num_pods, "obj_var")
    obj_size = model.new_int_var(1, num_pods, "obj_duration")
    obj_interval = model.new_interval_var(
        obj_var, obj_size, num_pods + 1, "obj_interval"
    )
    intervals.append(obj_interval)
    demands.append(cycle_time)

    # 累积约束：任意工位上的任务总需求不超过节拍时间。
    model.add_cumulative(intervals, demands, cycle_time)

    # 先后关系：后序任务的工位编号不能小于前序任务。
    for before, after in precedences:
        model.add(pods[after] >= pods[before])

    # 目标函数：最小化终止区间的起点（即使用的工位数）。
    model.minimize(obj_var)

    # 把贪心解作为搜索提示加入模型。
    for t in all_tasks:
        model.add_hint(pods[t], hint[t])

    if _OUTPUT_PROTO.value:
        print(f"Writing proto to{_OUTPUT_PROTO.value}")
        model.export_to_file(_OUTPUT_PROTO.value)

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    solver.parameters.log_search_progress = True
    solver.solve(model)


def main(argv: Sequence[str]) -> None:
    # 命令行只允许 flags，不允许额外的位置参数。
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    # 读取问题并打印统计信息。
    problem = read_problem(_INPUT.value)
    print_stats(problem)
    # 先求贪心解（作为搜索提示与工位数上界）。
    greedy_solution = solve_problem_greedily(problem)

    # 按所选模型精确求解。
    if _MODEL.value == "boolean":
        solve_problem_with_boolean_model(problem, greedy_solution)
    elif _MODEL.value == "scheduling":
        solve_problem_with_scheduling_model(problem, greedy_solution)


if __name__ == "__main__":
    app.run(main)
