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

"""闸门调度问题。

我们有一组待执行的任务（时长、宽度）。
有两台并行机器可以执行这些任务。
一台机器同一时刻只能执行一个任务。
任意时刻，两台机器上正在执行的任务的宽度之和
不得超过最大宽度 max_width。

优化目标是最小化所有任务的最大结束时间。
"""

from absl import app
from ortools.sat.python import cp_model
from ortools.sat.colab import visualization


def main(_) -> None:
    """求解闸门调度问题。"""
    model = cp_model.CpModel()

    # 数据：每个任务为 [时长, 宽度]
    jobs = [
        [3, 3],  # [duration, width]
        [2, 5],
        [1, 3],
        [3, 7],
        [7, 3],
        [2, 2],
        [2, 2],
        [5, 5],
        [10, 2],
        [4, 3],
        [2, 6],
        [1, 2],
        [6, 8],
        [4, 5],
        [3, 7],
    ]

    # 宽度上限：任意时刻活动任务的宽度总和不得超过该值
    max_width = 10

    # 时间上界：所有任务时长之和
    horizon = sum(t[0] for t in jobs)
    num_jobs = len(jobs)
    all_jobs = range(num_jobs)

    intervals = []
    intervals0 = []
    intervals1 = []
    performed = []
    starts = []
    ends = []
    demands = []

    for i in all_jobs:
        # 创建主区间。
        # 决策变量：任务开始时间
        start = model.new_int_var(0, horizon, f"start_{i}")
        duration = jobs[i][0]
        # 决策变量：任务结束时间
        end = model.new_int_var(0, horizon, f"end_{i}")
        interval = model.new_interval_var(start, duration, end, f"interval_{i}")
        starts.append(start)
        intervals.append(interval)
        ends.append(end)
        # 需求量：任务宽度（用于累积约束）
        demands.append(jobs[i][1])

        # 创建一个可选区间副本，表示任务在机器 0 上执行。
        # 布尔变量：任务是否在机器 0 上执行
        performed_on_m0 = model.new_bool_var(f"perform_{i}_on_m0")
        performed.append(performed_on_m0)
        start0 = model.new_int_var(0, horizon, f"start_{i}_on_m0")
        end0 = model.new_int_var(0, horizon, f"end_{i}_on_m0")
        interval0 = model.new_optional_interval_var(
            start0, duration, end0, performed_on_m0, f"interval_{i}_on_m0"
        )
        intervals0.append(interval0)

        # 创建一个可选区间副本，表示任务在机器 1 上执行。
        # presence 取反，保证两台机器恰好二选一。
        start1 = model.new_int_var(0, horizon, f"start_{i}_on_m1")
        end1 = model.new_int_var(0, horizon, f"end_{i}_on_m1")
        interval1 = model.new_optional_interval_var(
            start1,
            duration,
            end1,
            ~performed_on_m0,
            f"interval_{i}_on_m1",
        )
        intervals1.append(interval1)

        # 只有当任务被安排到某台机器上时，才传播同步约束
        #（把该机器上的局部开始时间与主开始时间绑定）。
        model.add(start0 == start).only_enforce_if(performed_on_m0)
        model.add(start1 == start).only_enforce_if(~performed_on_m0)

    # 宽度约束（用累积约束建模）：任意时刻活动任务的宽度总和不超过 max_width
    model.add_cumulative(intervals, demands, max_width)

    # 机器分配约束：每台机器上的任务不能重叠
    model.add_no_overlap(intervals0)
    model.add_no_overlap(intervals1)

    # 目标变量：makespan。
    # 约束：makespan 等于所有任务结束时间的最大值
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, ends)
    # 目标：最小化 makespan
    model.minimize(makespan)

    # 对称性破除：强制任务 0 在机器 1 上执行，消除两台机器互换的对称解。
    model.add(performed[0] == 0)

    # 求解模型。
    solver = cp_model.CpSolver()
    solver.solve(model)

    # 输出解。
    if visualization.RunFromIPython():
        # notebook 环境：生成 SVG 甘特图
        output = visualization.SvgWrapper(solver.objective_value, max_width, 40.0)
        output.AddTitle(f"Makespan = {solver.objective_value}")
        color_manager = visualization.ColorManager()
        color_manager.SeedRandomColor(0)

        for i in all_jobs:
            # 计算任务所在机器（0 或 1），决定其在图中的纵向位置
            performed_machine = 1 - solver.value(performed[i])
            start_of_task = solver.value(starts[i])
            d_x = jobs[i][0]
            d_y = jobs[i][1]
            s_y = performed_machine * (max_width - d_y)
            output.AddRectangle(
                start_of_task,
                s_y,
                d_x,
                d_y,
                color_manager.RandomColor(),
                "black",
                f"j{i}",
            )

        output.AddXScale()
        output.AddYScale()
        output.Display()
    else:
        # 终端环境：文本输出
        print("Solution")
        print(f"  - makespan = {solver.objective_value}")
        for i in all_jobs:
            performed_machine = 1 - solver.value(performed[i])
            start_of_task = solver.value(starts[i])
            print(
                f"  - Job {i} starts at {start_of_task} on machine"
                f" {performed_machine}"
            )
        print(solver.response_stats())


if __name__ == "__main__":
    app.run(main)
