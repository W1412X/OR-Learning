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

"""魔幻序列问题。

该模型旨在构造一个数字序列，使得数字 i 在该序列中
出现的次数等于序列第 i 个数字的值。
它使用了称为 distribute() 的 count 表达式的聚合形式。

用法: python magic_sequence_distribute.py NUMBER
"""

from absl import app
from absl import flags
from ortools.constraint_solver import pywrapcp

FLAGS = flags.FLAGS


def main(argv):
    # 创建求解器。
    solver = pywrapcp.Solver("magic sequence")

    # 创建一个 IntVar 数组来保存答案。
    # 序列长度 size 取自命令行第一个参数，未提供时默认为 100
    size = int(argv[1]) if len(argv) > 1 else 100
    # 所有可能的取值 0..size-1
    all_values = list(range(0, size))
    # 决策变量：all_vars[i] 表示序列第 i 个位置的值，取值范围 [0, size]
    all_vars = [solver.IntVar(0, size, "vars_%d" % i) for i in all_values]

    # 值等于 j 的变量个数应等于 all_vars[j] 的值。
    # Distribute(变量列表, 取值列表, 计数列表)：对每个取值 j，
    # 其在 all_vars 中出现的次数必须等于 all_vars[j]，形成自指计数约束
    solver.Add(solver.Distribute(all_vars, all_values, all_vars))

    # 所有值之和应等于 size。
    # （该约束是冗余的，但可以加快搜索速度。）
    solver.Add(solver.Sum(all_vars) == size)

    # 开始搜索：决策策略为"选第一个未绑定的变量，优先赋最小值"
    solver.NewSearch(
        solver.Phase(all_vars, solver.CHOOSE_FIRST_UNBOUND, solver.ASSIGN_MIN_VALUE)
    )
    # 找到并取第一个解
    solver.NextSolution()
    # 打印所有变量的取值
    print(all_vars)
    # 结束搜索
    solver.EndSearch()


if __name__ == "__main__":
    app.run(main)
