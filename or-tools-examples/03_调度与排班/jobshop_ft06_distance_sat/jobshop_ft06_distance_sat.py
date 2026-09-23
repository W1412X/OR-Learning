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

"""本模型实现了 ft06 作业车间调度问题的一个变体。

作业车间调度（jobshop）是一类标准的调度问题：需要在一组机器上对一系列
任务进行排序。每个作业（job）在每台机器上各有一个任务（task）。任务的
执行顺序与在每个机器上的加工时长均由具体任务决定。

优化目标是最小化所有作业的最大完工时间（makespan）。

本变体在每台机器上的所有作业之间引入了最小间隔距离。
"""

import collections

from ortools.sat.python import cp_model


def distance_between_jobs(x: int, y: int) -> int:
    """返回作业 x 的任务与作业 y 的任务之间的最小间隔距离。"""
    return abs(x - y)


def jobshop_ft06_distance() -> None:
    """求解带任务间隔的 ft06 作业车间调度问题。"""
    # 创建模型。
    model = cp_model.CpModel()

    # 算例规模：6 台机器、6 个作业。
    machines_count = 6
    jobs_count = 6
    all_machines = range(0, machines_count)
    all_jobs = range(0, jobs_count)

    # 每个作业各道工序的加工时长：durations[i][j] 为作业 i 的第 j 道工序时长。
    durations = [
        [1, 3, 6, 7, 3, 6],
        [8, 5, 10, 10, 10, 4],
        [5, 4, 8, 9, 1, 7],
        [5, 5, 5, 3, 8, 9],
        [9, 3, 5, 4, 3, 1],
        [3, 3, 9, 10, 4, 1],
    ]

    # 每个作业各道工序使用的机器编号：machines[i][j] 为作业 i 的第 j 道工序所在机器。
    machines = [
        [2, 0, 1, 3, 5, 4],
        [1, 2, 4, 5, 0, 3],
        [2, 3, 5, 0, 1, 4],
        [1, 0, 2, 3, 4, 5],
        [2, 1, 4, 5, 0, 3],
        [1, 3, 5, 0, 4, 2],
    ]

    # 静态计算时间上界 horizon（一个足够大的保守值）。
    horizon = 150

    # 命名元组：保存每个任务的开始、结束与区间变量。
    task_type = collections.namedtuple("task_type", "start end interval")

    # 创建所有作业的任务变量。
    all_tasks = {}
    for i in all_jobs:
        for j in all_machines:
            # 任务 (i, j) 的开始时间变量。
            start_var = model.new_int_var(0, horizon, f"start_{i}_{j}")
            duration = durations[i][j]
            # 任务 (i, j) 的结束时间变量。
            end_var = model.new_int_var(0, horizon, f"end_{i}_{j}")
            # 区间变量：把开始、时长、结束绑定在一起。
            interval_var = model.new_interval_var(
                start_var, duration, end_var, f"interval_{i}_{j}"
            )
            all_tasks[(i, j)] = task_type(
                start=start_var, end=end_var, interval=interval_var
            )

    # 创建析取（互斥）约束。
    for i in all_machines:
        # 收集在机器 i 上加工的所有任务的区间/索引/开始/结束变量。
        job_intervals = []
        job_indices = []
        job_starts = []
        job_ends = []
        for j in all_jobs:
            for k in all_machines:
                if machines[j][k] == i:
                    job_intervals.append(all_tasks[(j, k)].interval)
                    job_indices.append(j)
                    job_starts.append(all_tasks[(j, k)].start)
                    job_ends.append(all_tasks[(j, k)].end)
        # 机器容量约束：同一机器上的任务两两不重叠。
        model.add_no_overlap(job_intervals)

        # 用回路约束为机器 i 上的任务构造一个全序（哈密顿回路）。
        arcs = []
        for j1 in range(len(job_intervals)):
            # 从虚拟节点（0）到任务的起始弧：表示该任务是机器上的第一个任务。
            start_lit = model.new_bool_var(f"{j1} is first job")
            arcs.append((0, j1 + 1, start_lit))
            # 从任务回到虚拟节点的结束弧：表示该任务是机器上的最后一个任务。
            arcs.append((j1 + 1, 0, model.new_bool_var(f"{j1} is last job")))

            for j2 in range(len(job_intervals)):
                if j1 == j2:
                    continue

                # 弧变量 lit 为真表示任务 j2 紧跟在任务 j1 之后。
                lit = model.new_bool_var(f"{j2} follows {j1}")
                arcs.append((j1 + 1, j2 + 1, lit))

                # 用条件（reified）约束把该弧字面量与两个任务的时间联系起来：
                # 后继任务的开始时间必须不早于前驱结束时间加上最小间隔距离。
                min_distance = distance_between_jobs(j1, j2)
                model.add(
                    job_starts[j2] >= job_ends[j1] + min_distance
                ).only_enforce_if(lit)

        # 回路约束：所有弧构成一条经过每个任务恰好一次的回路，
        # 从而确定该机器上任务的加工顺序。
        model.add_circuit(arcs)

    # 作业内部的先后顺序：下一道工序必须等上一道工序结束。
    for i in all_jobs:
        for j in range(0, machines_count - 1):
            model.add(all_tasks[(i, j + 1)].start >= all_tasks[(i, j)].end)

    # 目标函数：最小化 makespan（所有作业最后一道工序结束时间的最大值）。
    obj_var = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(
        obj_var, [all_tasks[(i, machines_count - 1)].end for i in all_jobs]
    )
    model.minimize(obj_var)

    # 求解模型。
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    # 输出解。
    if status == cp_model.OPTIMAL:
        print(f"Optimal makespan: {solver.objective_value}")
    print(solver.response_stats())


# 脚本被导入或执行时直接求解。
jobshop_ft06_distance()
