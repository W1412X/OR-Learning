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

"""使用 CP-SAT 求解器求解带维护任务的作业车间调度问题。"""

import collections
from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """打印中间解的回调类。"""

    def __init__(self) -> None:
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0

    def on_solution_callback(self) -> None:
        """每当发现新的（更优）解时被调用。"""
        # 打印解的序号、耗时与当前目标值。
        print(
            f"Solution {self.__solution_count}, time = {self.wall_time} s,"
            f" objective = {self.objective_value}"
        )
        self.__solution_count += 1


def jobshop_with_maintenance() -> None:
    """求解一台机器带维护时段的作业车间调度问题。"""
    # 创建模型。
    model = cp_model.CpModel()

    # 作业数据：每个任务 = (机器编号, 加工时长)。
    jobs_data = [  # task = (machine_id, processing_time).
        [(0, 3), (1, 2), (2, 2)],  # Job0
        [(0, 2), (2, 1), (1, 4)],  # Job1
        [(1, 4), (2, 3)],  # Job2
    ]

    # 机器数量由数据推导（取最大机器编号 + 1）。
    machines_count = 1 + max(task[0] for job in jobs_data for task in job)
    all_machines = range(machines_count)

    # 动态计算时间上界 horizon：所有任务时长之和。
    horizon = sum(task[1] for job in jobs_data for task in job)

    # 命名元组：保存已创建变量的信息。
    task_type = collections.namedtuple("task_type", "start end interval")
    # 命名元组：用于整理解中的任务分配信息。
    assigned_task_type = collections.namedtuple(
        "assigned_task_type", "start job index duration"
    )

    # 创建各作业的区间变量，并把它们加入对应机器的列表。
    all_tasks = {}
    machine_to_intervals = collections.defaultdict(list)

    for job_id, job in enumerate(jobs_data):
        for entry in enumerate(job):
            task_id, task = entry
            machine, duration = task
            suffix = f"_{job_id}_{task_id}"
            # 任务 (job_id, task_id) 的开始时间变量。
            start_var = model.new_int_var(0, horizon, "start" + suffix)
            # 任务 (job_id, task_id) 的结束时间变量。
            end_var = model.new_int_var(0, horizon, "end" + suffix)
            # 区间变量：把开始、时长、结束绑定在一起。
            interval_var = model.new_interval_var(
                start_var, duration, end_var, "interval" + suffix
            )
            all_tasks[job_id, task_id] = task_type(
                start=start_var, end=end_var, interval=interval_var
            )
            # 把该任务区间登记到其所在机器。
            machine_to_intervals[machine].append(interval_var)

    # 添加维护区间（机器 0 在时间 {4, 5, 6, 7} 不可用）：
    # 维护区间从时刻 4 开始、时长 4、在时刻 8 结束。
    machine_to_intervals[0].append(model.new_interval_var(4, 4, 8, "weekend_0"))

    # 创建并添加析取（互斥）约束：每台机器上的任务两两不重叠
    # （机器 0 的区间列表还包含维护区间，因此任务也不会与维护时段重叠）。
    for machine in all_machines:
        model.add_no_overlap(machine_to_intervals[machine])

    # 作业内部的先后顺序：下一道工序必须等上一道工序结束。
    for job_id, job in enumerate(jobs_data):
        for task_id in range(len(job) - 1):
            model.add(
                all_tasks[job_id, task_id + 1].start >= all_tasks[job_id, task_id].end
            )

    # 目标函数：最小化 makespan（所有作业最后一道工序结束时间的最大值）。
    obj_var = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(
        obj_var,
        [all_tasks[job_id, len(job) - 1].end for job_id, job in enumerate(jobs_data)],
    )
    model.minimize(obj_var)

    # 求解模型（传入回调以打印中间解）。
    solver = cp_model.CpSolver()
    solution_printer = SolutionPrinter()
    status = solver.solve(model, solution_printer)

    # 输出解。
    if status == cp_model.OPTIMAL:
        # 按机器分组创建已排程任务列表。
        assigned_jobs = collections.defaultdict(list)
        for job_id, job in enumerate(jobs_data):
            for task_id, task in enumerate(job):
                machine = task[0]
                assigned_jobs[machine].append(
                    assigned_task_type(
                        start=solver.value(all_tasks[job_id, task_id].start),
                        job=job_id,
                        index=task_id,
                        duration=task[1],
                    )
                )

        # 逐机器生成输出行。
        output = ""
        for machine in all_machines:
            # 按开始时间排序。
            assigned_jobs[machine].sort()
            sol_line_tasks = "Machine " + str(machine) + ": "
            sol_line = "           "

            for assigned_task in assigned_jobs[machine]:
                name = f"job_{assigned_task.job}_{assigned_task.index}"
                # 加空格对齐各列。
                sol_line_tasks += f"{name:>10}"
                start = assigned_task.start
                duration = assigned_task.duration

                sol_tmp = f"[{start}, {start + duration}]"
                # 加空格对齐各列。
                sol_line += f"{sol_tmp:>10}"

            sol_line += "\n"
            sol_line_tasks += "\n"
            output += sol_line_tasks
            output += sol_line

        # 最后打印找到的最优解。
        print(f"Optimal Schedule Length: {solver.objective_value}")
        print(output)
        print(solver.response_stats())


def main(argv: Sequence[str]) -> None:
    # 命令行只允许无额外参数。
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    jobshop_with_maintenance()


if __name__ == "__main__":
    app.run(main)
