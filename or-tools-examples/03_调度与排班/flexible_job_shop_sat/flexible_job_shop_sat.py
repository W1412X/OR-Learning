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

"""用 CP-SAT 求解器求解柔性作业车间（flexible jobshop）调度问题。

作业车间调度是一类标准的调度问题：需要在一组机器上为一序列工序
排序。每个作业在每台机器上都有一个对应的工序；工序的执行顺序以及
作业在每台机器上的加工时长都取决于具体的工序。

优化目标是最小化所有作业的最大完工时间，即 makespan。
"""

# 重载的 sum() 会与 pytype 冲突，故添加此说明。
import collections

from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解的回调类。"""

    def __init__(self) -> None:
        cp_model.CpSolverSolutionCallback.__init__(self)
        # 已找到的解的数量
        self.__solution_count = 0

    def on_solution_callback(self) -> None:
        """每发现一个新解时被调用。"""
        print(
            f"Solution {self.__solution_count}, time = {self.wall_time} s,"
            f" objective = {self.objective_value}"
        )
        self.__solution_count += 1


def flexible_jobshop() -> None:
    """求解一个小型柔性作业车间调度问题。"""
    # 数据部分。
    # 任务格式：(加工时间, 机器编号)
    jobs = [  # task = (processing_time, machine_id)
        [  # Job 0
            [(3, 0), (1, 1), (5, 2)],  # 工序 0，共 3 个备选方案
            [(2, 0), (4, 1), (6, 2)],  # 工序 1，共 3 个备选方案
            [(2, 0), (3, 1), (1, 2)],  # 工序 2，共 3 个备选方案
        ],
        [  # Job 1
            [(2, 0), (3, 1), (4, 2)],
            [(1, 0), (5, 1), (4, 2)],
            [(2, 0), (1, 1), (4, 2)],
        ],
        [  # Job 2
            [(2, 0), (1, 1), (4, 2)],
            [(2, 0), (3, 1), (4, 2)],
            [(3, 0), (1, 1), (5, 2)],
        ],
    ]

    num_jobs = len(jobs)
    all_jobs = range(num_jobs)

    num_machines = 3
    all_machines = range(num_machines)

    # 建立柔性作业车间调度模型。
    model = cp_model.CpModel()

    # 计算时间上界 horizon：所有工序各自最大加工时间之和
    horizon = 0
    for job in jobs:
        for task in job:
            max_task_duration = 0
            for alternative in task:
                max_task_duration = max(max_task_duration, alternative[0])
            horizon += max_task_duration

    print(f"Horizon = {horizon}")

    # 变量的全局存储。
    intervals_per_resources = collections.defaultdict(list)  # 每台机器的区间列表
    starts = {}  # 以 (job_id, task_id) 为键
    presences = {}  # 以 (job_id, task_id, alt_id) 为键
    job_ends: list[cp_model.IntVar] = []

    # 扫描所有作业，创建相关的变量与区间。
    for job_id in all_jobs:
        job = jobs[job_id]
        num_tasks = len(job)
        previous_end = None
        for task_id in range(num_tasks):
            task = job[task_id]

            # 统计该工序所有备选方案的加工时间范围
            min_duration = task[0][0]
            max_duration = task[0][0]

            num_alternatives = len(task)
            all_alternatives = range(num_alternatives)

            for alt_id in range(1, num_alternatives):
                alt_duration = task[alt_id][0]
                min_duration = min(min_duration, alt_duration)
                max_duration = max(max_duration, alt_duration)

            # 创建该工序的主区间。
            suffix_name = f"_j{job_id}_t{task_id}"
            # 决策变量：工序开始时间
            start = model.new_int_var(0, horizon, "start" + suffix_name)
            # 决策变量：工序实际加工时长（落在各备选方案的时长范围内）
            duration = model.new_int_var(
                min_duration, max_duration, "duration" + suffix_name
            )
            # 决策变量：工序结束时间
            end = model.new_int_var(0, horizon, "end" + suffix_name)
            interval = model.new_interval_var(
                start, duration, end, "interval" + suffix_name
            )

            # 保存开始时间变量，便于最后输出解。
            starts[(job_id, task_id)] = start

            # 约束：与同一作业内的上一道工序保持先后顺序。
            if previous_end is not None:
                model.add(start >= previous_end)
            previous_end = end

            # 创建各备选方案（机器选择）的可选区间。
            if num_alternatives > 1:
                l_presences = []
                for alt_id in all_alternatives:
                    alt_suffix = f"_j{job_id}_t{task_id}_a{alt_id}"
                    # 布尔变量：是否选中该备选方案（该机器）
                    l_presence = model.new_bool_var("presence" + alt_suffix)
                    l_start = model.new_int_var(0, horizon, "start" + alt_suffix)
                    l_duration = task[alt_id][0]
                    l_end = model.new_int_var(0, horizon, "end" + alt_suffix)
                    # 可选区间：仅当 presence 为真时才生效
                    l_interval = model.new_optional_interval_var(
                        l_start, l_duration, l_end, l_presence, "interval" + alt_suffix
                    )
                    l_presences.append(l_presence)

                    # 约束：选中该方案时，把主（全局）变量与局部变量绑定一致。
                    model.add(start == l_start).only_enforce_if(l_presence)
                    model.add(duration == l_duration).only_enforce_if(l_presence)
                    model.add(end == l_end).only_enforce_if(l_presence)

                    # 把该可选区间加入对应机器的区间列表。
                    intervals_per_resources[task[alt_id][1]].append(l_interval)

                    # 保存 presence 变量，便于最后输出解。
                    presences[(job_id, task_id, alt_id)] = l_presence

                # 约束：恰好选中一个备选方案。
                model.add_exactly_one(l_presences)
            else:
                # 只有一个方案时，直接把主区间挂到对应机器上
                intervals_per_resources[task[0][1]].append(interval)
                presences[(job_id, task_id, 0)] = model.new_constant(1)

        if previous_end is not None:
            job_ends.append(previous_end)

    # 创建机器约束：同一机器上的区间不能重叠。
    for machine_id in all_machines:
        intervals = intervals_per_resources[machine_id]
        if len(intervals) > 1:
            model.add_no_overlap(intervals)

    # 目标函数：makespan（最大完工时间）。
    # 决策变量：makespan
    makespan = model.new_int_var(0, horizon, "makespan")
    # 约束：makespan 等于所有作业结束时间的最大值
    model.add_max_equality(makespan, job_ends)
    # 目标：最小化 makespan
    model.minimize(makespan)

    # 求解模型。
    solver = cp_model.CpSolver()
    solution_printer = SolutionPrinter()
    status = solver.solve(model, solution_printer)

    # 打印最终解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"Optimal objective value: {solver.objective_value}")
        for job_id in all_jobs:
            print(f"Job {job_id}")
            for task_id, task in enumerate(jobs[job_id]):
                # 该工序的开始时间
                start_value = solver.value(starts[(job_id, task_id)])
                machine: int = -1
                task_duration: int = -1
                selected: int = -1
                # 找出被选中的备选方案，得到机器与时长
                for alt_id, alt in enumerate(task):
                    if solver.boolean_value(presences[(job_id, task_id, alt_id)]):
                        task_duration, machine = alt
                        selected = alt_id
                print(
                    f"  task_{job_id}_{task_id} starts at {start_value} (alt"
                    f" {selected}, machine {machine}, duration {task_duration})"
                )

    print(solver.response_stats())


flexible_jobshop()
