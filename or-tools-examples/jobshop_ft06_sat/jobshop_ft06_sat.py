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

"""本模型实现了名为 ft06 的简单作业车间调度问题。

作业车间调度（jobshop）是一类标准的调度问题：需要在一组机器上对一系列
任务（task_type）进行排序。每个作业（job）在每台机器上各有一个任务
（task_type）。任务的执行顺序与在各机器上的加工时长均由具体任务决定。

优化目标是最小化所有作业的最大完工时间（makespan）。
"""

import collections

from ortools.sat.colab import visualization
from ortools.sat.python import cp_model


def jobshop_ft06() -> None:
    """求解 ft06 作业车间调度问题。"""
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

    # 动态计算时间上界 horizon：所有工序时长之和（最保守的上界）。
    horizon = sum([sum(durations[i]) for i in all_jobs])

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
            # 区间变量：把开始、固定时长、结束绑定在一起。
            interval_var = model.new_interval_var(
                start_var, duration, end_var, f"interval_{i}_{j}"
            )
            all_tasks[(i, j)] = task_type(
                start=start_var, end=end_var, interval=interval_var
            )

    # 创建析取（互斥）约束：按机器分组，保证同一机器上的任务不重叠。
    machine_to_jobs = {}
    for i in all_machines:
        machines_jobs = []
        for j in all_jobs:
            for k in all_machines:
                if machines[j][k] == i:
                    # 任务 (j, k) 的工序在机器 i 上加工，加入该机器的区间列表。
                    machines_jobs.append(all_tasks[(j, k)].interval)
        machine_to_jobs[i] = machines_jobs
        # 机器容量约束：同机器上的任务两两不重叠。
        model.add_no_overlap(machines_jobs)

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
    # 开启搜索进度日志。
    solver.parameters.log_search_progress = True
    status = solver.solve(model)

    # 输出解。
    if status == cp_model.OPTIMAL:
        if visualization.RunFromIPython():
            # notebook 环境：提取各任务开始时间并用甘特图展示。
            starts = [
                [solver.value(all_tasks[(i, j)][0]) for j in all_machines]
                for i in all_jobs
            ]
            visualization.DisplayJobshop(starts, durations, machines, "FT06")
        else:
            # 终端环境：打印最优 makespan。
            print(f"Optimal makespan: {solver.objective_value}")


# 脚本被导入或执行时直接求解。
jobshop_ft06()
