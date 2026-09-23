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

"""以优化问题的方式求解汽车排序问题（car sequencing problem）。

问题描述：带优化的汽车排序问题
-----------------------------------------------------------------

更多细节参见 https://en.wikipedia.org/wiki/Car_sequencing_problem 。

我们要为一组汽车确定装配线上的最优生产顺序。这是一个经典且具有挑战性的
组合优化问题，具有以下特点：

固定的生产需求：不同类型（或"类别"）的汽车必须按给定的、不可协商的数量
生产。本例中共有 6 种不同类别的汽车，每种恰好生产 5 辆，即共 30 辆
"真实"汽车。

多样化的汽车配置：每种类别由一组选装件（可选配置）的唯一组合定义。例如
"类别 1"可能需要天窗（选装件 1）和特殊发动机（选装件 4），而"类别 3"
只需要空调（选装件 2）。

专业化工位：装配线由一系列专业化工位组成，每个工位负责安装一种特定选装件，
例如天窗工位、特殊发动机工位等。

工位产能受限：问题的核心挑战在于此。工位无法处理无限密集的、需要其对应
选装件的汽车流。其产能由"滑动窗口"约束定义。例如天窗工位的约束可能是
"任意连续 3 辆汽车中，带天窗的至多 1 辆"。这意味着 [天窗, 无, 无, 天窗]
这样的序列合法，而 [天窗, 无, 天窗, 无] 不合法。

需要间隔（优化所在）：某些选装件需求量大而产能约束又紧，两者叠加可能导致
30 辆真实汽车无法连续生产。为了得到合法序列，可能需要在生产线上插入
"虚拟"（填充）汽车。虚拟汽车不带任何选装件，因此不占用任何工位产能，
纯粹作为间隔物，用来隔开选装件密集的汽车序列。

目标：找到满足全部 30 辆真实汽车需求、且使用虚拟汽车数量最少的生产序列。
这等价于寻找尽可能短的总生产排程（真实汽车 + 虚拟汽车）。

用 CP-SAT 建模与求解
------------------------------------------

我们使用 Google OR-Tools 库中的 CP-SAT 求解器来求解该问题。这是约束规划
（constraint programming）方法，通过定义变量、约束和目标函数来工作。

1. 决策变量
求解器要做的根本决策是："每个生产槽位应放置哪种类别的汽车？"
我们定义大量布尔变量 produces[c][s]：若槽位 s 排产类别 c 的汽车则为 True，
否则为 False。为所有汽车类别（含虚拟类别）和扩展的槽位数（30 个真实槽位
+ 20 个虚拟缓冲槽位）创建这些变量。
再引入一个关键整数变量 makespan（完工时刻）：它表示排程"有效部分"的总
长度，即第一辆虚拟汽车出现的槽位号——在其之后的所有汽车也都是虚拟汽车。

2. 约束（游戏规则）
我们把问题的规则翻译成求解器必须遵守的数学约束：

每个槽位一辆车：对每个生产槽位 s，恰好指派一种汽车类别。用 AddExactlyOne
约束对该槽位的所有 produces[c][s] 变量强制执行。

满足真实汽车需求：每种真实类别 c 在所有槽位中出现的总次数必须等于其需求量
（本例为 5）。即简单的 Add(sum(...) == 5) 约束。

工位产能（滑动窗口）：这是最关键的约束。对每种选装件（如天窗）及其产能规则
（如"3 中取 1"），为每个可能的滑动窗口建立约束：对每个长度为 3 的连续
槽位子序列，把需要该选装件的类别对应的 produces 变量求和，并限制该和
<= 1。

完工时刻定义：这是模型的巧妙之处。对每个槽位 s，用逻辑等价把 makespan
目标变量与虚拟汽车的位置关联起来：
(makespan <= s) 等价于 (槽位 s 放置虚拟汽车)
这保证：若求解器选择 makespan = 32，则它被迫在槽位 32、33、34 等处放置
虚拟汽车；反之，若为满足产能约束求解器不得不在槽位 32 放置虚拟汽车，
则 makespan 必须不超过 32。

3. 目标函数

目标简单且直接对应我们的目的：

最小化 makespan：指示求解器找到 makespan 变量取值尽可能小的解，即找到
满足全部规则的最短生产排程，这本身就最小化了使用的虚拟汽车数量。

按上述方式定义问题后，CP-SAT 求解器即可借助其强大的约束传播与搜索技术，
高效地探索庞大的可能序列空间，找到满足全部复杂要求的最优排列。
"""

from collections.abc import Sequence

from absl import app

from ortools.sat.python import cp_model


