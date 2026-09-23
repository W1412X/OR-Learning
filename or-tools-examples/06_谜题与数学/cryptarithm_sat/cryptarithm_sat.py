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

"""用 CP-SAT 求解一个简单的字谜算术问题：SEND+MORE=MONEY。"""

from absl import app
from ortools.sat.python import cp_model


def send_more_money() -> None:
    """求解字谜算术题 SEND+MORE=MONEY。"""
    model = cp_model.CpModel()

    # 创建变量。
    # s 是前导数字，因此不能为 0（取值 1~9）
    s = model.new_int_var(1, 9, "s")
    e = model.new_int_var(0, 9, "e")
    n = model.new_int_var(0, 9, "n")
    d = model.new_int_var(0, 9, "d")
    # m 是前导数字，因此不能为 0（取值 1~9）
    m = model.new_int_var(1, 9, "m")
    o = model.new_int_var(0, 9, "o")
    r = model.new_int_var(0, 9, "r")
    y = model.new_int_var(0, 9, "y")

    # 创建进位变量。c0 为真表示第一列相加后向高位进 1，
    # c1 表示第二列的进位，依此类推。
    c0 = model.new_bool_var("c0")
    c1 = model.new_bool_var("c1")
    c2 = model.new_bool_var("c2")
    c3 = model.new_bool_var("c3")

    # 约束：所有字母必须取互不相同的值。
    model.add_all_different(s, e, n, d, m, o, r, y)

    # 约束：逐列模拟竖式加法（从右往左）。
    # 第 0 列（个位）：
    model.add(c0 == m)

    # 第 1 列：
    model.add(c1 + s + m == o + 10 * c0)

    # 第 2 列：
    model.add(c2 + e + o == n + 10 * c1)

    # 第 3 列：
    model.add(c3 + n + r == e + 10 * c2)

    # 第 4 列（末列）：
    model.add(d + e == y + 10 * c3)

    # 求解模型。
    solver = cp_model.CpSolver()
    if solver.solve(model) == cp_model.OPTIMAL:
        print("Optimal solution found!")
    # 打印每个字母对应的数字
    print("s:", solver.value(s))
    print("e:", solver.value(e))
    print("n:", solver.value(n))
    print("d:", solver.value(d))
    print("m:", solver.value(m))
    print("o:", solver.value(o))
    print("r:", solver.value(r))
    print("y:", solver.value(y))


def main(_) -> None:
    send_more_money()


if __name__ == "__main__":
    app.run(main)
