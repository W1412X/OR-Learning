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

"""基于 CP-SAT 的 RCPSP 问题求解器（参见 rcpsp.proto）。

问题介绍：
   https://www.projectmanagement.ugent.be/research/project_scheduling/rcpsp

flag 使用的数据：
  http://www.om-db.wi.tum.de/psplib/data.html
"""

import collections

from absl import app
from absl import flags

from ortools.sat.python import cp_model
from ortools.scheduling import rcpsp_pb2
from ortools.scheduling.python import rcpsp

_INPUT = flags.DEFINE_string("input", "", "Input file to parse and solve.")
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
_PARAMS = flags.DEFINE_string("params", "", "Sat solver parameters.")
_USE_INTERVAL_MAKESPAN = flags.DEFINE_bool(
    "use_interval_makespan",
    True,
    "Whether we encode the makespan using an interval or not.",
)
_HORIZON = flags.DEFINE_integer("horizon", -1, "Force horizon.")


def print_problem_statistics(problem: rcpsp_pb2.RcpspProblem):
    """打印问题的各种统计信息。"""

    # 判断问题类型。
    problem_type = (
        "Resource Investment Problem" if problem.is_resource_investment else "RCPSP"
    )

    num_resources = len(problem.resources)
    num_tasks = len(problem.tasks) - 2  # 去掉 2 个哨兵任务。
    tasks_with_alternatives = 0
    variable_duration_tasks = 0
    tasks_with_delay = 0

    for task in problem.tasks:
        if len(task.recipes) > 1:
            tasks_with_alternatives += 1
            duration_0 = task.recipes[0].duration
            for recipe in task.recipes:
                if recipe.duration != duration_0:
                    variable_duration_tasks += 1
                    break
        if task.successor_delays:
            tasks_with_delay += 1

    if problem.is_rcpsp_max:
        problem_type += "/Max delay"
    # 输出的任务数比实际少 2：哨兵任务不计入 rcpsp 模型的描述。
    if problem.is_consumer_producer:
        print(f"Solving {problem_type} with:")
        print(f"  - {num_resources} reservoir resources")
        print(f"  - {num_tasks} tasks")
    else:
        print(f"Solving {problem_type} with:")
        print(f"  - {num_resources} renewable resources")
        print(f"  - {num_tasks} tasks")
        if tasks_with_alternatives:
            print(f"    - {tasks_with_alternatives} tasks with alternative resources")
        if variable_duration_tasks:
            print(f"    - {variable_duration_tasks} tasks with variable durations")
        if tasks_with_delay:
            print(f"    - {tasks_with_delay} tasks with successor delays")