def solve_car_sequencing_optimization() -> None:
    """用优化方法求解汽车排序问题。"""

    # --------------------
    # 1. 数据
    # --------------------
    # 真实汽车总数（6 类 × 每类 5 辆）与虚拟汽车（填充车）数量上限。
    num_real_cars: int = 30
    max_dummy_cars: int = 20
    num_slots = num_real_cars + max_dummy_cars
    all_slots = range(num_slots)

    class_options = [
        # 各列对应选装件: 1  2  3  4  5
        [0, 0, 0, 0, 0],  # 类别 0（虚拟汽车）
        [1, 0, 0, 1, 0],  # 类别 1（选装件 1 + 选装件 4）
        [0, 1, 0, 0, 1],  # 类别 2（选装件 2 + 选装件 5）
        [0, 1, 0, 0, 0],  # 类别 3（选装件 2）
        [0, 0, 1, 1, 0],  # 类别 4（选装件 3 + 选装件 4）
        [0, 0, 1, 0, 0],  # 类别 5（选装件 3）
        [0, 0, 0, 0, 1],  # 类别 6（选装件 5）
    ]
    num_classes = len(class_options)
    all_classes = range(num_classes)
    real_classes = range(1, num_classes)
    dummy_class = 0

    # 每种真实类别的需求量（与 real_classes 1..6 一一对应）。
    demands = [5, 5, 5, 5, 5, 5]

    # 每种选装件的产能规则 (max_cars, subsequence_len)：
    # 任意连续 subsequence_len 个槽位中，装有该选装件的汽车至多 max_cars 辆。
    capacity_constraints = [(1, 3), (1, 2), (1, 3), (2, 5), (1, 5)]
    num_options = len(capacity_constraints)
    all_options = range(num_options)

    # 预处理：每种选装件对应哪些真实类别。
    classes_with_option = [
        [c for c in real_classes if class_options[c][o] == 1] for o in all_options
    ]

    # --------------------
    # 2. 创建模型
    # --------------------
    model = cp_model.CpModel()

    # --------------------
    # 3. 决策变量
    # --------------------
    # 布尔决策变量 produces[(c, s)]：槽位 s 是否生产类别 c 的汽车。
    produces = {}
    for c in all_classes:
        for s in all_slots:
            produces[(c, s)] = model.new_bool_var(f"produces_c{c}_s{s}")

    # 完工时刻 makespan：有效排程的长度（首个虚拟汽车出现的位置）。
    makespan = model.new_int_var(num_real_cars, num_slots, "makespan")

    # --------------------
    # 4. 约束
    # --------------------

    # 约束 1：每个槽位恰好生产一辆汽车。
    for s in all_slots:
        model.add_exactly_one([produces[(c, s)] for c in all_classes])

    # 约束 2：满足真实汽车的需求量。
    for i, c in enumerate(real_classes):
        model.add(sum(produces[(c, s)] for s in all_slots) == demands[i])

    # 约束 3：对每种选装件施加滑动窗口产能约束。
    for o in all_options:
        max_cars, subsequence_len = capacity_constraints[o]
        for start in range(num_slots - subsequence_len + 1):
            window = range(start, start + subsequence_len)
            cars_with_option_in_window = []
            for c in classes_with_option[o]:
                for s in window:
                    cars_with_option_in_window.append(produces[(c, s)])
            model.add(sum(cars_with_option_in_window) <= max_cars)

    # 约束 4（把目标变量与排程末尾的虚拟汽车关联起来）
    for s in all_slots:
        makespan_le_s = model.new_bool_var(f"makespan_le_{s}")

        # 强制 makespan_le_s <=> (makespan <= s)
        model.add(makespan <= s).only_enforce_if(makespan_le_s)
        # 用 ~ 表示取反
        model.add(makespan > s).only_enforce_if(~makespan_le_s)

        # 强制 makespan_le_s => produces[dummy_class, s]
        # （makespan <= s 时，槽位 s 必须放虚拟汽车）
        model.add_implication(makespan_le_s, produces[dummy_class, s])

    # --------------------
    # 5. 目标函数
    # --------------------
    model.minimize(makespan)

    # --------------------
    # 6. 求解并打印解
    # --------------------
    # 求解模型（限时 30 秒，单线程即可）。
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 1  # 问题较容易，单线程即可。
    # solver.parameters.log_search_progress = True  # 取消注释以查看求解日志。

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        final_makespan = int(solver.ObjectiveValue())
        num_dummies_needed = final_makespan - num_real_cars

        print(
            f'\n{"Optimal" if status == cp_model.OPTIMAL else "Feasible"}'
            f" solution found with a makespan of {final_makespan}."
        )
        print(
            f"This requires the conceptual equivalent of {num_dummies_needed} dummy"
            " car(s) to be used as spacers."
        )

        # 还原解：记录每个槽位生产的汽车类别。
        sequence = [-1] * num_slots
        for s in all_slots:
            for c in all_classes:
                if solver.Value(produces[(c, s)]) == 1:
                    sequence[s] = c
                    break

        print("\nFull Production Sequence (Class 0 is dummy):")
        print("Slot:  | " + " | ".join(f"{i:2}" for i in range(num_slots)) + " |")
        print("-------|-" + "--|-" * num_slots)
        print("Class: | " + " | ".join(f"{c:2}" for c in sequence) + " |")

    elif status == cp_model.INFEASIBLE:
        print("\nNo solution found.")

    else:
        print(f"\nSomething went wrong. Solver status: {status}")

    print("\nSolver statistics:")
    print(solver.response_stats())


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    solve_car_sequencing_optimization()


if __name__ == "__main__":
    app.run(main)
