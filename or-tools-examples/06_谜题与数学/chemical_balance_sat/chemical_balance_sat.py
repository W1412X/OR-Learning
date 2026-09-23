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

"""化学平衡问题：将若干种化工原料组合起来，使 7 种养分元素的供给总量
尽可能贴近各自的目标用量（上限）。

输入是 7 种养分元素的目标用量（max_quantities）以及 5 种化工原料对每种
养分的单位贡献量（chemical_set）。要求确定每种原料的使用量，使每种养分
的总供给量不超过目标上限，且与目标的总短缺量（epsilon）最小。
"""

import math
from typing import Sequence
from absl import app
from ortools.sat.python import cp_model


def chemical_balance():
    """求解化学平衡问题。"""
    # 数据：7 种养分元素的目标（上限）用量
    max_quantities = [
        ["N_Total", 1944],
        ["P2O5", 1166.4],
        ["K2O", 1822.5],
        ["CaO", 1458],
        ["MgO", 486],
        ["Fe", 9.7],
        ["B", 2.4],
    ]

    # 数据：5 种化工原料（A~E），第 0 列为名称，其余为对 7 种养分的单位贡献量
    chemical_set = [
        ["A", 0, 0, 510, 540, 0, 0, 0],
        ["B", 110, 0, 0, 0, 160, 0, 0],
        ["C", 61, 149, 384, 0, 30, 1, 0.2],
        ["D", 148, 70, 245, 0, 15, 1, 0.2],
        ["E", 160, 158, 161, 0, 10, 1, 0.2],
    ]

    num_products = len(max_quantities)
    all_products = range(num_products)

    num_sets = len(chemical_set)
    all_sets = range(num_sets)

    # 建模
    model = cp_model.CpModel()

    # 将每种原料的用量上界放大 1000 倍后取整：对原料 s，在它含有的非零养分 q
    # 上取 max_quantities[q][1] * 1000 / chemical_set[s][q+1] 的最小值并向上
    # 取整，从而保证单独使用该原料时任何一种养分都不会超过目标上限。
    max_set = [
        int(
            math.ceil(
                min(
                    max_quantities[q][1] * 1000 / chemical_set[s][q + 1]
                    for q in all_products
                    if chemical_set[s][q + 1] != 0
                )
            )
        )
        for s in all_sets
    ]

    # 决策变量：第 s 种原料的使用量（放大 1000 倍后的整数值）
    set_vars = [model.new_int_var(0, max_set[s], f"set_{s}") for s in all_sets]

    # 决策变量：允许的最大短缺量（各养分与目标值之间的总偏差）
    epsilon = model.new_int_var(0, 10000000, "epsilon")

    # 约束：对每种养分 p，要求组合出的供给量落在 [目标 - epsilon, 目标] 区间内
    for p in all_products:
        # 上界约束：各原料对养分 p 的贡献总量不超过目标上限
        #（贡献量放大 10 倍、目标放大 10000 倍，用整数运算处理小数）
        model.add(
            sum(int(chemical_set[s][p + 1] * 10) * set_vars[s] for s in all_sets)
            <= int(max_quantities[p][1] * 10000)
        )
        # 下界约束：短缺量（目标减去总供给量）不超过 epsilon
        model.add(
            sum(int(chemical_set[s][p + 1] * 10) * set_vars[s] for s in all_sets)
            >= int(max_quantities[p][1] * 10000) - epsilon
        )

    # 目标函数：最小化最大短缺量 epsilon，使各养分的供给量尽可能贴近目标
    model.minimize(epsilon)

    # 创建求解器并求解
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL:
        # 最优目标值（除以 10000 还原为真实短缺量）
        print(f"Optimal objective value = {solver.objective_value / 10000.0}")

        # 打印每种原料的使用量（除以 1000 还原为真实数量）
        for s in all_sets:
            print(
                f"  {chemical_set[s][0]} = {solver.value(set_vars[s]) / 1000.0}",
                end=" ",
            )
            print()
        # 打印每种养分的实际供给量与目标上限的对比
        for p in all_products:
            name = max_quantities[p][0]
            max_quantity = max_quantities[p][1]
            quantity = sum(
                solver.value(set_vars[s]) / 1000.0 * chemical_set[s][p + 1]
                for s in all_sets
            )
            print(f"{name}: {quantity:.3f} out of {max_quantity}")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    chemical_balance()


if __name__ == "__main__":
    app.run(main)
