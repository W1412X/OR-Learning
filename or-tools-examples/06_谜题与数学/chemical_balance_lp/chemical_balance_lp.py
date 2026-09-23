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
"""译注：以下原始 docstring 为上游模板遗留文字（与 balance_group_sat 示例相同），
与本项目实际内容不符。本项目实际是"化肥配比"线性规划问题（chemical_set_lp）：
用若干种化肥组合（chemical_set）混合出肥料，使各养分总量尽量接近但不超过
给定配额（max_quantities），并最小化最大缺口 epsilon。

原始 docstring 译文（描述的是分组平衡问题，仅供参考）：
我们尝试把物品分成大小相同的组。
每个物品有颜色和取值。我们希望每组的取值之和尽可能接近平均值。
此外，如果某种颜色出现在某组中，该组必须至少包含 k 个该颜色的物品。"""

from ortools.linear_solver import pywraplp

# 数据

# 各养分的配额上限：[养分名称, 数量上限]。
max_quantities = [
    ["N_Total", 1944],
    ["P2O5", 1166.4],
    ["K2O", 1822.5],
    ["CaO", 1458],
    ["MgO", 486],
    ["Fe", 9.7],
    ["B", 2.4],
]

# 化肥组合（配方）清单：[名称, N_Total 含量, P2O5, K2O, CaO, MgO, Fe, B]；
# 每种组合的使用份数是决策变量。
chemical_set = [
    ["A", 0, 0, 510, 540, 0, 0, 0],
    ["B", 110, 0, 0, 0, 160, 0, 0],
    ["C", 61, 149, 384, 0, 30, 1, 0.2],
    ["D", 148, 70, 245, 0, 15, 1, 0.2],
    ["E", 160, 158, 161, 0, 10, 1, 0.2],
]

# 养分数量与索引范围。
NUM_PRODUCTS = len(max_quantities)
ALL_PRODUCTS = range(NUM_PRODUCTS)

# 化肥组合数量与索引范围。
NUM_SETS = len(chemical_set)
ALL_SETS = range(NUM_SETS)

# 模型

# 预计算每种组合的最大可用份数 max_set[s]：对含量非零的养分，
# 取"配额 / 单份含量"的最小值。
max_set = [
    min(max_quantities[q][1] / chemical_set[s][q + 1] for q in ALL_PRODUCTS
        if chemical_set[s][q + 1] != 0.0) for s in ALL_SETS
]

# 创建 GLOP 线性规划（LP）求解器。
solver = pywraplp.Solver("chemical_set_lp",
                         pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

# 决策变量：每种化肥组合使用的份数 set_vars[s]，取值范围 [0, max_set[s]]。
set_vars = [solver.NumVar(0, max_set[s], f"set_{s}") for s in ALL_SETS]

# 决策变量：允许的最大养分缺口 epsilon（各养分"不足额"的上界）。
epsilon = solver.NumVar(0, 1000, "epsilon")

# 约束：对每种养分 p，
#   - 总量 <= 配额（硬约束，不得超过）；
#   - 总量 >= 配额 - epsilon（允许至多缺口 epsilon）。
for p in ALL_PRODUCTS:
    solver.Add(
        sum(chemical_set[s][p + 1] * set_vars[s]
            for s in ALL_SETS) <= max_quantities[p][1])
    solver.Add(
        sum(chemical_set[s][p + 1] * set_vars[s]
            for s in ALL_SETS) >= max_quantities[p][1] - epsilon)

# 目标函数：最小化最大缺口 epsilon（各养分配给量越贴近配额越好）。
solver.Minimize(epsilon)

print(f"Number of variables = {solver.NumVariables()}")
print(f"Number of constraints = {solver.NumConstraints()}")

# 求解模型。
result_status = solver.Solve()

# 断言问题已求得最优解。
assert result_status == pywraplp.Solver.OPTIMAL

# 校验解的正确性（容差 1e-7，并打印校验信息）。
assert solver.VerifySolution(1e-7, True)

print(f"Problem solved in {solver.wall_time()} milliseconds")

# 解的目标值。
print(f"Optimal objective value = {solver.Objective().Value()}")

# 打印每种化肥组合的使用份数；
# 再打印每种养分的实际配给量与配额对比。
for s in ALL_SETS:
    print(f"  {chemical_set[s][0]} = {set_vars[s].solution_value()}", end=" ")
    print()
for p in ALL_PRODUCTS:
    name = max_quantities[p][0]
    max_quantity = max_quantities[p][1]
    quantity = sum(set_vars[s].solution_value() * chemical_set[s][p + 1]
                   for s in ALL_SETS)
    print(f"{name}: {quantity} out of {max_quantity}")
