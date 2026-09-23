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
"""重新分配生产任务，使各年度的产量更加平滑（均衡）。"""


import collections

from ortools.sat.python import cp_model


def main():
    # 数据
    data_0 = [
        [107, 107, 107, 0, 0],  # pr1（项目 1）
        [0, 47, 47, 47, 0],  # pr2（项目 2）
        [10, 10, 10, 0, 0],  # pr3（项目 3）
        [0, 55, 55, 55, 55],  # pr4（项目 4）
    ]

    data_1 = [
        [119444030, 0, 0, 0],
        [34585586, 38358559, 31860661, 0],
        [19654655, 21798799, 18106106, 0],
        [298836792, 0, 0, 0],
        [3713428, 4118530, 4107277, 3072018],
        [6477273, 7183884, 5358471, 0],
        [1485371, 1647412, 1642911, 1228807],
    ]

    data_2 = [
        [1194440, 0, 0, 0],
        [345855, 383585, 318606, 0],
        [196546, 217987, 181061, 0],
        [2988367, 0, 0, 0],
        [37134, 41185, 41072, 30720],
        [64772, 71838, 53584, 0],
        [14853, 16474, 16429, 12288],
    ]

    # 选择当前使用的输入数据集（可改为 data_1 或 data_2）
    pr = data_0

    # 项目数与年数
    num_pr = len(pr)
    num_years = len(pr[1])
    # 所有项目各年产量的总和，以及年度平均值
    total = sum(pr[p][y] for p in range(num_pr) for y in range(num_years))
    avg = total // num_years

    # 建模
    model = cp_model.CpModel()

    # 变量
    # delta：各年产量与平均值之间的最大偏差（目标变量）
    delta = model.NewIntVar(0, total, "delta")

    # 贡献变量：仅对原计划中非零的 (项目, 年份) 格子创建
    contributions_per_years = collections.defaultdict(list)
    contributions_per_prs = collections.defaultdict(list)
    all_contribs = {}

    for p, inner_l in enumerate(pr):
        for y, item in enumerate(inner_l):
            if item != 0:
                # 重新分配后项目 p 在年份 y 的产量
                contrib = model.NewIntVar(0, total, "r%d c%d" % (p, y))
                contributions_per_years[y].append(contrib)
                contributions_per_prs[p].append(contrib)
                all_contribs[p, y] = contrib

    # 各年度总产量变量
    year_var = [model.NewIntVar(0, total, "y[%i]" % i) for i in range(num_years)]

    # 约束

    # 维护 year_var：年度总量 = 该年所有项目贡献之和。
    for y in range(num_years):
        model.Add(year_var[y] == sum(contributions_per_years[y]))

    # 每个项目被重新分配后的产量之和必须与原计划总量一致。
    for p in range(num_pr):
        model.Add(sum(pr[p]) == sum(contributions_per_prs[p]))

    # 把 delta 与年度变量关联：每年产量都落在 [avg - delta, avg + delta] 内。
    for y in range(num_years):
        model.Add(year_var[y] >= avg - delta)

    for y in range(num_years):
        model.Add(year_var[y] <= avg + delta)

    # 求解并输出
    # 目标函数：最小化最大偏差 delta（越小表示各年产量越均衡）
    model.Minimize(delta)

    # 求解模型。
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # 输出解。
    if status == cp_model.OPTIMAL:
        print("Data")
        print("  - total = ", total)
        print("  - year_average = ", avg)
        print("  - number of projects = ", num_pr)
        print("  - number of years = ", num_years)

        # 打印原始输入产量表
        print("  - input production")
        for p in range(num_pr):
            for y in range(num_years):
                if pr[p][y] == 0:
                    print("        ", end="")
                else:
                    print("%10i" % pr[p][y], end="")
            print()

        # 打印重新分配后的产量表
        print("Solution")
        for p in range(num_pr):
            for y in range(num_years):
                if pr[p][y] == 0:
                    print("        ", end="")
                else:
                    print("%10i" % solver.Value(all_contribs[p, y]), end="")
            print()

        # 打印重新分配后各年的总产量
        for y in range(num_years):
            print("%10i" % solver.Value(year_var[y]), end="")
        print()


if __name__ == "__main__":
    main()