def solve_rcpsp(
    problem: rcpsp_pb2.RcpspProblem,
    proto_file: str,
    params: str,
    active_tasks: set[int],
    source: int,
    sink: int,
) -> None:
    """解析并求解一个 proto 格式的 RCPSP 问题。

    模型只考虑 {source} + {sink} + active_tasks 中的任务，忽略其余任务。

    参数：
      problem: 以 protobuf 格式描述的待求解模型
      proto_file: 导出 CpModel proto 的目标文件名。
      params: 传给 SAT 求解器的参数（字符串形式）。
      active_tasks: 需要考虑的活动任务集合。
      source: 图中的源任务。其结束时间被强制为 0。
      sink: 图中的汇任务。其开始时间即问题的 makespan（总工期）。

    返回：
      (目标函数下界, 找到的最优解, 分配结果)
    """
    # 创建模型。
    model = cp_model.CpModel()
    model.name = problem.name

    num_resources = len(problem.resources)

    all_active_tasks = list(active_tasks)
    all_active_tasks.sort()
    all_resources = range(num_resources)

    # 计算时间跨度 horizon：优先取 deadline，其次 horizon，均无效则朴素估计
    horizon = problem.deadline if problem.deadline != -1 else problem.horizon
    if _HORIZON.value > 0:
        # flag 强制指定的 horizon 优先级最高
        horizon = _HORIZON.value
    elif horizon == -1:  # 朴素计算：所有任务最大工期之和（max 问题再加上所有延迟的绝对值）
        horizon = sum(max(r.duration for r in t.recipes) for t in problem.tasks)
        if problem.is_rcpsp_max:
            for t in problem.tasks:
                for sd in t.successor_delays:
                    for rd in sd.recipe_delays:
                        for d in rd.min_delays:
                            horizon += abs(d)
    print(f"Horizon = {horizon}", flush=True)

    # 数据容器：
    # 任务的时间/区间变量，以及 (任务, 资源) 维度的能量与需求信息
    task_starts = {}
    task_ends = {}
    task_durations = {}
    task_intervals = {}
    task_resource_to_energy = {}
    # 每个任务对各资源的需求变量列表
    task_to_resource_demands = collections.defaultdict(list)

    # 每个任务的模式选择字面量 / 各模式工期 / (任务,资源)→固定需求表 / 最大能量
    task_to_presence_literals = collections.defaultdict(list)
    task_to_recipe_durations = collections.defaultdict(list)
    task_resource_to_fixed_demands = collections.defaultdict(dict)
    task_resource_to_max_energy = collections.defaultdict(int)

    # 每种资源的需求上界之和（用于无容量信息时的回退值）
    resource_to_sum_of_demand_max = collections.defaultdict(int)

    # 创建任务变量。
    for t in all_active_tasks:
        task = problem.tasks[t]
        num_recipes = len(task.recipes)
        all_recipes = range(num_recipes)

        # 开始/结束时间变量（取值范围 [0, horizon]）
        start_var = model.new_int_var(0, horizon, f"start_of_task_{t}")
        end_var = model.new_int_var(0, horizon, f"end_of_task_{t}")

        if num_recipes > 1:
            # 多模式任务：为每个 recipe 创建一个选择字面量。
            literals = [model.new_bool_var(f"is_present_{t}_{r}") for r in all_recipes]

            # 约束：恰好执行其中一种 recipe。
            model.add_exactly_one(literals)

        else:
            # 单模式任务：无需选择字面量
            literals = [1]

        # 临时数据结构：把缺失的需求补为 0。
        demand_matrix = collections.defaultdict(int)

        # 扫描所有 recipe，构建需求矩阵与工期向量。
        for recipe_index, recipe in enumerate(task.recipes):
            task_to_recipe_durations[t].append(recipe.duration)
            for demand, resource in zip(recipe.demands, recipe.resources):
                demand_matrix[(resource, recipe_index)] = demand

        # 用累计出的工期集合创建工期变量。
        duration_var = model.new_int_var_from_domain(
            cp_model.Domain.from_values(task_to_recipe_durations[t]),
            f"duration_of_task_{t}",
        )

        # 把 recipe 选择字面量与工期变量联动：选中哪个模式，工期即为其值。
        for r in range(num_recipes):
            model.add(duration_var == task_to_recipe_durations[t][r]).only_enforce_if(
                literals[r]
            )

        # 创建任务的区间变量（开始 + 工期 = 结束）。
        task_interval = model.new_interval_var(
            start_var, duration_var, end_var, f"task_interval_{t}"
        )

        # 保存任务变量。
        task_starts[t] = start_var
        task_ends[t] = end_var
        task_durations[t] = duration_var
        task_intervals[t] = task_interval
        task_to_presence_literals[t] = literals

        # 为任务的每种资源创建需求变量。
        for res in all_resources:
            demands = [demand_matrix[(res, recipe)] for recipe in all_recipes]
            task_resource_to_fixed_demands[(t, res)] = demands
            demand_var = model.new_int_var_from_domain(
                cp_model.Domain.from_values(demands), f"demand_{t}_{res}"
            )
            task_to_resource_demands[t].append(demand_var)

            # 把 recipe 选择字面量与需求变量联动：选中哪个模式，需求即为其值。
            for r in all_recipes:
                model.add(demand_var == demand_matrix[(res, r)]).only_enforce_if(
                    literals[r]
                )

            resource_to_sum_of_demand_max[res] += max(demands)

        # 为 (任务, 资源) 组合创建能量表达式：
        # 能量 = 所选模式的字面量 × 工期 × 需求 之和
        for res in all_resources:
            task_resource_to_energy[(t, res)] = sum(
                literals[r]
                * task_to_recipe_durations[t][r]
                * task_resource_to_fixed_demands[(t, res)][r]
                for r in all_recipes
            )
            task_resource_to_max_energy[(t, res)] = max(
                task_to_recipe_durations[t][r]
                * task_resource_to_fixed_demands[(t, res)][r]
                for r in all_recipes
            )

    # 创建 makespan（总工期）变量：
    # 把 makespan 编码为一个区间，便于参与累积约束以压缩总工期
    makespan = model.new_int_var(0, horizon, "makespan")
    makespan_size = model.new_int_var(1, horizon, "interval_makespan_size")
    interval_makespan = model.new_interval_var(
        makespan,
        makespan_size,
        model.new_constant(horizon + 1),
        "interval_makespan",
    )

    # 添加先后约束。
    if problem.is_rcpsp_max:
        # 在 RCPSP/Max 问题中，先后关系以两个任务开始时间之间的
        # 最大延迟（可为负）形式给出。
        for task_id in all_active_tasks:
            task = problem.tasks[task_id]
            num_modes = len(task.recipes)

            for successor_index, next_id in enumerate(task.successors):
                delay_matrix = task.successor_delays[successor_index]
                num_next_modes = len(problem.tasks[next_id].recipes)
                for m1 in range(num_modes):
                    s1 = task_starts[task_id]
                    p1 = task_to_presence_literals[task_id][m1]
                    if next_id == sink:
                        delay = delay_matrix.recipe_delays[m1].min_delays[0]
                        model.add(s1 + delay <= makespan).only_enforce_if(p1)
                    else:
                        for m2 in range(num_next_modes):
                            delay = delay_matrix.recipe_delays[m1].min_delays[m2]
                            s2 = task_starts[next_id]
                            p2 = task_to_presence_literals[next_id][m2]
                            model.add(s1 + delay <= s2).only_enforce_if([p1, p2])
    else:
        # 普通先后依赖：任务必须在后继任务开始之前结束。
        for t in all_active_tasks:
            for n in problem.tasks[t].successors:
                if n == sink:
                    model.add(task_ends[t] <= makespan)
                elif n in active_tasks:
                    model.add(task_ends[t] <= task_starts[n])

    # 资源投资问题（RIP）专用容器。
    capacities = []  # 所有资源的容量变量。
    max_cost = 0  # 投资成本的上界。

    # 创建资源约束。
    for res in all_resources:
        resource = problem.resources[res]
        c = resource.max_capacity
        if c == -1:
            print(f"No capacity: {resource}")
            c = resource_to_sum_of_demand_max[res]

        # RIP 问题只有可再生资源，且没有 makespan。
        if problem.is_resource_investment or resource.renewable:
            intervals = [task_intervals[t] for t in all_active_tasks]
            demands = [task_to_resource_demands[t][res] for t in all_active_tasks]

            if problem.is_resource_investment:
                capacity = model.new_int_var(0, c, f"capacity_of_{res}")
                model.add_cumulative(intervals, demands, capacity)
                capacities.append(capacity)
                max_cost += c * resource.unit_cost
            else:  # 标准可再生资源：累积约束（任一时刻总需求 ≤ 容量 c）
                if _USE_INTERVAL_MAKESPAN.value:
                    intervals.append(interval_makespan)
                    demands.append(c)

                model.add_cumulative(intervals, demands, c)
        else:  # 非空且不可再生的资源。（仅支持单模式）
            if problem.is_consumer_producer:
                reservoir_starts = []
                reservoir_demands = []
                for t in all_active_tasks:
                    if task_resource_to_fixed_demands[(t, res)][0]:
                        reservoir_starts.append(task_starts[t])
                        reservoir_demands.append(
                            task_resource_to_fixed_demands[(t, res)][0]
                        )
                model.add_reservoir_constraint(
                    reservoir_starts,
                    reservoir_demands,
                    resource.min_capacity,
                    resource.max_capacity,
                )
            else:  # 非生产者-消费者情形：直接对总需求求和并与容量比较。
                model.add(
                    cp_model.LinearExpr.sum(
                        [task_to_resource_demands[t][res] for t in all_active_tasks]
                    )
                    <= c
                )

    # 目标函数。
    if problem.is_resource_investment:
        objective = model.new_int_var(0, max_cost, "capacity_costs")
        model.add(
            objective
            == sum(
                problem.resources[i].unit_cost * capacities[i]
                for i in range(len(capacities))
            )
        )
    else:
        objective = makespan

    model.minimize(objective)

    # 添加哨兵任务：
    # source 任务的开始/结束时间固定为 0；
    # sink 任务的开始时间即 makespan（作为图汇总节点）。
    task_starts[source] = 0
    task_ends[source] = 0
    task_to_presence_literals[0].append(True)
    task_starts[sink] = makespan
    task_to_presence_literals[sink].append(True)

    # 把模型写入文件。
    if proto_file:
        print(f"Writing proto to{proto_file}")
        model.export_to_file(proto_file)

    # 求解模型。
    solver = cp_model.CpSolver()

    # 解析用户指定的求解器参数。
    if params:
        solver.parameters.parse_text_format(params)

    # 偏好 objective_shaving 而非 objective_lb_search。
    if solver.parameters.num_workers >= 16 and solver.parameters.num_workers < 24:
        solver.parameters.ignore_subsolvers.append("objective_lb_search")
        solver.parameters.extra_subsolvers.append("objective_shaving")

    # 实验性：告知求解器目标函数是 makespan（总工期）
    solver.parameters.push_all_tasks_toward_start = True

    # 在主求解过程中启用日志。
    solver.parameters.log_search_progress = True

    # 求解模型。
    solver.solve(model)


def main(_):
    # 解析输入文件并打印统计信息
    rcpsp_parser = rcpsp.RcpspParser()
    rcpsp_parser.parse_file(_INPUT.value)

    problem = rcpsp_parser.problem()
    print_problem_statistics(problem)

    # 最后一个任务作为 sink（哨兵），任务 0 作为 source（哨兵）
    last_task = len(problem.tasks) - 1

    solve_rcpsp(
        problem=problem,
        proto_file=_OUTPUT_PROTO.value,
        params=_PARAMS.value,
        active_tasks=set(range(1, last_task)),
        source=0,
        sink=last_task,
    )


if __name__ == "__main__":
    app.run(main)
